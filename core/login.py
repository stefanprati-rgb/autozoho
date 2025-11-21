# -*- coding: utf-8 -*-
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, InvalidSessionIdException

# Tenta importar de config, senão usa fallback
try:
    from config.constants import ZOHO_EMAIL, ZOHO_SENHA, URL_ZOHO_DESK
except ImportError:
    # Fallback de credenciais (Preenche se o config falhar)
    ZOHO_EMAIL = "seu_email@exemplo.com"
    ZOHO_SENHA = "sua_senha"
    URL_ZOHO_DESK = "https://desk.zoho.com/agent/"

SELETORES_LOGIN = {
    "login_email_input": 'input#login_id',
    "login_next_btn": 'button#nextbtn',
    "login_password_input": 'input#password',
    "login_problem_btn": 'div#problemsignin',
    "login_otp_method_btn": "//div[contains(text(), 'Insira a OTP com base em tempo')]",
}

SELETORES_APLICACAO = {
    "icone_pesquisa": 'button[data-id="globalSearchIcon"]',
}

TIMEOUT_LOGIN_MANUAL_SEGUNDOS = 900  # 15 minutos

def fazer_login(driver):
    """Executa o login no Zoho Desk."""
    try:
        if verificar_sessao_ativa(driver):
            return True
        
        driver.get(URL_ZOHO_DESK)
        logging.info("Navegando para login...")
        
        if not inserir_email(driver): return False
        inserir_senha(driver)
        configurar_otp(driver)
        
        if not aguardar_login_manual(driver): return False
        
        return verificar_login_bem_sucedido(driver)
    except Exception as e:
        logging.error(f"Erro no login: {e}")
        return False

def verificar_sessao_ativa(driver):
    try:
        WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.CSS_SELECTOR, SELETORES_APLICACAO["icone_pesquisa"])))
        logging.info("Sessão já ativa.")
        return True
    except TimeoutException:
        return False

def inserir_email(driver):
    try:
        wait = WebDriverWait(driver, 10)
        email = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, SELETORES_LOGIN["login_email_input"])))
        email.send_keys(ZOHO_EMAIL)
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, SELETORES_LOGIN["login_next_btn"]))).click()
        return True
    except Exception:
        return False

def inserir_senha(driver):
    try:
        wait = WebDriverWait(driver, 10)
        pwd = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, SELETORES_LOGIN["login_password_input"])))
        pwd.send_keys(ZOHO_SENHA)
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, SELETORES_LOGIN["login_next_btn"]))).click()
    except Exception:
        pass

def configurar_otp(driver):
    try:
        wait = WebDriverWait(driver, 5)
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, SELETORES_LOGIN["login_problem_btn"]))).click()
        wait.until(EC.element_to_be_clickable((By.XPATH, SELETORES_LOGIN["login_otp_method_btn"]))).click()
    except Exception:
        pass

def aguardar_login_manual(driver):
    print(f"\n>>> AGUARDANDO LOGIN MANUAL ({TIMEOUT_LOGIN_MANUAL_SEGUNDOS}s)... Insira o OTP no navegador.")
    start = time.time()
    while time.time() - start < TIMEOUT_LOGIN_MANUAL_SEGUNDOS:
        if "desk.zoho.com/agent/" in driver.current_url:
            try:
                WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, SELETORES_APLICACAO["icone_pesquisa"])))
                return True
            except: pass
        time.sleep(2)
    return False

def verificar_login_bem_sucedido(driver):
    try:
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, SELETORES_APLICACAO["icone_pesquisa"])))
        return True
    except: return False
