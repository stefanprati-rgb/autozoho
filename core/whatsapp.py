"""
core/whatsapp.py
Fluxos de envio via WhatsApp dentro do Zoho Desk.

- Abrir o canal "Enviar mensagens via WhatsApp (canal de IM)"
- Preencher/colar mensagem (com chunk se muito longa)
- Anexar arquivos (opcional)
- Enviar e confirmar envio
- Retries resilientes + screenshots em falha
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Iterable, List, Optional

from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

from core.actions import (
    click_safe,
    type_text,
    find_one,
    wait_visible,
    wait_clickable,
    scroll_into_view,
)

# ---------------------------------------------------------------------------
# Config com fallback (não quebra import-time)
# ---------------------------------------------------------------------------
try:
    from config import CONFIG
except Exception:
    class _Timeouts:
        search_wait = 15
        after_click = 20
        long = 45
    class _Whats:
        max_chunk_chars = 3000  # fatiamento seguro
        confirm_timeout = 25
    class _Cfg:
        timeouts = _Timeouts()
        whatsapp = _Whats()
    CONFIG = _Cfg()

# import tardio para evitar circularidade
def _screenshot_safe(name: str, driver: Optional[WebDriver]):
    try:
        from core.driver import _screenshot_fallback
        return _screenshot_fallback(name, driver)
    except Exception:
        return None

# ---------------------------------------------------------------------------
# Seletores centralizados
# (ajuste aqui se o Zoho alterar o DOM/nome do canal)
# ---------------------------------------------------------------------------
SEL = {
    "botao_whatsapp_menu": 'span[data-title="Enviar mensagens via WhatsApp (canal de IM)"]',
    "modal_container": 'div[data-zd-id="zd_im_chat"]',
    # caixa de texto dentro do modal
    "textbox_msg": 'div[data-zd-id="zd_im_chat"] div[contenteditable="true"]',
    # botão de anexar (clip) e input file
    "btn_anexar": 'div[data-zd-id="zd_im_chat"] button[title*="Anexar"]',
    "input_file": 'input[type="file"]',
    # botão enviar
    "btn_enviar": 'div[data-zd-id="zd_im_chat"] button[title*="Enviar"]',
    # confirmação visual de envio (um item de mensagem aparecendo do lado direito)
    "msg_enviada_bolha": 'div[data-zd-id="zd_im_chat"] div[class*="messageItem"] div[class*="right"]',
}

# ---------------------------------------------------------------------------
# Funções utilitárias
# ---------------------------------------------------------------------------
def _chunk_text(msg: str, max_chars: int) -> List[str]:
    """Divide mensagens muito longas em partes menores (evita falha no input)."""
    if not msg:
        return []
    m = max(512, max_chars)  # nunca menor que 512
    return [msg[i:i+m] for i in range(0, len(msg), m)]

def _assert_modal_aberto(driver: WebDriver) -> None:
    wait_visible(driver, SEL["modal_container"], timeout=getattr(CONFIG.timeouts, "search_wait", 15))


# ---------------------------------------------------------------------------
# Abertura do canal WhatsApp
# ---------------------------------------------------------------------------
@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, max=6), reraise=True)
def abrir_canal_whatsapp(driver: WebDriver) -> bool:
    """
    Abre o modal de envio do WhatsApp no perfil do contato.
    Pré-condição: você já deve estar na página do cliente (perfil/contato no Desk).
    """
    logger.info("🟢 Abrindo canal de WhatsApp (Zoho Desk)…")
    try:
        click_safe(
            driver,
            SEL["botao_whatsapp_menu"],
            timeout=getattr(CONFIG.timeouts, "search_wait", 15),
            after_click_wait=getattr(CONFIG.timeouts, "after_click", 20),
        )
        _assert_modal_aberto(driver)
        logger.success("Canal WhatsApp aberto.")
        return True
    except TimeoutException as e:
        logger.error(f"Não foi possível abrir o canal de WhatsApp: {e}")
        _screenshot_safe("abrir_canal_whatsapp_fail", driver)
        return False


# ---------------------------------------------------------------------------
# Anexos
# ---------------------------------------------------------------------------
def anexar_arquivos(driver: WebDriver, arquivos: Iterable[Path]) -> bool:
    """
    Anexa arquivos no modal aberto do WhatsApp. Ignora caminhos inexistentes.
    """
    paths = [Path(a) for a in arquivos or [] if a]
    paths = [p for p in paths if p.exists() and p.is_file()]
    if not paths:
        return True

    logger.info(f"📎 Anexando {len(paths)} arquivo(s).")
    try:
        # expõe input[type=file] (algumas vezes já está presente)
        try:
            click_safe(driver, SEL["btn_anexar"], timeout=8)
        except Exception:
            pass  # se não houver botão, tentamos achar o input direto

        inp = find_one(driver, SEL["input_file"], timeout=10)
        for p in paths:
            try:
                inp.send_keys(str(p.resolve()))
                time.sleep(0.3)
            except Exception as e:
                logger.warning(f"Falha ao anexar {p.name}: {e!r}")

        logger.debug("Arquivos enviados para o input de upload.")
        return True
    except Exception as e:
        logger.error(f"Erro ao anexar arquivos: {e!r}")
        _screenshot_safe("anexar_arquivos_fail", driver)
        return False


# ---------------------------------------------------------------------------
# Envio de mensagem (único chunk)
# ---------------------------------------------------------------------------
def _enviar_chunk(driver: WebDriver, texto: str) -> bool:
    try:
        # foca/coloca o texto
        type_text(
            driver,
            SEL["textbox_msg"],
            texto,
            timeout=getattr(CONFIG.timeouts, "search_wait", 15),
            clear=False,
            paste=True,  # mais resiliente para mensagens longas
        )
        # clica enviar
        click_safe(
            driver,
            SEL["btn_enviar"],
            timeout=getattr(CONFIG.timeouts, "search_wait", 15),
            after_click_wait=getattr(CONFIG.timeouts, "after_click", 20),
        )
        return True
    except TimeoutException as e:
        logger.error(f"Timeout ao enviar o chunk: {e}")
        _screenshot_safe("enviar_chunk_timeout", driver)
        return False
    except Exception as e:
        logger.error(f"Falha no envio do chunk: {e!r}")
        _screenshot_safe("enviar_chunk_fail", driver)
        return False


def _confirmar_envio(driver: WebDriver, timeout: Optional[int] = None) -> bool:
    """Confirma visualmente que a última mensagem apareceu no histórico."""
    to = timeout or getattr(getattr(CONFIG, "whatsapp", object()), "confirm_timeout", 25)
    try:
        wait_visible(driver, SEL["msg_enviada_bolha"], timeout=to)
        return True
    except TimeoutException:
        _screenshot_safe("confirmar_envio_timeout", driver)
        return False


# ---------------------------------------------------------------------------
# API principal: enviar mensagem (com anexos)
# ---------------------------------------------------------------------------
@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1.5, max=8), reraise=True)
def enviar_whatsapp(
    driver: WebDriver,
    mensagem: str,
    anexos: Optional[Iterable[Path]] = None,
    abrir_canal: bool = True,
    confirmar: bool = True,
) -> bool:
    """
    Envia uma mensagem (e anexos, se houver) no canal WhatsApp do Zoho Desk.

    Parâmetros:
      - abrir_canal: se True, tenta abrir o modal automaticamente
      - confirmar: se True, aguarda confirmação visual após o envio do último chunk

    Retorna:
      True em sucesso, False em falha.
    """
    # 1) abre o canal se necessário
    if abrir_canal:
        if not abrir_canal_whatsapp(driver):
            return False
    else:
        try:
            _assert_modal_aberto(driver)
        except TimeoutException:
            logger.warning("Modal WhatsApp não está aberto. Abrindo agora…")
            if not abrir_canal_whatsapp(driver):
                return False

    # 2) anexos primeiro (se houver)
    if anexos:
        if not anexar_arquivos(driver, anexos):
            logger.warning("Falha em anexar um ou mais arquivos (seguindo com mensagem).")

    # 3) mensagem (com fatiamento seguro)
    msg = (mensagem or "").strip()
    if not msg and not anexos:
        logger.warning("Nada para enviar (mensagem vazia e sem anexos).")
        return False

    max_chars = getattr(getattr(CONFIG, "whatsapp", object()), "max_chunk_chars", 3000)
    partes = _chunk_text(msg, max_chars) if msg else []
    logger.info(f"✉️ Enviando mensagem em {max(len(partes),1)} parte(s).")

    ultimo_ok = True
    for i, parte in enumerate(partes or [""] , 1):
        if parte:
            logger.debug(f"→ Enviando parte {i}/{len(partes)} ({len(parte)} chars)")
        ok = _enviar_chunk(driver, parte)
        if not ok:
            ultimo_ok = False
            break
        # opcional: pequena pausa entre partes para evitar throttling
        time.sleep(0.4)

    if not ultimo_ok:
        return False

    # 4) confirmação visual (última bolha do lado direito)
    if confirmar and (partes or anexos):
        if not _confirmar_envio(driver):
            logger.warning("Não foi possível confirmar visualmente o envio.")
            # não aborta necessariamente — pode ter sido enviado mesmo assim
            return False

    logger.success("✅ Mensagem enviada com sucesso.")
    return True


# ---------------------------------------------------------------------------
# Fechar modal (opcional)
# ---------------------------------------------------------------------------
def fechar_modal_whatsapp(driver: WebDriver) -> bool:
    """
    Fecha o modal (se houver X ou se ESC funcionar). Dependente do DOM;
    mantemos como best-effort.
    """
    try:
        # tentativas comuns: botão fechar no cabeçalho ou ESC
        try:
            # botão fechar genérico dentro do container do chat
            btn = find_one(driver, 'div[data-zd-id="zd_im_chat"] button[title*="Fechar"]', timeout=5)
            scroll_into_view(driver, btn)
            btn.click()
            return True
        except Exception:
            pass
        # ESC
        driver.execute_script("document.dispatchEvent(new KeyboardEvent('keydown', {key:'Escape'}));")
        time.sleep(0.3)
        return True
    except Exception as e:
        logger.debug(f"Falha ao fechar modal: {e!r}")
        return False


# ---------------------------------------------------------------------------
# Teste local de fatiamento (sem Selenium)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    long = "x" * 6500
    ch = _chunk_text(long, 3000)
    assert len(ch) == 3 and len(ch[0]) == 3000 and len(ch[1]) == 3000 and len(ch[2]) == 500
    print("✓ chunk_text ok")

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def selecionar_template_whatsapp(driver, nome_template: str, ancoras: list[str], timeout=15) -> bool:
    wait = WebDriverWait(driver, timeout)
    try:
        lbl = wait.until(EC.presence_of_element_located((By.XPATH, "//label[normalize-space()='Modelo de mensagem']")))
        inp = lbl.find_element(By.XPATH, ".//following::input[contains(@class,'secondarydropdown-textBox')][1]")
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", inp)
        try: inp.click()
        except: driver.execute_script("arguments[0].click();", inp)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//li[@role='option']")))
    except Exception as e:
        _screenshot_safe("template_dropdown_fail", driver)
        return False

    candidato = None
    # por nome exato
    try:
        cands = driver.find_elements(By.XPATH, f"//li[@role='option' and .//div[contains(@class,'listTitle') and normalize-space()='{nome_template}']]")
        cands = [c for c in cands if c.is_displayed()]
        if cands: candidato = cands[0]
    except: pass
    # por âncora
    if not candidato and ancoras:
        anc = ancoras[0].replace("'", "\\'")
        try:
            cands = driver.find_elements(By.XPATH, f"//li[@role='option' and contains(@data-title, '{anc}')]")
            cands = [c for c in cands if c.is_displayed()]
            if cands: candidato = cands[0]
        except: pass
    # por parcial
    if not candidato:
        itens = [e for e in driver.find_elements(By.XPATH, "//li[@role='option']") if e.is_displayed()]
        nm = (nome_template or "").strip().lower()
        for it in itens:
            try:
                t = (it.find_element(By.XPATH, ".//div[contains(@class,'listTitle')] ").text or "").strip().lower()
                if t == nm or nm in t or t in nm:
                    candidato = it; break
            except: continue

    if not candidato:
        _screenshot_safe("template_nao_encontrado", driver)
        return False

    try: candidato.click()
    except: driver.execute_script("arguments[0].click();", candidato)
    return True
