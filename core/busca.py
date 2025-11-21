"""
core/busca.py
Busca inteligente de clientes no Zoho Desk.

- Variações de nomes (PF/PJ) com saneamento
- Fuzzy-match com limiar dinâmico (PF vs PJ)
- Cache de decisões manuais (não pergunta duas vezes)
- Escolha manual quando não há match automático
- Resiliência a DOM instável (timeouts adaptativos, pequenos retries)
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


# ---------------------------------------------------------------------------
# Configs e utilitários com fallbacks (evita quebrar import-time)
# ---------------------------------------------------------------------------
def _load_cfg():
    """Carrega CONFIG com fallbacks seguros."""
    try:
        from config import CONFIG  # type: ignore
        return CONFIG
    except Exception:
        class _Fuzzy:
            threshold = 0.85
            primeiro_ultimo = 0.84
        class _Timeouts:
            login = 300
            search_wait = 15
            after_click = 20
        class _Cfg:
            fuzzy = _Fuzzy()
            timeouts = _Timeouts()
        return _Cfg()

CONFIG = _load_cfg()

# Funções de normalização/fuzzy (tenta utils, cai para normalizacao)
try:
    from utils import (  # type: ignore
        normalizar_nome,
        calcular_fuzzy_score,
        tipo_cliente,
        _sanear_termo_busca,
        _tokens_nome,
        _limpa_sufixos_empresa,
    )
except Exception:
    # fallbacks mínimos usando normalizacao.py
    from normalizacao import normalizar_nome, calcular_fuzzy_score, tipo_cliente  # type: ignore

# Importa função de formatação de documentos
try:
    from utils.validation import formatar_documento_brasil  # type: ignore
except Exception:
    # fallback se não existir
    def formatar_documento_brasil(valor):
        if not valor:
            return ""
        limpo = re.sub(r'\D', '', str(valor))
        if len(limpo) == 11:  # CPF
            return f"{limpo[:3]}.{limpo[3:6]}.{limpo[6:9]}-{limpo[9:]}"
        elif len(limpo) == 14:  # CNPJ
            return f"{limpo[:2]}.{limpo[2:5]}.{limpo[5:8]}/{limpo[8:12]}-{limpo[12:]}"
        return valor

    # utilitários auxiliares locais (versões simples)
    def _sanear_termo_busca(txt: str) -> str:
        t = normalizar_nome(txt, remover_invalidos=True)
        return " ".join(p for p in t.split() if len(p) >= 2)

    def _tokens_nome(txt: str) -> List[str]:
        return [p for p in normalizar_nome(txt, remover_invalidos=True).split() if len(p) > 1]

    def _limpa_sufixos_empresa(txt: str) -> str:
        # remove sufixos societários básicos
        base = normalizar_nome(txt, remover_invalidos=True)
        sufx = {"ltda", "me", "epp", "sa", "eireli", "ei"}
        return " ".join(p for p in base.split() if p not in sufx)


# ---------------------------------------------------------------------------
# Cache de decisões manuais
# ---------------------------------------------------------------------------
CACHE_FILE = Path(__file__).resolve().parent.parent / "mapeamentos_decisoes.json"

def _carregar_cache() -> Dict[str, Dict]:
    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _salvar_cache(cache: Dict[str, Dict]) -> None:
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Falha ao salvar cache de decisões: {e!r}")


# ---------------------------------------------------------------------------
# Geração de variações de busca
# ---------------------------------------------------------------------------
_SOBRENOMES_MUITO_COMUNS = {
    "silva","santos","souza","oliveira","pereira","lima","ferreira","costa","rodrigues",
    "almeida","nascimento","gomes","martins","araujo","melo","barbosa","cardoso","teixeira",
    "dias","vieira","batista"
}

def _gerar_variacoes_inteligentes(nome_original: str) -> List[str]:
    """
    - Prioriza "Primeiro + Segundo"
    - Alternativa "Primeiro + Último"
    - Último token se não for muito comum
    - Nome completo (3+ tokens)
    - Primeiro nome (>=3)
    """
    variacoes: List[str] = []
    nome_limpo = _limpa_sufixos_empresa(nome_original)
    toks = _tokens_nome(nome_limpo)

    if not toks:
        unico = _sanear_termo_busca(nome_limpo)
        return [unico] if unico else []

    # 1) Primeiro + Segundo
    if len(toks) >= 2:
        variacoes.append(f"{toks[0]} {toks[1]}")

    # 2) Primeiro + Último
    if len(toks) >= 2:
        variacoes.append(f"{toks[0]} {toks[-1]}")

    # 3) Último token (se não for muito comum)
    ultimo = toks[-1]
    if len(ultimo) >= 3 and ultimo not in _SOBRENOMES_MUITO_COMUNS:
        variacoes.append(ultimo)

    # 4) Nome completo (se 3+)
    if len(toks) >= 3:
        variacoes.append(" ".join(toks))

    # 5) Primeiro nome (curto, porém útil)
    if len(toks[0]) >= 3:
        variacoes.append(toks[0])

    # Sanitiza, remove duplicatas, limita a 10
    final = []
    vistos = set()
    for v in variacoes:
        s = _sanear_termo_busca(v)
        if s and len(s) >= 3 and s not in vistos:
            vistos.add(s)
            final.append(s)
    return final[:10]


# ---------------------------------------------------------------------------
# Limiar dinâmico para fuzzy
# ---------------------------------------------------------------------------
def _limiar_dinamico(tipo: str, qtd_resultados: int, ratio_geral: float) -> float:
    """
    Ajusta limiar conforme tipo e contexto.
    - PJ: se já temos um match parcial razoável (ratio_geral > 0.7), relaxa 0.05
    - PF: com poucos resultados coletados, relaxa levemente
    Clampa entre [0.70, 0.95]
    """
    cfg = getattr(CONFIG, "fuzzy", None)
    base = getattr(cfg, "primeiro_ultimo", 0.84)
    if tipo == "PJ":
        if ratio_geral > 0.70:
            base -= 0.05
    else:
        if qtd_resultados <= 3:
            base -= 0.03
    return max(0.70, min(0.95, base))


# ---------------------------------------------------------------------------
# Escolha manual (console)
# ---------------------------------------------------------------------------
def _escolher_resultado_manual(resultados_dict: Dict[str, Dict], nome_original: str) -> Optional[Dict]:
    print("\a")  # beep
    print("\n" + "=" * 60)
    print(f"Buscando por: '{nome_original}'")
    print("⚠️  Nenhum match automático encontrado.")
    print(f"Coletados {len(resultados_dict)} resultados parciais:")
    print("=" * 60)

    lista_ordenada = sorted(resultados_dict.values(), key=lambda x: x["score"], reverse=True)
    for idx, res in enumerate(lista_ordenada, 1):
        via = res.get("busca_origem", "")
        nome_exib = res.get("nome_exibicao", "")
        badge = "PJ" if tipo_cliente(normalizar_nome(nome_exib)) == "PJ" else "PF"
        print(f"  {idx}) {nome_exib}  [{badge}]  (Score: {res['score']*100:.0f}% | via: '{via}')")
    print("  0) NENHUM dos resultados está correto (pular cliente)")
    print("=" * 60)

    while True:
        try:
            escolha = input(f"\nEscolha o número correto (0-{len(lista_ordenada)}): ").strip()
            n = int(escolha)
            if n == 0:
                return None
            if 1 <= n <= len(lista_ordenada):
                escolhido = lista_ordenada[n - 1]
                _registrar_decisao_manual(
                    entrada_norm=normalizar_nome(nome_original),
                    via=escolhido.get("busca_origem", ""),
                    nome_exibicao=escolhido.get("nome_exibicao", "")
                )
                return escolhido
            print("❌ Opção inválida.")
        except (ValueError, EOFError, KeyboardInterrupt):
            print("\n❌ Entrada inválida. Digite apenas o número.")


def _registrar_decisao_manual(entrada_norm: str, via: str, nome_exibicao: str) -> None:
    cache = _carregar_cache()
    item = cache.get(entrada_norm, {"via": via, "nome_exibicao": nome_exibicao, "contagem": 0})
    item["via"] = via
    item["nome_exibicao"] = nome_exibicao
    item["contagem"] = int(item.get("contagem", 0)) + 1
    cache[entrada_norm] = item
    _salvar_cache(cache)


# ---------------------------------------------------------------------------
# Helpers de espera
# ---------------------------------------------------------------------------
def _wait(driver, seconds: Optional[int] = None) -> WebDriverWait:
            logger.warning(f"Falha ao aplicar mapeamento (seguindo fluxo normal): {e!r}")

    # 2) variações
    variacoes = _gerar_variacoes_inteligentes(nome_cliente)
    if not variacoes:
        logger.warning(f"❌ Nenhuma variação válida gerada para '{nome_cliente}'")
        return False
    logger.info(f"🔍 Geradas {len(variacoes)} variações para busca: {variacoes}")

    todos_os_resultados: Dict[str, Dict] = {}
    wait = _wait(driver)

    for tentativa, termo in enumerate(variacoes, 1):
        termo_busca = _sanear_termo_busca(termo.strip())
        if len(termo_busca) < 3:
            logger.debug(f"  → Tentativa {tentativa}/{len(variacoes)}: ignorando termo curto '{termo}'")
            continue

        logger.debug(f"  → Tentativa {tentativa}/{len(variacoes)}: buscando por '{termo_busca}'")
        try:
            # Abre barra e dispara busca
            barra = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[data-id="searchInput"]')))
            barra.clear()
            barra.send_keys(termo_busca)
            barra.send_keys("\n")
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"❌ Erro ao enviar termo na barra de pesquisa: {e!r}")
            continue

        # Espera renderizar algo (resultados ou estado vazio)
        try:
            wait.until(EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-title]")),
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.zd_v2-commonemptystate-title")),
            ))
        except TimeoutException:
            logger.warning(f"⏰ Timeout aguardando resultados para '{termo_busca}'")
            continue

        # Estado "nenhum resultado"
        try:
            msg = driver.find_element(By.CSS_SELECTOR, "div.zd_v2-commonemptystate-title")
            if msg.is_displayed():
                logger.debug(f"Tentativa {tentativa}: nenhum resultado para '{termo_busca}'.")
                continue
        except NoSuchElementException:
            pass

        # Coleta itens
        try:
            itens = []
            for _ in range(5):  # pequenos retries contra stale
                try:
                    itens = driver.find_elements(By.CSS_SELECTOR, "a[data-title]")
                    if itens and any(i.get_attribute("data-title") for i in itens):
                        break
                    time.sleep(0.4)
                except StaleElementReferenceException:
                    continue

            if not itens:
                logger.warning(f"Tentativa {tentativa}: DOM vazio para '{termo_busca}'.")
                continue

            nome_busca_norm = normalizar_nome(termo_busca, remover_invalidos=True)

            for link in itens:
                try:
                    exib = link.get_attribute("data-title") or link.text
                    if not exib:
                        continue
                    exib_norm = normalizar_nome(exib, remover_invalidos=True)

                    # match exato normalizado
                    if exib_norm == nome_original_norm:
                        logger.info(f"✅ EXATO: '{exib}' (via '{termo_busca}')")
                        link.click()
                        WebDriverWait(driver, getattr(CONFIG.timeouts, "after_click", 20)).until(
                            EC.element_to_be_clickable(
                                (By.CSS_SELECTOR, 'span[data-title="Enviar mensagens via WhatsApp (canal de IM)"]')
                            )
                        )
                        return True

                    # fuzzy
                    fuzzy = calcular_fuzzy_score(exib_norm, nome_original_norm)
                    tipo_b = tipo_cliente(nome_original_norm)
                    thr = _limiar_dinamico(tipo_b, len(todos_os_resultados), fuzzy["ratio"])
                    if fuzzy["ratio"] >= thr:
                        logger.info(f"✅ FUZZY {fuzzy['ratio']*100:.0f}% (thr {thr*100:.0f}%): '{exib}' (via '{termo_busca}')")
                        link.click()
                        WebDriverWait(driver, getattr(CONFIG.timeouts, "after_click", 20)).until(
                            EC.element_to_be_clickable(
                                (By.CSS_SELECTOR, 'span[data-title="Enviar mensagens via WhatsApp (canal de IM)"]')
                            )
                        )
                        return True

                    # coleta “quase bons” (>= 0.50)
                    score = fuzzy["ratio"]
                    if score >= 0.50:
                        chave = exib_norm
                        cur = todos_os_resultados.get(chave)
                        if not cur or cur["score"] < score:
                            todos_os_resultados[chave] = {
                                "nome_exibicao": exib,
                                "score": score,
                                "busca_origem": termo_busca,
                            }

                except StaleElementReferenceException:
                    continue
                except Exception as e:
                    logger.debug(f"Erro ao processar item de resultado: {e!r}")
                    continue

        except Exception as e_list:
            logger.error(f"Erro ao processar lista para '{termo_busca}': {e_list!r}")
            try:
                from core.driver import _screenshot_fallback  # import tardio pra evitar circularidade
                _screenshot_fallback(f"erro_busca_{nome_cliente}", driver)
            except Exception:
                pass
            continue

    # 3) escolha manual
    if not todos_os_resultados:
        logger.warning(f"❌ Cliente '{nome_cliente}' NÃO encontrado após {len(variacoes)} tentativas")
        return False

    logger.info(f"Nenhum match automático para '{nome_cliente}'. Apresentando {len(todos_os_resultados)} candidatos...")
    escolha = _escolher_resultado_manual(todos_os_resultados, nome_cliente)
    if not escolha:
        logger.warning(f"Usuário optou por pular '{nome_cliente}'.")
        return False

    # 4) reexecuta busca específica e clica
    return _executar_busca_e_clicar(driver, escolha["busca_origem"], escolha["nome_exibicao"])


# ---------------------------------------------------------------------------
# Re-execução de busca e clique determinístico
# ---------------------------------------------------------------------------
def _executar_busca_e_clicar(driver, nome_busca: str, nome_para_clicar: str) -> bool:
    """
    Reexecuta a busca por `nome_busca` e clica no item cujo `data-title` ou texto
    corresponda exatamente a `nome_para_clicar`.
    """
    logger.info(f"🔄 Reexecutando busca por '{nome_busca}' para clicar em '{nome_para_clicar}'")
    wait = _wait(driver, seconds=getattr(CONFIG.timeouts, "search_wait", 15))

    # dispara busca
    barra = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[data-id="searchInput"]')))
    barra.clear()
    barra.send_keys(nome_busca)
    barra.send_keys("\n")
    time.sleep(0.5)

    # espera renderizar
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-title]")))
    itens = driver.find_elements(By.CSS_SELECTOR, "a[data-title]")

    alvo_norm = normalizar_nome(nome_para_clicar, remover_invalidos=True)
    for link in itens:
        try:
            exib = link.get_attribute("data-title") or link.text
            if not exib:
                continue
            if normalizar_nome(exib, remover_invalidos=True) == alvo_norm:
                link.click()
                WebDriverWait(driver, getattr(CONFIG.timeouts, "after_click", 20)).until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, 'span[data-title="Enviar mensagens via WhatsApp (canal de IM)"]')
                    )
                )
                logger.success(f"✅ Clicado: '{exib}'")
                return True
        except StaleElementReferenceException:
            continue

    logger.warning(f"❌ Não foi possível clicar em '{nome_para_clicar}' (não apareceu na lista).")
    return False


# ---------------------------------------------------------------------------
# Testes básicos (opcional, não executa login/UI)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # sanity local dos geradores (sem Selenium)
    casos = [
        "João da Silva",
        "FLAVIO LOPES BATISTA",
        "EMPRESA XPTO LTDA ME",
        "Maria de Souza e Silva",
    ]
    for c in casos:
        print(c, "->", _gerar_variacoes_inteligentes(c))
