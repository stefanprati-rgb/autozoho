# -*- coding: utf-8 -*-
"""
Módulo de messaging do sistema de automação Zoho Desk.
Contém todas as funções relacionadas ao envio de mensagens via WhatsApp.
"""

import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException, UnexpectedAlertPresentException

SELETORES_MESSAGING = {
    "botao_whatsapp": 'span[data-title="Enviar mensagens via WhatsApp (canal de IM)"]',
    "modal_mensagem": 'div.zd_v2-lookup-box',
    "modal_dialog_xpath": "//div[contains(@class,'zd_v2') and .//button[contains(.,'Enviar')]]",
    "botao_concordo_marketing": 'button[data-id="alertConfirmButton"]',
    "dropdown_departamento": 'span[data-id="qdeptcontainer_value"]',
    "item_departamento": "div.zd_v2-listitem-multiLineValue",
    "tab_whatsapp": "//div[@class='zd_v2-tab-tabText zd_v24af66c9aeb zd_v2050393fdda zd_v2eb439ba1e6 zd_v2577c9fa95f' and text()='WhatsApp']",
    "tab_email": "//div[@class='zd_v2-tab-tabText zd_v24af66c9aeb zd_v2050393fdda zd_v2eb439ba1e6 zd_v2577c9fa95f' and text()='E-mail']",
}

def avisar_modal_abriu():
    logging.info(">>> MODAL DO WHATSAPP ABERTO.")

def modal_esta_aberto(driver, timeout=3):
    try:
        modal = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((By.XPATH, "//div[contains(@class,'zd_v2') and .//button[contains(.,'Enviar')]]"))
        )
        return modal.is_displayed()
    except TimeoutException:
        try:
            el = driver.find_element(By.CSS_SELECTOR, "div.zd_v2-lookup-box")
            return el.is_displayed()
        except: return False

def fechar_ui_flutuante(driver):
    try:
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        time.sleep(0.2)
    except: pass

def clicar_seguro(driver, wait, by, selector, dry_run=False, timeout_por_tentativa=None, scroll=True, **kwargs):
    max_tentativas = 3
    for i in range(1, max_tentativas + 1):
        try:
            tmo = timeout_por_tentativa if timeout_por_tentativa else 3
            _wait = WebDriverWait(driver, tmo)
            el = _wait.until(EC.presence_of_element_located((by, selector)))
            if scroll:
                try: driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'nearest'});", el)
                except: pass
            el = _wait.until(EC.element_to_be_clickable((by, selector)))
            if dry_run: return True
            el.click()
            return True
        except Exception as e:
            if i == max_tentativas:
                try:
                    el = driver.find_element(by, selector)
                    driver.execute_script("arguments[0].click();", el)
                    return True
                except: pass
            time.sleep(0.5)
    return False

def take_screenshot(driver, base_name, folder="screenshots"):
    try:
        import os
        from datetime import datetime
        os.makedirs(folder, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        out_path = os.path.join(folder, f"{base_name}_{ts}.png")
        driver.save_screenshot(out_path)
        logging.error(f"Screenshot salvo: {out_path}")
        return out_path
    except: return ""

def fechar_alerta_sem_telefone(driver):
    try:
        alerta = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.XPATH, "//div[contains(., 'nenhum número') or contains(., 'no phone number')]")))
        botao_ok = alerta.find_element(By.XPATH, ".//button[.//span[normalize-space()='Ok'] or normalize-space()='Ok']")
        driver.execute_script("arguments[0].click();", botao_ok)
        logging.warning("Fechado alerta: cliente sem telefone.")
        return True
    except: return False

def recarregar_pagina_cliente(driver, wait_clickable_timeout=20):
    driver.refresh()
    try:
        WebDriverWait(driver, wait_clickable_timeout).until(lambda d: d.execute_script("return document.readyState") == "complete")
        WebDriverWait(driver, wait_clickable_timeout).until(EC.element_to_be_clickable((By.CSS_SELECTOR, SELETORES_MESSAGING["botao_whatsapp"])))
        return True
    except: return False

def abrir_modal_whatsapp(driver, nome_cliente, dry_run=False, max_tentativas=2):
    logging.info(f"[{nome_cliente}] Abrindo modal WhatsApp...")
    fechar_ui_flutuante(driver)
    
    if not clicar_seguro(driver, WebDriverWait(driver, 12), By.CSS_SELECTOR, SELETORES_MESSAGING["botao_whatsapp"], timeout_por_tentativa=5):
        logging.warning(f"[{nome_cliente}] Falha ao clicar no ícone WhatsApp")
        return False
    
    if fechar_alerta_sem_telefone(driver): return False
    
    for _ in range(14):
        if modal_esta_aberto(driver):
            logging.info(f"[{nome_cliente}] ✅ Modal aberto")
            time.sleep(2)
            return True
        time.sleep(0.6)
    
    logging.error(f"[{nome_cliente}] ❌ Modal não abriu")
    return False

def selecionar_canal_e_modelo(driver, canal_substr, nome_template, ancoras, timeout=15):
    wait = WebDriverWait(driver, timeout)
    short = WebDriverWait(driver, 5)
    fechar_ui_flutuante(driver)

    # 1. SELEÇÃO DE CANAL
    try:
        lbl_canal = wait.until(EC.presence_of_element_located((By.XPATH, "//label[normalize-space()='Canal do WhatsApp']")))
        canal_input = lbl_canal.find_element(By.XPATH, ".//following::input[1] | .//following::div[contains(@class,'select')][1]")
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", canal_input)
        try: canal_input.click()
        except: driver.execute_script("arguments[0].click();", canal_input)
        
        wait.until(EC.presence_of_element_located((By.XPATH, "//li[@role='option']")))
        opcoes = driver.find_elements(By.XPATH, "//li[@role='option']")
        for op in opcoes:
            if op.is_displayed() and canal_substr in op.text:
                op.click()
                logging.info(f"Canal '{canal_substr}' selecionado.")
                time.sleep(0.5)
                break
    except Exception as e:
        logging.warning(f"Aviso na seleção de canal (pode já estar certo): {e}")

    # 2. SELEÇÃO DE TEMPLATE (AQUI ESTÁ O PROBLEMA GERALMENTE)
    try:
        # Procura o input ou dropdown do Modelo
        label_modelo = wait.until(EC.presence_of_element_located((By.XPATH, "//label[normalize-space()='Modelo de mensagem']")))
        # Tenta encontrar o elemento clicável próximo (input ou div de dropdown)
        modelo_input = label_modelo.find_element(By.XPATH, ".//following::*[contains(@class,'secondarydropdown') or contains(@class,'select') or contains(@class,'input')][1]")
        
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", modelo_input)
        try: modelo_input.click()
        except: driver.execute_script("arguments[0].click();", modelo_input)
        
        # Espera opções aparecerem
        wait.until(EC.presence_of_element_located((By.XPATH, "//li[@role='option']")))
        time.sleep(1) # Pausa crucial para renderização
        
    except Exception as e:
        logging.error(f"Falha ao abrir dropdown de templates: {e}")
        take_screenshot(driver, "erro_abrir_dropdown_template")
        return False

    # 3. BUSCAR O TEMPLATE NA LISTA
    candidato = None
    try:
        opcoes = driver.find_elements(By.XPATH, "//li[@role='option']")
        opcoes_visiveis = [op for op in opcoes if op.is_displayed()]
        
        # DIAGNÓSTICO: Mostra o que o robô está vendo
        textos_opcoes = [op.text.split('\n')[0].strip() for op in opcoes_visiveis] # Pega só a primeira linha (título)
        logging.info(f"Opções disponíveis no dropdown: {textos_opcoes}")
        
        nome_norm = nome_template.strip().lower()
        
        # Tentativa 1: Nome Exato
        for op in opcoes_visiveis:
            txt = op.text.split('\n')[0].strip() # Título do template
            if txt.lower() == nome_norm:
                candidato = op
                logging.info(f"Template encontrado (match exato): '{txt}'")
                break
        
        # Tentativa 2: Contém o nome
        if not candidato:
            for op in opcoes_visiveis:
                txt = op.text.split('\n')[0].strip()
                if nome_norm in txt.lower():
                    candidato = op
                    logging.info(f"Template encontrado (match parcial): '{txt}'")
                    break
        
        # Tentativa 3: Âncoras (texto do corpo)
        if not candidato and ancoras:
            ancora = ancoras[0].replace("'", "").strip()[:50]
            for op in opcoes_visiveis:
                if ancora.lower() in op.text.lower():
                    candidato = op
                    logging.info("Template encontrado por âncora.")
                    break

    except Exception as e:
        logging.error(f"Erro ao varrer opções: {e}")

    if candidato:
        try:
            candidato.click()
            logging.info(f"Template '{nome_template}' clicado com sucesso.")
            time.sleep(1)
            return True
        except:
            driver.execute_script("arguments[0].click();", candidato)
            logging.info("Template clicado via JS.")
            return True
    
    logging.error(f"❌ Template '{nome_template}' NÃO encontrado na lista. Verifique o nome exato no constants.py.")
    return False

def tratar_alerta_marketing(driver, nome_cliente, dry_run=False):
    try:
        btn = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.CSS_SELECTOR, SELETORES_MESSAGING["botao_concordo_marketing"])))
        logging.warning(f"[{nome_cliente}] Aviso de marketing.")
        if not dry_run: btn.click()
        return True
    except: return True

def trocar_departamento_zoho(driver, nome_departamento, wait_timeout=15):
    # (Mantido simplificado pois o foco é o messaging)
    return True 

def enviar_mensagem_whatsapp(driver, nome_cliente, dry_run=False, modo_semi_assistido=True, timeout_envio_manual=600, **kwargs):
    wait = WebDriverWait(driver, 15)
    btn_enviar = "//div[contains(@class,'zd_v2')]//button[contains(.,'Enviar')]"
    
    try:
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, btn_enviar)))
    except:
        logging.error("Botão Enviar não ficou pronto.")
        return False

    if dry_run:
        logging.info(f"[{nome_cliente}] [DRY-RUN] Mensagem pronta para envio.")
        return True

    # Modo Automático (Enviar direto)
    logging.info(f"[{nome_cliente}] Clicando em Enviar...")
    if clicar_seguro(driver, wait, By.XPATH, btn_enviar):
        time.sleep(2)
        # Fecha modal se não fechar sozinho
        fechar_ui_flutuante(driver)
        logging.info(f"[{nome_cliente}] ✅ Mensagem enviada.")
        return True
    
    return False