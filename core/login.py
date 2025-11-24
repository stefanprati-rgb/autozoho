# -*- coding: utf-8 -*-
"""
Módulo de login do sistema de automação Zoho Desk.
Gerencia a autenticação semi-automatizada.
"""

import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, InvalidSessionIdException, NoSuchElementException

# Configurações
ZOHO_EMAIL = "gestao.gdc@grupogera.com"
ZOHO_SENHA = "Ger@2357"
URL_ZOHO_DESK = "https://desk.zoho.com/agent/hubedesk/era-verde-energia/whatsapp/page#IM/-1/sessions/mine-all"
TIMEOUT_LOGIN_MANUAL_SEGUNDOS = 900  # 15 minutos

# Seletores de Login
SELETORES_LOGIN = {
    "login_email_input": 'input#login_id',
    "login_next_btn": 'button#nextbtn',
    "login_password_input": 'input#password',
    "login_problem_btn": 'div#problemsignin',
    "login_otp_method_btn": "//div[contains(text(), 'Insira a OTP com base em tempo')]",
    "icone_pesquisa": 'button[data-id="globalSearchIcon"]',
    
    # NOVO: Seletor para o botão "Agora não" (Trust Device)
    "btn_agora_nao": "button.trustdevice.notnowbtn" 
}

def clicar_seguro(driver, wait, by, selector):
    try:
        el = wait.until(EC.element_to_be_clickable((by, selector)))
        el.click()
        return True
    except:
        try:
            driver.execute_script("arguments[0].click();", driver.find_element(by, selector))
            return True
        except: return False

def fazer_login(driver):
    """
    Executa o login semi-automatizado com tratamento para o botão 'Agora não'.
    """
    driver.get(URL_ZOHO_DESK)
    wait = WebDriverWait(driver, 20)
    short_wait = WebDriverWait(driver, 5)
        
    try:
        # 1. Verifica se já está logado
        try:
            WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.CSS_SELECTOR, SELETORES_LOGIN["icone_pesquisa"])))
            logging.info("Login já estava ativo (sessão em cache).")
            return True
        except TimeoutException:
            logging.info("Iniciando processo de login...")

        # 2. Insere Credenciais
        try:
            # E-mail
            email_input = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, SELETORES_LOGIN["login_email_input"])))
            email_input.send_keys(ZOHO_EMAIL)
            clicar_seguro(driver, wait, By.CSS_SELECTOR, SELETORES_LOGIN["login_next_btn"])
            logging.info("E-mail inserido.")
            
            # Senha
            try:
                password_input = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, SELETORES_LOGIN["login_password_input"])))
                password_input.send_keys(ZOHO_SENHA)
                clicar_seguro(driver, wait, By.CSS_SELECTOR, SELETORES_LOGIN["login_next_btn"])
                logging.info("Senha inserida.")
            except TimeoutException:
                logging.info("Campo de senha não apareceu (possível fluxo alternativo).")
            
            # Seleção de OTP (se necessário)
            try:
                short_wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, SELETORES_LOGIN["login_problem_btn"]))).click()
                clicar_seguro(driver, wait, By.XPATH, SELETORES_LOGIN["login_otp_method_btn"])
                logging.info("Selecionado método OTP App.")
            except: pass

        except Exception as e:
            logging.warning(f"Erro parcial no preenchimento (pode já estar na tela de OTP): {e}")

        # 3. Espera Inteligente (OTP + Botão 'Agora não')
        print("\n" + "="*40)
        print(f"Aguardando login manual (OTP)... (Timeout: {TIMEOUT_LOGIN_MANUAL_SEGUNDOS//60} min)")
        print("Se aparecer o botão 'Agora não', o robô tentará clicar.")
        print("="*40 + "\n")
        
        inicio_espera = time.time()
        
        while True:
            # Verifica Timeout
            if time.time() - inicio_espera > TIMEOUT_LOGIN_MANUAL_SEGUNDOS:
                logging.error("Timeout aguardando login.")
                return False

            try:
                # --- NOVO: CLICA NO BOTÃO 'AGORA NÃO' SE APARECER ---
                try:
                    # Verifica se o botão existe e está visível
                    btn_trust = driver.find_element(By.CSS_SELECTOR, SELETORES_LOGIN["btn_agora_nao"])
                    if btn_trust.is_displayed():
                        logging.info("Botão 'Agora não' (Dispositivo Confiável) detectado. Clicando...")
                        btn_trust.click()
                        time.sleep(2) # Espera a página reagir
                except (NoSuchElementException, Exception):
                    pass # Botão não está na tela, continua esperando
                # ----------------------------------------------------

                # Verifica sucesso (URL do agente ou ícone de pesquisa)
                if "desk.zoho.com/agent/" in driver.current_url:
                    try:
                        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, SELETORES_LOGIN["icone_pesquisa"])))
                        logging.info("Login concluído com sucesso!")
                        return True
                    except: pass # URL certa, mas ainda carregando
                
                # Verifica se o navegador foi fechado
                _ = driver.title 
                
                time.sleep(1)

            except InvalidSessionIdException:
                logging.critical("Navegador fechado pelo usuário.")
                return False
            except Exception:
                time.sleep(1)

    except Exception as e:
        logging.error(f"Erro fatal no login: {e}")
        return False