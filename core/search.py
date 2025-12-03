# -*- coding: utf-8 -*-
"""
Módulo de busca de clientes.
Replicado fielmente da versão v3.1 funcional (Lógica de Variações Inteligentes + Fuzzy).
Atualizado com Limpeza Nuclear de Campo de Busca.
"""

import time
import re
import logging
import unicodedata
import json
import os
from difflib import SequenceMatcher
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, StaleElementReferenceException
)

from core.messaging import clicar_seguro, fechar_ui_flutuante

# --- CONSTANTES DO SCRIPT V3.1 ---

SELETORES = {
    "icone_pesquisa": 'button[data-id="globalSearchIcon"]',
    "barra_pesquisa": 'input[data-id="searchInput"]',
    "msg_sem_resultados": 'div.zd_v2-commonemptystate-title',
    "botao_whatsapp": 'span[data-title="Enviar mensagens via WhatsApp (canal de IM)"]'
}

STOPWORDS_NOME = {
    "de","da","do","das","dos","e","d","jr","jr.","junior","júnior","filho","neto","sobrinho",
    "me","epp","s/a","sa","s.a","s.a.","ltda","ltda.","holding","group","grupogera"
}

SOBRENOMES_COMUNS_IGNORAR = {
    "silva", "santos", "souza", "oliveira", "pereira", "lima", "ferreira",
    "costa", "rodrigues", "almeida", "nascimento", "gomes", "martins",
    "araujo", "melo", "barbosa", "cardoso", "teixeira", "dias", "vieira",
    "batista", "jesus", "alves", "ramores", "lopes"
}

EMPRESA_PALAVRAS_DESCARTAR = {
    "ltda","ltda.","me","epp","eireli","s/a","sa","s.a","s.a.","holding","associação","associacao",
    "associacão","condomínio","condominio","condominios","residencial","edificio","edifício",
    "centro","clínica","clinica","auto","automotivo","empresa","comercial","industria","industrial",
    "cooperativa","igreja","paróquia","paroquia","sindicato","escola","faculdade","universidade",
    "energy", "energia", "servicos", "serviços"
}

FUZZY_MATCH_THRESHOLD = 0.85
FUZZY_MATCH_PRIMEIRO_ULTIMO = 0.85

# Pesos para Score Composto
SCORE_PESO_JACCARD = 0.40
SCORE_PESO_FUZZY_TOKENS = 0.40
SCORE_PESO_POSICIONAL = 0.20

# Delays de digitação (para simular humano e evitar erros de JS)
DELAY_DIGITACAO_CURTA = 0.02
DELAY_DIGITACAO_MEDIA = 0.03
DELAY_DIGITACAO_LONGA = 0.04

# --- SISTEMA DE CACHE DE DECISÕES (APRENDIZADO) ---
MAPEAMENTOS_JSON = 'mapeamentos_decisoes.json'

def _carregar_cache_decisoes():
    try:
        if os.path.exists(MAPEAMENTOS_JSON):
            with open(MAPEAMENTOS_JSON, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def _salvar_cache_decisoes(cache: dict):
    try:
        with open(MAPEAMENTOS_JSON, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.warning(f"Falha ao salvar cache de decisões: {e}")

def _registrar_decisao_manual(entrada_norm: str, via: str, nome_exibicao: str):
    cache = _carregar_cache_decisoes()
    item = cache.get(entrada_norm, {"via": via, "nome_exibicao": nome_exibicao, "contagem": 0})
    item["via"] = via
    item["nome_exibicao"] = nome_exibicao
    item["contagem"] = int(item.get("contagem", 0)) + 1
    cache[entrada_norm] = item
    _salvar_cache_decisoes(cache)

# --- FUNÇÕES AUXILIARES DE TEXTO (IDÊNTICAS AO V3.1) ---

def normalizar_nome(nome, remover_invalidos=False):
    try:
        nome = str(nome)
        if remover_invalidos:
            nome = nome.replace('\ufffd', ' ')
            nome = re.sub(r'[^\w\s-]', ' ', nome) 
        nfkd = unicodedata.normalize('NFKD', nome).encode('ascii', 'ignore').decode('utf-8', 'ignore')
        nome_limpo = re.sub(r'[^\w\s-]', '', nfkd).lower()
        return ' '.join(nome_limpo.split())
    except:
        return (nome.lower().strip() if nome else "")

def _sanear_termo_busca(s: str) -> str:
    if not s: return s
    s = s.replace('\ufffd', ' ')
    toks = re.split(r"\s+", s.strip())
    toks_limpos = [t for t in toks if len(t) >= 3 and t.lower() not in STOPWORDS_NOME]
    resultado = " ".join(toks_limpos)
    return resultado if len(resultado) >= 3 else ""

def _tokens_nome(s: str) -> list:
    if not s: return []
    s_norm = normalizar_nome(s, remover_invalidos=True)
    tokens = [re.sub(r"[^a-z0-9-]", "", tok) for tok in s_norm.split()]
    return [t for t in tokens if t and len(t) >= 3 and t not in STOPWORDS_NOME]

def _limpa_sufixos_empresa(s: str):
    s_norm = normalizar_nome(s, remover_invalidos=True)
    toks = [t for t in re.split(r"\s+", s_norm) if t]
    toks = [t for t in toks if t not in EMPRESA_PALAVRAS_DESCARTAR]
    return " ".join(toks).strip()

def classificar_pf_ou_pj(nome_norm: str) -> str:
    if not nome_norm: return "PF"
    toks = [t for t in nome_norm.split() if t]
    corporativos = [t for t in toks if t in EMPRESA_PALAVRAS_DESCARTAR]
    return "PJ" if len(corporativos) >= 2 else "PF"

# --- LÓGICA DE SCORES E FUZZY (V3.1) ---

def _token_nuclear_pj(tokens: list) -> set:
    base = []
    for t in tokens:
        if t in EMPRESA_PALAVRAS_DESCARTAR or t in STOPWORDS_NOME or len(t) < 3: continue
        base.append(t)
    genericos = {"auto", "automotivo", "centro", "clínica", "clinica", "residencial", "servicos", "serviço", "servico", "assistencia"}
    return {t for t in base if t not in genericos}

def calcular_fuzzy_score(nome_resultado_norm: str, nome_original_norm: str) -> dict:
    if not nome_resultado_norm or not nome_original_norm:
        return {'match': False, 'ratio': 0.0}
    try:
        ratio_geral = SequenceMatcher(None, nome_resultado_norm, nome_original_norm).ratio()
        if ratio_geral <= FUZZY_MATCH_THRESHOLD:
            return {'match': False, 'ratio': ratio_geral}
        
        toks_res = [t for t in nome_resultado_norm.split() if t not in STOPWORDS_NOME]
        toks_orig = [t for t in nome_original_norm.split() if t not in STOPWORDS_NOME]

        if not toks_res or not toks_orig:
            return {'match': False, 'ratio': ratio_geral}

        ratio_primeiro = SequenceMatcher(None, toks_res[0], toks_orig[0]).ratio()
        ratio_ultimo = SequenceMatcher(None, toks_res[-1], toks_orig[-1]).ratio()

        match = (ratio_primeiro > FUZZY_MATCH_PRIMEIRO_ULTIMO and ratio_ultimo > FUZZY_MATCH_PRIMEIRO_ULTIMO)
        return { 'match': match, 'ratio': ratio_geral }
    except:
        return {'match': False, 'ratio': 0.0}

def _limiar_dinamico_auto(tipo, qtd_resultados_coletados, ratio_geral, nome_busca_norm, nome_res_norm):
    base = FUZZY_MATCH_PRIMEIRO_ULTIMO
    if tipo == "PJ":
        toks_b = [t for t in nome_busca_norm.split() if t]
        toks_r = [t for t in nome_res_norm.split() if t]
        if _token_nuclear_pj(toks_b).intersection(_token_nuclear_pj(toks_r)):
            base -= 0.05
    else:
        toks_b = [t for t in nome_busca_norm.split() if t]
        if toks_b and toks_b[-1] in SOBRENOMES_COMUNS_IGNORAR:
            base += 0.03
    if qtd_resultados_coletados <= 3:
        base -= 0.03
    return max(0.70, min(0.95, base))

def calcular_score_composto(nome_resultado_norm, nome_busca_norm):
    if not nome_resultado_norm or not nome_busca_norm: return 0.0
    return SequenceMatcher(None, nome_resultado_norm, nome_busca_norm).ratio()

# --- FUNÇÃO PRINCIPAL DE BUSCA (V3.1) ---

def buscar_e_abrir_cliente(driver, cliente_input):
    """
    Lógica de busca idêntica ao V3.1: Coleta resultados, tenta match automático e fallback manual.
    """
    # Suporta string ou dict (compatibilidade)
    nome_cliente = cliente_input.get('busca', cliente_input) if isinstance(cliente_input, dict) else cliente_input
    
    wait = WebDriverWait(driver, 15)
    short_wait = WebDriverWait(driver, 5)
    
    instabilidade_zoho = 0
    
    def calcular_timeout_adaptativo(base):
        return base * 2 if instabilidade_zoho >= 3 else base

    # Verifica Cache
    nome_original_norm = normalizar_nome(nome_cliente, remover_invalidos=True)
    cache = _carregar_cache_decisoes()
    if nome_original_norm in cache:
        m = cache[nome_original_norm]
        logging.info(f"💾 Usando mapeamento aprendido: '{m['nome_exibicao']}'")
        if _executar_busca_e_clicar(driver, wait, m['via'], m['nome_exibicao']):
            return True

    # Geração de Variações
    def gerar_variacoes_inteligentes(nome_original):
        variacoes = []
        nome_limpo_empresa = _limpa_sufixos_empresa(nome_original)
        toks = _tokens_nome(nome_limpo_empresa)
        
        if not toks:
            saneado = _sanear_termo_busca(normalizar_nome(nome_limpo_empresa, remover_invalidos=True))
            return [saneado] if saneado else []

        if len(toks) >= 2: variacoes.append(f"{toks[0]} {toks[1]}")
        if len(toks) >= 2: variacoes.append(f"{toks[0]} {toks[-1]}")
        
        ultimo = toks[-1]
        if len(ultimo) >= 3 and ultimo not in SOBRENOMES_COMUNS_IGNORAR:
            variacoes.append(ultimo)
            
        if len(toks) >= 3: variacoes.append(" ".join(toks))
        if len(toks[0]) >= 3: variacoes.append(toks[0])
        if len(toks) >= 3: variacoes.append(f"{toks[-2]} {toks[-1]}")

        saneado = _sanear_termo_busca(normalizar_nome(nome_limpo_empresa, remover_invalidos=True))
        if saneado: variacoes.append(saneado)
        
        if len(ultimo) >= 3 and ultimo in SOBRENOMES_COMUNS_IGNORAR:
            variacoes.append(ultimo)

        uniq = list(dict.fromkeys(variacoes))
        return [u for u in (_sanear_termo_busca(u) for u in uniq) if u and len(u) >= 3][:10]

    variacoes = gerar_variacoes_inteligentes(nome_cliente)
    logging.info(f"🔍 Buscando '{nome_cliente}' com {len(variacoes)} variações: {variacoes}")
    
    todos_resultados = {}

    for tentativa, nome_busca in enumerate(variacoes, 1):
        try:
            # 1. Interação com Barra de Pesquisa
            try:
                barra = short_wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, SELETORES["barra_pesquisa"])))
            except:
                if not clicar_seguro(driver, wait, By.CSS_SELECTOR, SELETORES["icone_pesquisa"]): continue
                barra = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, SELETORES["barra_pesquisa"])))

            # --- LIMPEZA NUCLEAR DE CAMPO ---
            # Garante que o campo esteja realmente vazio antes de digitar
            campo_limpo = False
            for _ in range(3): # Tenta até 3 vezes limpar se falhar
                barra.click()
                time.sleep(0.1)
                
                # 1. JS Force Clear + Event Dispatch (Crucial para React/Zoho)
                driver.execute_script("""
                    arguments[0].value = '';
                    arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                """, barra)
                
                # 2. Teclado Físico (Redundância)
                barra.send_keys(Keys.CONTROL, "a")
                barra.send_keys(Keys.DELETE)
                
                # 3. Verificação
                valor_atual = barra.get_attribute("value")
                if not valor_atual:
                    campo_limpo = True
                    break
                else:
                    logging.warning(f"⚠️ Campo de busca teimoso: '{valor_atual}'. Tentando limpar novamente...")
                    # Backspace agressivo se sobrar lixo
                    for _ in range(len(valor_atual) + 2):
                        barra.send_keys(Keys.BACKSPACE)
            
            if not campo_limpo:
                logging.error("❌ Não foi possível limpar o campo de busca. Pulando variação.")
                continue
            # --------------------------------

            # Digitação
            delay = DELAY_DIGITACAO_CURTA if len(nome_busca) <= 5 else DELAY_DIGITACAO_MEDIA
            for char in nome_busca:
                barra.send_keys(char)
                time.sleep(delay)
            
            # Validação final antes do ENTER
            if barra.get_attribute("value").strip() != nome_busca:
                # Se o JS do site sobrescreveu, forçamos de novo
                driver.execute_script("arguments[0].value = arguments[1];", barra, nome_busca)
            
            barra.send_keys(Keys.ENTER)
            
            # Fechar alerta termo curto
            try:
                alerta = WebDriverWait(driver, 1.5).until(EC.presence_of_element_located((By.XPATH, "//div[contains(., 'forneça pelo menos 2 letras')]")))
                driver.execute_script("arguments[0].remove()", alerta)
                continue
            except: pass

            # 2. Aguardar Resultados
            try:
                WebDriverWait(driver, calcular_timeout_adaptativo(15)).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-title]")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, SELETORES["msg_sem_resultados"]))
                    )
                )
            except TimeoutException:
                instabilidade_zoho += 1
                continue

            # 3. Processar Resultados
            lista_res = driver.find_elements(By.CSS_SELECTOR, "a[data-title]")
            if not lista_res: continue

            nome_busca_norm = normalizar_nome(nome_busca, remover_invalidos=True)

            for link in lista_res:
                try:
                    nome_res = link.get_attribute("data-title") or link.text
                    if not nome_res: continue
                    
                    nome_res_norm = normalizar_nome(nome_res, remover_invalidos=True)
                    
                    # Match Exato
                    if nome_res_norm == nome_original_norm:
                        logging.info(f"✅ Match EXATO: '{nome_res}'")
                        clicar_resultado(driver, link)
                        return True
                    
                    # Match Fuzzy
                    fuzzy = calcular_fuzzy_score(nome_res_norm, nome_original_norm)
                    tipo = classificar_pf_ou_pj(nome_original_norm)
                    thr = _limiar_dinamico_auto(tipo, len(todos_resultados), fuzzy['ratio'], nome_busca_norm, nome_res_norm)
                    
                    if fuzzy['ratio'] >= thr:
                        logging.info(f"✅ Match FUZZY ({fuzzy['ratio']:.2f}): '{nome_res}'")
                        clicar_resultado(driver, link)
                        return True
                    
                    # Coleta parcial
                    score_comp = calcular_score_composto(nome_res_norm, nome_busca_norm)
                    if score_comp >= 0.5:
                        if nome_res_norm not in todos_resultados or todos_resultados[nome_res_norm]['score'] < score_comp:
                            todos_resultados[nome_res_norm] = {
                                'nome_exibicao': nome_res,
                                'score': score_comp,
                                'busca_origem': nome_busca
                            }
                except StaleElementReferenceException:
                    continue

        except Exception as e:
            logging.error(f"Erro na busca '{nome_busca}': {e}")
            fechar_ui_flutuante(driver)

    # Fallback Manual
    if not todos_resultados:
        logging.warning(f"❌ Cliente '{nome_cliente}' não encontrado.")
        return False

    # Se não rodar headless, poderia perguntar ao usuário aqui.
    # Como é automação, pegamos o melhor score se for alto o suficiente
    melhor = max(todos_resultados.values(), key=lambda x: x['score'])
    if melhor['score'] > 0.8:
        logging.info(f"⚠️ Usando melhor match parcial: '{melhor['nome_exibicao']}'")
        return _executar_busca_e_clicar(driver, wait, melhor['busca_origem'], melhor['nome_exibicao'])
    
    logging.warning(f"❌ Nenhum match confiável. Melhores candidatos: {[v['nome_exibicao'] for v in list(todos_resultados.values())[:3]]}")
    return False

def clicar_resultado(driver, elemento):
    """
    Clica no nome do cliente (e NÃO no e-mail).
    Identifica o nome pelo atributo data-type, ou descarta links que contenham '@'.
    Prioriza links com espaço no texto (típico de "Nome Sobrenome").
    """
    try:
        # 🔍 1. Encontrar a linha
        try:
            linha = elemento.find_element(By.XPATH, "./ancestor::tr[1]")
        except:
            try:
                linha = elemento.find_element(By.XPATH, "./ancestor::*[contains(@class, 'row')][1]")
            except:
                linha = elemento.find_element(By.XPATH, "./ancestor::*[.//a][1]")

        # 🔍 2. Tentar encontrar link cujo data-type indique NOME
        try:
            nome_element = linha.find_element(
                By.XPATH,
                ".//a[@data-type and not(contains(@data-title, '@'))]"
            )
        except:
            # 🔍 3. Fallback 1: link sem '@' e com ESPAÇO no texto (ex.: 'João Silva')
            try:
                nome_element = linha.find_element(
                    By.XPATH,
                    ".//a[not(contains(normalize-space(.), '@')) and contains(normalize-space(.), ' ')]"
                )
            except:
                # 🔍 4. Fallback 2: procura manualmente, priorizando nomes com espaço
                anchors = linha.find_elements(By.XPATH, ".//a")
                nome_element = None

                # 4b) Primeiro, sem '@' E com espaço
                for a in anchors:
                    txt = (a.text or "").strip()
                    if txt and "@" not in txt and " " in txt:
                        nome_element = a
                        break

                # 4b) Se ainda não achou, qualquer link sem '@'
                if nome_element is None:
                    for a in anchors:
                        txt = (a.text or "").strip()
                        if txt and "@" not in txt:
                            nome_element = a
                            break

                # 4c) Último recurso: primeiro link disponível
                if nome_element is None and anchors:
                    nome_element = anchors[0]

        # 🔥 5. Clicar no nome
        try:
            nome_element.click()
        except:
            driver.execute_script("arguments[0].click();", nome_element)

        logging.info("✅ Clicou no NOME do cliente corretamente")

    except Exception as e:
        logging.warning(f"⚠️ Falhou ao clicar no nome, usando fallback: {e}")
        try:
            elemento.click()
        except:
            driver.execute_script("arguments[0].click();", elemento)

    # 🔄 6. Aguardar página carregar
    try:
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, SELETORES["botao_whatsapp"]))
        )
    except:
        pass


def _executar_busca_e_clicar(driver, wait, termo, nome_alvo):
    """Re-executa a busca para clicar num alvo específico."""
    try:
        barra = driver.find_element(By.CSS_SELECTOR, SELETORES["barra_pesquisa"])
        barra.click()
        driver.execute_script("arguments[0].value = '';", barra)
        barra.send_keys(termo + Keys.ENTER)
        
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, f"a[data-title='{nome_alvo}']")))
        link = driver.find_element(By.CSS_SELECTOR, f"a[data-title='{nome_alvo}']")
        clicar_resultado(driver, link)
        return True
    except Exception as e:
        logging.error(f"Erro no clique manual: {e}")
        return False