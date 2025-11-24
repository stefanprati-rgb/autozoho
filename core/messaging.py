# -*- coding: utf-8 -*-
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

SELETORES_MESSAGING = {
    "botao_whatsapp": 'span[data-title="Enviar mensagens via WhatsApp (canal de IM)"]',
    "botao_concordo_marketing": 'button[data-id="alertConfirmButton"]',
}

def _clicar_robusto(driver, elemento):
    try:
        elemento.click()
        return True
    except:
        driver.execute_script("arguments[0].click();", elemento)
        return True

def fechar_ui_flutuante(driver):
    try:
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        time.sleep(0.5)
    except: pass

def abrir_modal_whatsapp(driver, nome_cliente, dry_run=False):
    logging.info(f"[{nome_cliente}] Abrindo WhatsApp...")
    fechar_ui_flutuante(driver)
    
    try:
        btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, SELETORES_MESSAGING["botao_whatsapp"])))
        _clicar_robusto(driver, btn)
    except:
        logging.warning(f"[{nome_cliente}] Botão WhatsApp falhou.")
        return False
    
    # Fecha alertas
    try:
        alerta = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.XPATH, "//div[contains(., 'nenhum número')]")))
        driver.execute_script("arguments[0].click();", alerta.find_element(By.TAG_NAME, "button"))
        return False
    except: pass
    
    # Espera modal
    try:
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//div[contains(@class,'zd_v2') and .//button[contains(.,'Enviar')]]"))
        )
        time.sleep(2) # Pausa para estabilizar
        return True
    except: return False

def selecionar_canal_e_modelo(driver, canal_substr, nome_template, ancoras, timeout=15):
    wait = WebDriverWait(driver, timeout)
    fechar_ui_flutuante(driver)

    # Seleção de Template
    logging.info(f"Procurando template: '{nome_template}'")
    try:
        label_modelo = wait.until(EC.presence_of_element_located((By.XPATH, "//label[normalize-space()='Modelo de mensagem']")))
        modelo_input = label_modelo.find_element(By.XPATH, ".//following::*[contains(@class,'secondarydropdown') or contains(@class,'select') or contains(@class,'input')][1]")
        
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", modelo_input)
        time.sleep(1)
        _clicar_robusto(driver, modelo_input)
        
        # Espera lista (Aumentado para 3s)
        wait.until(EC.presence_of_element_located((By.XPATH, "//li[@role='option']")))
        time.sleep(3) 
        
        opcoes = driver.find_elements(By.XPATH, "//li[@role='option']")
        candidato = None
        
        nome_norm = nome_template.strip().lower()
        
        for op in opcoes:
            if not op.is_displayed(): continue
            txt = op.text.split('\n')[0].strip().lower()
            
            if txt == nome_norm: # Exato
                candidato = op
                break
            if nome_norm in txt: # Parcial
                candidato = op
        
        if candidato:
            logging.info(f"Selecionando: '{candidato.text.splitlines()[0]}'")
            _clicar_robusto(driver, candidato)
            time.sleep(1.5)
            return True
        else:
            logging.error(f"Template '{nome_template}' não encontrado.")
            return False

    except Exception as e:
        logging.error(f"Erro seleção template: {e}")
        return False

def enviar_mensagem_whatsapp(driver, nome_cliente, dry_run=False, modo_semi_assistido=False, **kwargs):
    wait = WebDriverWait(driver, 15)
    btn_enviar = "//div[contains(@class,'zd_v2')]//button[contains(.,'Enviar')]"
    
    try:
        el = wait.until(EC.element_to_be_clickable((By.XPATH, btn_enviar)))
        if dry_run:
            logging.info(f"[{nome_cliente}] [DRY-RUN] Pronto para enviar.")
            return True
        
        logging.info(f"[{nome_cliente}] Enviando...")
        _clicar_robusto(driver, el)
        time.sleep(3)
        fechar_ui_flutuante(driver)
        return True
    except:
        return False