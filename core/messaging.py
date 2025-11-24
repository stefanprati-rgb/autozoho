# -*- coding: utf-8 -*-
"""
Módulo de messaging do sistema de automação Zoho Desk.
Versão Otimizada com Estrutura HTML Confirmada (listTitle/listdesc).
"""

import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException

SELETORES_MESSAGING = {
    "botao_whatsapp": 'span[data-title="Enviar mensagens via WhatsApp (canal de IM)"]',
    "modal_dialog_xpath": "//div[contains(@class,'zd_v2') and .//button[contains(.,'Enviar')]]",
    "botao_concordo_marketing": 'button[data-id="alertConfirmButton"]',
    "dropdown_departamento": 'span[data-id="qdeptcontainer_value"]',
    "tab_whatsapp": "//div[@class='zd_v2-tab-tabText zd_v24af66c9aeb zd_v2050393fdda zd_v2eb439ba1e6 zd_v2577c9fa95f' and text()='WhatsApp']",
    "tab_email": "//div[@class='zd_v2-tab-tabText zd_v24af66c9aeb zd_v2050393fdda zd_v2eb439ba1e6 zd_v2577c9fa95f' and text()='E-mail']",
}

def avisar_modal_abriu():
    logging.info(">>> MODAL DO WHATSAPP ABERTO.")

def modal_esta_aberto(driver, timeout=3):
    try:
        modal = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((
                By.XPATH,
                "//div[contains(@class,'zd_v2') and .//button[contains(.,'Enviar')]]"
            ))
        )
        return modal.is_displayed()
    except Exception:
        try:
            return driver.find_element(By.CSS_SELECTOR, "div.zd_v2-lookup-box").is_displayed()
        except: return False

def fechar_ui_flutuante(driver):
    try:
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        time.sleep(0.3)
    except: pass

def clicar_seguro(driver, wait, by, selector, dry_run=False, tentativas=3, timeout_total=10, timeout_por_tentativa=None, scroll=True):
    for i in range(1, max(1, tentativas) + 1):
        try:
            tmo = timeout_por_tentativa if timeout_por_tentativa else max(2, int((timeout_total or 10) / tentativas))
            wait_local = WebDriverWait(driver, tmo)
            el = wait_local.until(EC.presence_of_element_located((by, selector)))
            if scroll:
                try: driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'nearest'});", el)
                except: pass
            el = wait_local.until(EC.element_to_be_clickable((by, selector)))
            
            if dry_run:
                logging.info(f"[DRY-RUN] Clique em {selector}")
                return True
            
            el.click()
            return True
        except Exception:
            if i == tentativas:
                try:
                    el = driver.find_element(by, selector)
                    driver.execute_script("arguments[0].click();", el)
                    return True
                except: pass
            time.sleep(0.5)
    return False

def take_screenshot(driver, base_name: str, folder: str = "screenshots") -> str:
    try:
        import os
        from datetime import datetime
        import re
        os.makedirs(folder, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe = re.sub(r"[^0-9A-Za-z_-]+", "_", base_name)[:80] or "shot"
        path = os.path.join(folder, f"{safe}_{ts}.png")
        driver.save_screenshot(path)
        return os.path.abspath(path)
    except: return ""

def fechar_alerta_sem_telefone(driver):
    try:
        alerta = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(., 'nenhum número') or contains(., 'no phone number')]"))
        )
        btn = alerta.find_element(By.XPATH, ".//button[.//span[normalize-space()='Ok'] or normalize-space()='Ok']")
        driver.execute_script("arguments[0].click();", btn)
        return True
    except: return False

def recarregar_pagina_cliente(driver, wait_clickable_timeout=20):
    try: driver.execute_script("window.stop();")
    except: pass
    driver.refresh()
    try:
        WebDriverWait(driver, wait_clickable_timeout).until(lambda d: d.execute_script("return document.readyState") == "complete")
        WebDriverWait(driver, wait_clickable_timeout).until(EC.element_to_be_clickable((By.CSS_SELECTOR, SELETORES_MESSAGING["botao_whatsapp"])))
        return True
    except: return False

def abrir_modal_whatsapp(driver, nome_cliente, dry_run=False):
    logging.info(f"[{nome_cliente}] Abrindo modal WhatsApp...")
    fechar_ui_flutuante(driver)
    
    if not clicar_seguro(driver, WebDriverWait(driver, 12), By.CSS_SELECTOR, SELETORES_MESSAGING["botao_whatsapp"], timeout_total=10, timeout_por_tentativa=5):
        logging.warning(f"[{nome_cliente}] Falha ao clicar no ícone WhatsApp")
        return False
    
    if fechar_alerta_sem_telefone(driver): return False
    
    for _ in range(14):
        if modal_esta_aberto(driver, timeout=3):
            logging.info(f"[{nome_cliente}] ✅ Modal aberto")
            avisar_modal_abriu()
            time.sleep(2.5)
            return True
        time.sleep(0.6)
    
    logging.error(f"[{nome_cliente}] ❌ Modal não abriu")
    return False

def tratar_alerta_marketing(driver, nome_cliente, dry_run=False):
    try:
        WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.CSS_SELECTOR, SELETORES_MESSAGING["botao_concordo_marketing"])))
        logging.warning(f"[{nome_cliente}] ⚠️ Aviso de marketing detectado")
        if clicar_seguro(driver, WebDriverWait(driver, 5), By.CSS_SELECTOR, SELETORES_MESSAGING["botao_concordo_marketing"], dry_run=dry_run):
            time.sleep(0.5)
            return True
    except: pass
    return True

def selecionar_canal_e_modelo(driver, canal_substr: str, nome_template: str, ancoras: list, timeout=15) -> bool:
    """
    Seleciona Canal e Template usando busca inteligente e classes confirmadas pelo HTML.
    Classes: zd_v2-imcommondropdown-listTitle e zd_v2-imcommondropdown-listdesc
    """
    wait = WebDriverWait(driver, timeout)
    short = WebDriverWait(driver, 5)

    # --- 1. GARANTIR CANAL ---
    try:
        fechar_ui_flutuante(driver)
        lbl_canal = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//label[contains(.,'Canal do WhatsApp') or contains(.,'WhatsApp Channel')]")))
        canal_input = lbl_canal.find_element(By.XPATH, ".//following::input[contains(@class,'secondarydropdown-textBox')][1]")
        
        if canal_substr.lower() not in (canal_input.get_attribute("value") or "").lower():
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", canal_input)
            driver.execute_script("arguments[0].click();", canal_input)
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//li[@role='option']")))
            
            opcoes = [li for li in driver.find_elements(By.XPATH, "//li[@role='option']") if li.is_displayed()]
            for op in opcoes:
                if canal_substr in op.text:
                    op.click()
                    logging.info(f"Canal '{canal_substr}' selecionado.")
                    time.sleep(1)
                    break
    except Exception as e:
        logging.warning(f"Aviso canal: {e}")

    # --- 2. SELECIONAR TEMPLATE (COM BUSCA E ESTRUTURA HTML CORRETA) ---
    logging.info(f"Procurando template: '{nome_template}'")
    try:
        # Localiza Input
        label = wait.until(EC.presence_of_element_located((By.XPATH, "//label[normalize-space()='Modelo de mensagem' or contains(.,'Template')]")))
        modelo_input = label.find_element(By.XPATH, ".//following::input[contains(@class,'secondarydropdown-textBox')][1]")
        
        # Verifica se já selecionado
        if nome_template.lower() in (modelo_input.get_attribute("value") or "").lower():
            return True

        # Abre Dropdown
        fechar_ui_flutuante(driver)
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", modelo_input)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", modelo_input)
        time.sleep(2) # Carregamento
        
        # --- Tenta digitar na busca do menu (se houver) ---
        search_typed = False
        try:
            search_box = driver.find_element(By.CSS_SELECTOR, "input[placeholder='Search']")
            if search_box.is_displayed():
                search_box.click()
                search_box.clear()
                search_box.send_keys(nome_template)
                time.sleep(1.5)
                search_typed = True
        except: pass

        # --- BUSCA PELAS CLASSES DO HTML ---
        wait.until(EC.presence_of_element_located((By.XPATH, "//li[@role='option']")))
        
        candidato = None
        nome_limpo = nome_template.strip()
        
        # Pega todos os 'li' visíveis (opções)
        opcoes = [op for op in driver.find_elements(By.XPATH, "//li[@role='option']") if op.is_displayed()]
        
        # 1. Busca pelo Título (listTitle)
        for op in opcoes:
            try:
                titulo_el = op.find_element(By.XPATH, ".//div[contains(@class, 'listTitle')]")
                if nome_limpo in titulo_el.text:
                    candidato = op
                    logging.info(f"Template encontrado (Título): '{titulo_el.text}'")
                    break
            except: continue
        
        # 2. Busca pela Descrição/Âncora (listdesc)
        if not candidato and ancoras and not search_typed:
            for ancora in ancoras:
                ancora_limpa = ancora.replace("'", "\\'")[:50]
                for op in opcoes:
                    try:
                        desc_el = op.find_element(By.XPATH, ".//div[contains(@class, 'listdesc')]")
                        if ancora_limpa in desc_el.text:
                            candidato = op
                            logging.info(f"Template encontrado (Âncora): '{ancora_limpa}...'")
                            break
                    except: continue
                if candidato: break

        # Clica
        if candidato:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", candidato)
            try: candidato.click()
            except: driver.execute_script("arguments[0].click();", candidato)
            time.sleep(1)
            return True
        else:
            # Debug: lista o que achou
            titulos_visiveis = []
            for op in opcoes[:5]:
                try: titulos_visiveis.append(op.find_element(By.XPATH, ".//div[contains(@class, 'listTitle')]").text)
                except: pass
            logging.error(f"Template '{nome_template}' não encontrado. Visíveis: {titulos_visiveis}")
            return False

    except Exception as e:
        logging.error(f"Erro template: {e}")
        take_screenshot(driver, f"erro_template_{nome_template}")
        return False

def enviar_mensagem_whatsapp(driver, nome_cliente, dry_run=False, modo_semi_assistido=True, timeout_envio_manual=600, template_nome=None, ancoras_template=None):
    wait = WebDriverWait(driver, 15)
    xpath_btn = "//div[contains(@class,'zd_v2')]//button[contains(.,'Enviar')]"
    
    logging.info(f"[{nome_cliente}] 4️⃣ Enviando mensagem...")
    try:
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, xpath_btn)))
    except:
        logging.warning(f"[{nome_cliente}] Botão Enviar não habilitou.")
    
    if modo_semi_assistido:
        if dry_run:
            logging.info(f"[{nome_cliente}] [DRY-RUN] Aguardando (simulado)...")
            return True
        logging.info(f"[{nome_cliente}] ⏸️ AGUARDANDO USUÁRIO CLICAR EM 'ENVIAR'...")
        try:
            WebDriverWait(driver, timeout_envio_manual).until(EC.invisibility_of_element_located((By.XPATH, SELETORES_MESSAGING["modal_dialog_xpath"])))
            logging.info(f"[{nome_cliente}] ✅ Modal fechado (envio manual).")
            return True
        except:
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            return False
    else:
        if dry_run:
            logging.info(f"[{nome_cliente}] [DRY-RUN] Clicando (simulado)...")
            return True
        logging.info(f"[{nome_cliente}] 🚀 Clicando em 'Enviar' (auto)...")
        if clicar_seguro(driver, wait, By.XPATH, xpath_btn, timeout_por_tentativa=5):
            try:
                WebDriverWait(driver, 12).until(EC.any_of(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@class,'toast')][contains(.,'envi') or contains(.,'sucesso')]")),
                    EC.presence_of_element_located((By.XPATH, "//button[contains(.,'Enviar') and @disabled]"))
                ))
                logging.info(f"[{nome_cliente}] ✅ Sucesso detectado.")
                try:
                    btn_fechar = driver.find_element(By.XPATH, "//div[contains(@class,'zd_v2') and @role='dialog']//button[contains(@aria-label,'Fechar') or contains(.,'×')]")
                    driver.execute_script("arguments[0].click();", btn_fechar)
                except: fechar_ui_flutuante(driver)
                time.sleep(1)
                return True
            except:
                logging.error("Erro pós-envio.")
        else:
            logging.error("Falha clique Enviar.")
            return False
    return False

def processar_envio_completo_whatsapp(driver, nome_cliente, departamento, template_nome, ancoras_template, dry_run=False, modo_semi_assistido=True):
    logging.info(f"INICIANDO ENVIO WHATSAPP: {nome_cliente}")
    if not abrir_modal_whatsapp(driver, nome_cliente, dry_run): return False
    if not selecionar_canal_e_modelo(driver, departamento, template_nome, ancoras_template):
        take_screenshot(driver, f"falha_template_{nome_cliente}")
        return False
    tratar_alerta_marketing(driver, nome_cliente, dry_run)
    sucesso = enviar_mensagem_whatsapp(driver, nome_cliente, dry_run, modo_semi_assistido, template_nome=template_nome, ancoras_template=ancoras_template)
    if sucesso: logging.info(f"[{nome_cliente}] ✅ ENVIO CONCLUÍDO!")
    return sucesso