"""
core/tickets.py
Ações de ticket no Zoho Desk.

- Abrir ticket por ID
- Criar ticket (assunto, descrição, contato, departamento, prioridade, status)
- Atualizar campos customizados
- Adicionar comentário (interno/externo) + anexos
- Alterar status e adicionar tags
- Obter informações do ticket atual
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, Iterable, Optional, List

from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from selenium.webdriver.remote.webdriver import WebDriver

from core.actions import (
    click_safe,
    type_text,
    find_one,
    find_all,
    wait_visible,
    wait_clickable,
    scroll_into_view,
)

# ---------------------------------------------------------------------------
# Config com fallback
# ---------------------------------------------------------------------------
try:
    from config import CONFIG
except Exception:
    class _Timeouts:
        search_wait = 15
        after_click = 20
        long = 45
    class _Zoho:
        desk_base = "https://desk.zoho.com"
        dept_padrao = None
    class _Cfg:
        timeouts = _Timeouts()
        zoho = _Zoho()
    CONFIG = _Cfg()

def _screenshot_safe(name: str, driver: Optional[WebDriver]):
    try:
        from core.driver import _screenshot_fallback
        return _screenshot_fallback(name, driver)
    except Exception:
        return None

# ---------------------------------------------------------------------------
# Seletores centralizados
# ---------------------------------------------------------------------------
SEL = {
    # navegação
    "search_input": 'input[data-id="globalSearchInput"]',
    "search_btn":   'button[data-id="globalSearchIcon"]',
    "search_result_ticket": 'a[data-type="TICKET"][data-title]',  # resultados de ticket
    # criação
    "novo_ticket_btn": 'button[data-id="newTicket"]',
    "modal_ticket": 'div[data-zd-id="zd_ticket_create"]',
    "campo_assunto": 'div[data-zd-id="zd_ticket_create"] input[name="subject"]',
    "campo_descricao": 'div[data-zd-id="zd_ticket_create"] div[contenteditable="true"]',
    "campo_contato": 'div[data-zd-id="zd_ticket_create"] input[name="contact"]',
    "campo_departamento": 'div[data-zd-id="zd_ticket_create"] input[name="department"]',
    "campo_prioridade": 'div[data-zd-id="zd_ticket_create"] input[name="priority"]',
    "campo_status": 'div[data-zd-id="zd_ticket_create"] input[name="status"]',
    "dropdown_opcao": 'div[role="listbox"] div[role="option"]',
    "btn_criar": 'div[data-zd-id="zd_ticket_create"] button[type="submit"]',
    # tela do ticket
    "view_ticket_container": 'div[data-zd-id="zd_ticket_detail"]',
    "header_ticket_id": 'div[data-zd-id="zd_ticket_detail"] [data-id="ticketId"]',
    "header_status": 'div[data-zd-id="zd_ticket_detail"] [data-id="ticketStatus"]',
    "header_tags": 'div[data-zd-id="zd_ticket_detail"] [data-id="ticketTags"]',
    "btn_editar": 'button[data-id="editTicket"]',
    "form_edicao": 'div[data-zd-id="zd_ticket_edit"]',
    "btn_salvar_edicao": 'div[data-zd-id="zd_ticket_edit"] button[type="submit"]',
    # comentário
    "tab_conversa": 'button[data-id="tabConversations"]',
    "comentario_editor": 'div[data-zd-id="composer"] div[contenteditable="true"]',
    "comentario_toggle_interno": 'button[title*="Comentário interno"]',
    "comentario_btn_enviar": 'button[data-id="sendReply"]',
    "comentario_input_file": 'input[type="file"]',
    # campos genéricos
    "campo_texto_generico": 'div[data-zd-id="zd_ticket_edit"] input[name="{}"]',
    "campo_rich_generico": 'div[data-zd-id="zd_ticket_edit"] div[contenteditable="true"][data-field="{}"]',
    "campo_dropdown_generico": 'div[data-zd-id="zd_ticket_edit"] input[name="{}"]',
    # status inline (no header)
    "status_header_btn": 'button[data-id="ticketStatusDropdown"]',
    "status_opcao": 'div[role="listbox"] div[role="option"]',
    # tags
    "tags_btn": 'button[data-id="tagsEdit"]',
    "tags_input": 'input[data-id="tagsInput"]',
    "tags_chip": 'div[data-id="tagsChips"] div[role="listitem"]',
    "tags_salvar": 'button[data-id="tagsSave"]',
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _desk_url() -> str:
    try:
        return CONFIG.zoho.url.split("/agent")[0]
    except Exception:
        return getattr(CONFIG.zoho, "desk_base", "https://desk.zoho.com")

def _tickets_url() -> str:
    base = _desk_url()
    return f"{base}/agent/tickets"

def _abrir_dropdown_e_escolher(driver: WebDriver, input_selector: str, valor: str) -> None:
    # tipo-ahead: digita valor e seleciona primeira opção correspondente
    type_text(driver, input_selector, valor, paste=True)
    time.sleep(0.25)
    # espera lista e clica primeira opção que contem o termo
    opts = find_all(driver, SEL["dropdown_opcao"], require_non_empty=True, must_be_visible=True)
    alvo = None
    for o in opts:
        if valor.lower() in (o.text or "").lower():
            alvo = o
            break
    (alvo or opts[0]).click()

def _map_status(status: str) -> str:
    # Adeque aos labels do seu Zoho (ex.: Aberto, Em Progresso, Pendente, Fechado)
    s = (status or "").strip().lower()
    mapping = {
        "novo": "Novo",
        "aberto": "Aberto",
        "em progresso": "Em Progresso",
        "pendente": "Pendente",
        "fechado": "Fechado",
        "resolvido": "Resolvido",
    }
    return mapping.get(s, status)

def _anexar_no_comentario(driver: WebDriver, arquivos: Iterable[Path]) -> None:
    paths = [Path(a) for a in arquivos or [] if a]
    paths = [p for p in paths if p.exists() and p.is_file()]
    if not paths:
        return
    try:
        inp = find_one(driver, SEL["comentario_input_file"], timeout=8)
        for p in paths:
            inp.send_keys(str(p.resolve()))
            time.sleep(0.2)
    except Exception as e:
        logger.warning(f"Falha ao anexar arquivo no comentário: {e!r}")

# ---------------------------------------------------------------------------
# Ações
# ---------------------------------------------------------------------------
@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, max=6), reraise=True)
def abrir_ticket_por_id(driver: WebDriver, ticket_id: str) -> bool:
    """
    Abre um ticket existente pelo ID (ex.: #123).
    """
    url = _tickets_url()
    try:
        driver.get(url)
        type_text(driver, SEL["search_input"], ticket_id, paste=True)
        click_safe(driver, SEL["search_btn"], after_click_wait=getattr(CONFIG.timeouts, "after_click", 20))
        wait_visible(driver, SEL["search_result_ticket"])
        itens = find_all(driver, SEL["search_result_ticket"], require_non_empty=True)
        itens_list = list(itens)
        alvo = None
        for it in itens_list:
            tt = it.get_attribute("data-title") or it.text
            if ticket_id.replace("#", "") in (tt or ""):
                alvo = it
                break
        (alvo or itens_list[0]).click()
        wait_visible(driver, SEL["view_ticket_container"], timeout=getattr(CONFIG.timeouts, "long", 45))
        logger.success(f"Ticket {ticket_id} aberto.")
        return True
    except Exception as e:
        logger.error(f"Falha ao abrir ticket {ticket_id}: {e!r}")
        _screenshot_safe("abrir_ticket_por_id_fail", driver)
        return False

@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, max=8), reraise=True)
def criar_ticket(
    driver: WebDriver,
    contato: Optional[str],
    assunto: str,
    descricao: str = "",
    departamento: Optional[str] = None,
    prioridade: Optional[str] = None,
    status: Optional[str] = None,
) -> bool:
    """
    Cria um ticket básico. Pré-requisito: estar no módulo Tickets.
    Retorna True se criado e view aberta.
    """
    try:
        # abrir diálogo
        click_safe(driver, SEL["novo_ticket_btn"], timeout=getattr(CONFIG.timeouts, "search_wait", 15))
        wait_visible(driver, SEL["modal_ticket"])

        # contato
        if contato:
            type_text(driver, SEL["campo_contato"], contato, paste=True)
            time.sleep(0.2)
            # escolhe a primeira opção
            _abrir_dropdown_e_escolher(driver, SEL["campo_contato"], contato)

        # assunto / descrição
        type_text(driver, SEL["campo_assunto"], assunto, paste=True)
        if descricao:
            type_text(driver, SEL["campo_descricao"], descricao, paste=True)

        # departamento/prioridade/status
        if departamento or getattr(CONFIG.zoho, "dept_padrao", None):
            _abrir_dropdown_e_escolher(driver, SEL["campo_departamento"], departamento or CONFIG.zoho.dept_padrao)
        if prioridade:
            _abrir_dropdown_e_escolher(driver, SEL["campo_prioridade"], prioridade)
        if status:
            _abrir_dropdown_e_escolher(driver, SEL["campo_status"], _map_status(status))

        # criar
        click_safe(driver, SEL["btn_criar"], timeout=10, after_click_wait=getattr(CONFIG.timeouts, "after_click", 20))
        wait_visible(driver, SEL["view_ticket_container"], timeout=getattr(CONFIG.timeouts, "long", 45))
        logger.success("Ticket criado com sucesso.")
        return True
    except Exception as e:
        logger.error(f"Erro ao criar ticket: {e!r}")
        _screenshot_safe("criar_ticket_fail", driver)
        return False

@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, max=6), reraise=True)
def atualizar_campos_ticket(driver: WebDriver, campos: Dict[str, str]) -> bool:
    """
    Abre o modo de edição e atualiza campos (inclui customizados se mapeados por 'name').
    Ex.: {"cf_numero_pedido": "123", "priority": "Alta"}
    """
    try:
        click_safe(driver, SEL["btn_editar"], timeout=8)
        wait_visible(driver, SEL["form_edicao"], timeout=10)

        for name, valor in (campos or {}).items():
            if not valor:
                continue
            # tentamos como dropdown (type-ahead); se falhar, tentamos texto
            try:
                type_text(driver, SEL["campo_dropdown_generico"].format(name), valor, paste=True)
                time.sleep(0.2)
                _abrir_dropdown_e_escolher(driver, SEL["campo_dropdown_generico"].format(name), valor)
                continue
            except Exception:
                pass
            # campo texto simples
            try:
                type_text(driver, SEL["campo_texto_generico"].format(name), valor, paste=True)
                continue
            except Exception:
                pass
            # campo rich text (caso mapeado por data-field)
            try:
                type_text(driver, SEL["campo_rich_generico"].format(name), valor, paste=True, clear=True)
            except Exception as e:
                logger.debug(f"Campo '{name}' não atualizado ({e!r})")

        click_safe(driver, SEL["btn_salvar_edicao"], timeout=8, after_click_wait=getattr(CONFIG.timeouts, "after_click", 20))
        wait_visible(driver, SEL["view_ticket_container"], timeout=20)
        logger.success("Campos do ticket atualizados.")
        return True
    except Exception as e:
        logger.error(f"Falha ao atualizar campos: {e!r}")
        _screenshot_safe("atualizar_campos_ticket_fail", driver)
        return False

@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, max=6), reraise=True)
def adicionar_comentario(
    driver: WebDriver,
    texto: str,
    interno: bool = True,
    anexos: Optional[Iterable[Path]] = None,
) -> bool:
    """
    Adiciona um comentário no ticket (padrão: interno).
    """
    try:
        click_safe(driver, SEL["tab_conversa"], timeout=8)
        wait_visible(driver, SEL["comentario_editor"], timeout=10)

        # interno/externo
        if interno:
            try:
                click_safe(driver, SEL["comentario_toggle_interno"], timeout=5)
            except Exception:
                pass

        # anexos (opcional)
        if anexos:
            _anexar_no_comentario(driver, anexos)

        # texto e enviar
        type_text(driver, SEL["comentario_editor"], texto, paste=True, clear=True)
        click_safe(driver, SEL["comentario_btn_enviar"], timeout=8, after_click_wait=getattr(CONFIG.timeouts, "after_click", 20))
        logger.success("Comentário adicionado.")
        return True
    except Exception as e:
        logger.error(f"Erro ao adicionar comentário: {e!r}")
        _screenshot_safe("adicionar_comentario_fail", driver)
        return False

@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, max=6), reraise=True)
def definir_status(driver: WebDriver, status: str) -> bool:
    """
    Altera o status do ticket via dropdown do header.
    """
    try:
        click_safe(driver, SEL["status_header_btn"], timeout=6)
        wait_visible(driver, SEL["status_opcao"], timeout=6)
        # escolhe opção correspondente
        alvo_txt = _map_status(status)
        for opt in find_all(driver, SEL["status_opcao"], require_non_empty=True, must_be_visible=True):
            if alvo_txt.lower() in (opt.text or "").lower():
                scroll_into_view(driver, opt)
                opt.click()
                break
        time.sleep(0.3)
        logger.success(f"Status alterado para '{alvo_txt}'.")
        return True
    except Exception as e:
        logger.error(f"Falha ao definir status '{status}': {e!r}")
        _screenshot_safe("definir_status_fail", driver)
        return False

@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, max=6), reraise=True)
def adicionar_tags(driver: WebDriver, tags: Iterable[str]) -> bool:
    """
    Adiciona (ou mantém) tags no ticket aberto.
    """
    ts = [t.strip() for t in (tags or []) if t and t.strip()]
    if not ts:
        return True
    try:
        click_safe(driver, SEL["tags_btn"], timeout=6)
        inp = wait_visible(driver, SEL["tags_input"], timeout=8)
        for t in ts:
            type_text(driver, SEL["tags_input"], t, paste=True)
            inp.send_keys("\n")
            time.sleep(0.1)
        click_safe(driver, SEL["tags_salvar"], timeout=6)
        logger.success(f"Tags aplicadas: {', '.join(ts)}")
        return True
    except Exception as e:
        logger.error(f"Falha ao adicionar tags: {e!r}")
        _screenshot_safe("adicionar_tags_fail", driver)
        return False

def obter_info_ticket(driver: WebDriver) -> Dict[str, str]:
    """
    Coleta informações básicas do ticket em exibição (best-effort).
    """
    info: Dict[str, str] = {}
    try:
        container = wait_visible(driver, SEL["view_ticket_container"], timeout=10)
        tid = find_one(driver, SEL["header_ticket_id"], timeout=6).text
        st = find_one(driver, SEL["header_status"], timeout=6).text
        tg = ""
        try:
            tg = " ".join([c.text for c in find_all(driver, SEL["tags_chip"], require_non_empty=False)])
        except Exception:
            pass
        info = {"ticket_id": tid, "status": st, "tags": tg}
    except Exception as e:
        logger.debug(f"Falha ao obter info do ticket: {e!r}")
        _screenshot_safe("obter_info_ticket_warn", driver)
    return info
