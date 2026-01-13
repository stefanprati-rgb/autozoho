# -*- coding: utf-8 -*-
"""
Módulo de gerenciamento de departamentos (core/departments.py).
"""
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

def trocar_departamento_zoho(driver, nome_departamento, wait_timeout=30):
    """
    Seleciona o departamento no Zoho Desk.
    IMPORTANTE: Esse seletor só funciona na aba E-Mail (/e-mail/list/...).
    O robô clica em E-Mail, troca o departamento e depois volta para WhatsApp.
    """
    wait = WebDriverWait(driver, wait_timeout)
    logging.info(f"Selecionando departamento: {nome_departamento}")
        
    def fechar_alertas():
        """Helper para limpar alertas intrusivos do Zoho."""
        try:
            for _ in range(5):
                try:
                    alert = driver.switch_to.alert
                    txt = alert.text
                    logging.warning(f"⚠️ Alerta Zoho interceptado: {txt}")
                    alert.accept()
                    time.sleep(1)
                except:
                    break
        except: pass

    try:
        # 1. Aguarda carregamento real da página
        if "desk.zoho.com/agent/" not in driver.current_url:
             logging.info("Aguardando carregamento da interface do agente...")
             try:
                 WebDriverWait(driver, 15).until(lambda d: "desk.zoho.com/agent/" in d.current_url)
                 time.sleep(3) # Tempo extra para scripts do Zoho
             except: pass

        # 2. Limpeza inicial
        fechar_alertas()
        
        # 3. Ir para a aba E-Mail
        logging.info("Navegando para aba E-Mail...")
        if not clicar_aba_email(driver):
            logging.error("Não foi possível acessar a aba E-Mail.")
            return False
        
        # Aguarda estabilização da aba
        time.sleep(5) 
        fechar_alertas()

        # 3. Localizar dropdown (Combobox) do departamento
        logging.info("Procurando seletor de departamento...")
        selectors_dropdown = [
            'input[role="combobox"][aria-label="Pesquisar departamento"]',
            'span[data-id="qdeptcontainer_value"]', # Seletor clássico
            '[aria-label="Pesquisar departamento"]',
            '.zd_v2-dept-list', 
            '#qdeptcontainer_value'
        ]
        
        dropdown = None
        
        # Tenta localizar usando lista
        for tenta in range(3):
            fechar_alertas()
            for sel in selectors_dropdown:
                try:
                    # Usa timeout curto (5s) para checagem rápida de cada opção
                    dropdown = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
                    if dropdown:
                        logging.info(f"Dropdown encontrado com seletor: {sel}")
                        break
                except: continue
            
            if dropdown: break
            
            logging.warning(f"Tentativa {tenta+1} de localizar dropdown falhou. Retentando...")
            time.sleep(2)

        if not dropdown:
            logging.error("Dropdown de departamento não encontrado na aba E-Mail após retentativas.")
            return False
        
        # 4. Verificar departamento atual
        try:
            fechar_alertas()
            dept_atual = dropdown.get_attribute("value") or ""
            if nome_departamento.lower() in dept_atual.lower():
                logging.info(f"Departamento '{nome_departamento}' já selecionado.")
                clicar_aba_whatsapp(driver)
                return True
        except: pass

        # 5. Abrir Dropdown
        logging.debug(f"Abrindo dropdown de departamentos...")
        dropdown_aberto = False
        
        # Tenta localizar o dropdown usando múltiplos seletores
        selectors_dropdown = [
            'input[role="combobox"][aria-label="Pesquisar departamento"]',
            'span[data-id="qdeptcontainer_value"]',
            '[aria-label="Pesquisar departamento"]',
            '.zd_v2-dept-list'
        ]
        
        dropdown = None
        for sel in selectors_dropdown:
            try:
                dropdown = driver.find_element(By.CSS_SELECTOR, sel)
                if dropdown.is_displayed():
                    break
            except: continue
            
        if not dropdown:
            logging.error("Dropdown de departamento não encontrado.")
            return False

        # Tenta abrir
        for _ in range(3):
            try:
                driver.execute_script("arguments[0].click();", dropdown)
                time.sleep(1.5)
                # Verifica se abriu procurando options ou itens de lista
                if driver.find_elements(By.CSS_SELECTOR, "li[role='option'], div.zd_v2-listitem"):
                    dropdown_aberto = True
                    break
            except:
                time.sleep(1)
        
        if not dropdown_aberto:
            logging.warning("Dropdown parece não ter aberto options. Tentando XPath direto...")

        # 6. Selecionar Opção
        xpath_opcao = f"//option[contains(normalize-space(.), '{nome_departamento}')]"
        
        # Mapeamento de nodes (para <option>)
        map_nodes = {
            "Alagoas Energia": "7936",
            "EGS": "7940",
            "Era Verde Energia": "7946",
            "Hube": "7950",
            "Lua Nova Energia": "7954"
        }
        node = map_nodes.get(nome_departamento)
        
        opcao = None
        # Tenta localizar a opção (Priorizando DIV rápido)
        for _ in range(3):
            try:
                fechar_alertas()
                
                # 1. TENTATIVA RÁPIDA: DIV Estrutural (Como visto nos logs)
                # <div class="zd_v2-listitem-multiLineValue ...">EGS</div>
                try:
                    xpath_div = f"//div[contains(@class, 'zd_v2-listitem') and normalize-space(.)='{nome_departamento}']"
                    # Busca rápida (1s)
                    div = WebDriverWait(driver, 1).until(EC.element_to_be_clickable((By.XPATH, xpath_div)))
                    if div:
                        opcao = div
                        logging.info(f"Opção encontrada (DIV Rapid): {nome_departamento}")
                        break
                except: pass

                # 2. Tenta <option> padrão
                try:
                    opcao = WebDriverWait(driver, 1).until(EC.element_to_be_clickable((By.XPATH, xpath_opcao)))
                    if opcao: break
                except: pass
                
                # 3. Tenta pelo Node ID
                if node:
                    try:
                        xpath_node = f"//option[@node='{node}']"
                        opcao = driver.find_element(By.XPATH, xpath_node)
                        if opcao: break
                    except: pass

                time.sleep(0.5)
            except:
                fechar_alertas()
                time.sleep(1)

        if not opcao:
            logging.error(f"Falha ao localizar o departamento '{nome_departamento}' na lista.")
            return False

        # 7. Clicar na opção
        try:
            fechar_alertas()
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", opcao)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", opcao)
        except:
            opcao.click()

        logging.info(f"Departamento '{nome_departamento}' selecionado.")
        time.sleep(3) # Zoho é lento para trocar o contexto
        fechar_alertas()
        
        if not clicar_aba_whatsapp(driver):
            logging.warning("Falha ao retornar para WhatsApp, mas departamento trocado.")
        
        return True

    except Exception as e:
        logging.error(f"Erro crítico ao trocar departamento: {e}")
        return False

def clicar_aba_email(driver, tentativas=3):
    """Clica na aba E-Mail."""
    for tent in range(tentativas):
        time.sleep(1)
        seletores = [
            "a[data-id='qtab_Cases_Tab']", # ID específico do Zoho
            "a[data-title='E-mail']",       # Atributo de título explícito
            "a[data-title='E-Mail']",       # Variação com hífen
            "//a[contains(@data-id, 'Cases_Tab')]",  # Contém Cases_Tab
            "//div[contains(@class, 'zd_v2-tab-tabText') and text()='E-mail']",
            "//div[contains(@class, 'zd_v2-tab-tabText') and text()='E-Mail']",
            "//a[normalize-space(.)='E-Mail']", 
            "//a[normalize-space(.)='E-mail']",
            "//a[contains(@href, '/e-mail/list')]",
            "//a[contains(@href, '/e-mail')]",
            # Seletores de ícone de e-mail (usa mais em mobile/telas estreitas)
            "a[data-id='qtab_Cases_Tab'] svg",
            "//a[contains(@class, 'zd_v2-tab')]//span[contains(text(), 'E-mail')]",
        ]
        
        logging.debug(f"Tentativa {tent+1}/{tentativas} de clicar na aba E-Mail...")
        
        for sel in seletores:
            try:
                if sel.startswith("//"):
                    el = driver.find_element(By.XPATH, sel)
                else:
                    el = driver.find_element(By.CSS_SELECTOR, sel)
                
                # Mesmo se não visível, tenta JS click
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
                    time.sleep(0.3)
                except: pass
                
                driver.execute_script("arguments[0].click();", el)
                logging.info(f"📧 Clicou na aba E-Mail (Seletor: {sel})")
                
                # Confirmação via URL
                try: 
                    WebDriverWait(driver, 5).until(lambda d: "e-mail" in d.current_url.lower() or "cases" in d.current_url.lower())
                    return True
                except: 
                    # Mesmo sem confirmação de URL, continua
                    time.sleep(2)
                    return True
                    
            except Exception as e:
                logging.debug(f"Seletor {sel} falhou: {e}")
                continue
        
        logging.warning(f"Tentativa {tent+1} falhou. Recarregando página...")
        try:
            driver.refresh()
            time.sleep(3)
        except: pass
        
    return False

def clicar_aba_whatsapp(driver):
    """Clica na aba WhatsApp."""
    time.sleep(1)
    seletores = [
        "//a[normalize-space(.)='WhatsApp']", # USER SUGGESTION
        "//a[contains(@href, '/whatsapp/page')]", # USER SUGGESTION
        "//div[text()='WhatsApp']",
        "//div[contains(@class, 'zd_v2-tab') and contains(., 'WhatsApp')]"
    ]
    for sel in seletores:
        try:
            if sel.startswith("//"):
                el = driver.find_element(By.XPATH, sel)
            else:
                el = driver.find_element(By.CSS_SELECTOR, sel)
            
            if el.is_displayed():
                driver.execute_script("arguments[0].click();", el)
                logging.info("📱 Clicou na aba WhatsApp")
                
                # Confirmação via URL
                try: WebDriverWait(driver, 5).until(lambda d: "whatsapp" in d.current_url.lower())
                except: pass
                
                return True
        except: continue
    return False

def garantir_aba_whatsapp(driver, max_tentativas=3):
    """Garante que estamos na aba WhatsApp."""
    return clicar_aba_whatsapp(driver)

def voltar_para_whatsapp(driver):
    """Alias para clicar_aba_whatsapp."""
    return clicar_aba_whatsapp(driver)