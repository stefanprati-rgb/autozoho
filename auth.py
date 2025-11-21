"""
Módulo de autenticação no Zoho Desk.

Responsabilidades:
- Detectar sessão ativa (evita login desnecessário)
- Preencher email/senha
- Aguardar OTP manual (com timeout)
- Restaurar/salvar cookies
- Retry em caso de falha
"""

import time
from typing import Optional

from loguru import logger
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from tenacity import retry, stop_after_attempt, wait_exponential

from config import SETTINGS, CONFIG
from core.driver import _salvar_cookies, _screenshot_fallback

# ---------- URLs ----------
try:
    ZOHO_DESK_BASE_URL = CONFIG.zoho.url.split("/agent")[0]
except Exception:
    ZOHO_DESK_BASE_URL = "https://desk.zoho.com"
ZOHO_ACCOUNTS_URL = "https://accounts.zoho.com/signin"

# ---------- Seletores ----------
LOGIN_SELECTORS = {
    "email_input": "input#login_id",
    "next_btn": "button#nextbtn",
    "password_input": "input#password",
    "otp_method_btn": "//div[contains(text(),'Insira a OTP com base em tempo')]",
    "problem_signin_btn": "div#problemsignin",
}

# ---------- Auxiliares ----------
def _esta_logado(driver) -> bool:
    """Detecta se já está logado verificando ícone de pesquisa do Desk."""
    try:
        driver.get(ZOHO_DESK_BASE_URL)
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'button[data-id="globalSearchIcon"]')
            )
        )
        logger.info("Sessão ativa detectada. Pulando login.")
        return True
    except TimeoutException:
        return False
    except Exception as e:
        logger.debug(f"Falha ao verificar sessão: {e!r}")
        return False


def _aguardar_otp_manual(driver) -> bool:
    """Aguarda o usuário inserir OTP no navegador até timeout."""
    timeout = getattr(CONFIG.timeouts, "login", 300)
    logger.info(f"Aguardando OTP manual (timeout {timeout//60} min)...")
    inicio = time.time()
    last_log = inicio

    while time.time() - inicio < timeout:
        try:
            if "accounts.zoho.com" not in driver.current_url:
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, 'button[data-id="globalSearchIcon"]')
                    )
                )
                logger.success("Login detectado (OTP inserido).")
                return True
        except TimeoutException:
            pass
        if time.time() - last_log > 30:
            logger.info("Ainda aguardando OTP...")
            last_log = time.time()
        time.sleep(2)

    logger.error("Timeout aguardando OTP manual.")
    return False


# ---------- Login principal ----------
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, max=30),
    reraise=True,
    before_sleep=lambda rs: logger.warning(
        f"Retry login (tentativa {rs.attempt_number})"
    ),
)
def fazer_login(driver) -> bool:
    """
    Executa o login completo no Zoho.
    Retorna:
        True  -> logado com sucesso
        False -> falha (timeout ou erro)
    """
    if _esta_logado(driver):
        return True

    logger.info("Iniciando login no Zoho...")
    driver.get(ZOHO_ACCOUNTS_URL)

    try:
        email_input = WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, LOGIN_SELECTORS["email_input"]))
        )
        email_input.send_keys(SETTINGS.zoho_email)
        driver.find_element(By.CSS_SELECTOR, LOGIN_SELECTORS["next_btn"]).click()
        logger.debug("Email inserido.")
    except Exception as e:
        logger.error(f"Falha ao inserir email: {e}")
        _screenshot_fallback("erro_email_login", driver)
        return False

    try:
        password_input = WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, LOGIN_SELECTORS["password_input"]))
        )
        password_input.send_keys(SETTINGS.zoho_senha)
        driver.find_element(By.CSS_SELECTOR, LOGIN_SELECTORS["next_btn"]).click()
        logger.debug("Senha inserida.")
    except Exception as e:
        logger.error(f"Falha ao inserir senha: {e}")
        _screenshot_fallback("erro_senha_login", driver)
        return False

    # OTP
    try:
        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, LOGIN_SELECTORS["otp_method_btn"]))
        ).click()
        logger.info("Selecionado método OTP por app autenticador.")
    except TimeoutException:
        logger.debug("Tela de OTP não apareceu (seguindo adiante).")

    if not _aguardar_otp_manual(driver):
        _screenshot_fallback("timeout_otp", driver)
        return False

    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-id="globalSearchIcon"]'))
        )
        logger.success("Login concluído com sucesso!")
        _salvar_cookies(driver)
        return True
    except TimeoutException:
        logger.error("Login não concluído - ícone de pesquisa não encontrado.")
        _screenshot_fallback("login_incompleto", driver)
        return False


# ---------- Context Manager ----------
class LoginManager:
    """Context manager para login automático e salvamento de cookies."""

    def __init__(self, driver):
        self.driver = driver
        self.logado = False

    def __enter__(self) -> bool:
        self.logado = fazer_login(self.driver)
        return self.logado

    def __exit__(self, exc_type, exc, tb):
        if self.logado:
            _salvar_cookies(self.driver)
        return False  # não suprime exceções