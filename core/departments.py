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

# Tenta importar seletores do config, senão usa fallback local
try:
    from config.selectors import SELETORES_MESSAGING as SELETORES
except ImportError:
    SELETORES = {
        "dropdown_departamento": 'span[data-id="qdeptcontainer_value"]',
        "item_departamento": "div.zd_v2-listitem-multiLineValue",
        "tab_whatsapp": "//div[contains(text(),'WhatsApp')]",
        "tab_email": "//div[contains(text(),'E-mail')]"
    }

def trocar_departamento_zoho(driver, nome_departamento, wait_timeout=30):
    """
    Seleciona o departamento no Zoho Desk.
    """
    wait = WebDriverWait(driver, wait_timeout)
    logging.info(f"Selecionando departamento: {nome_departamento}")
        
    try:
        # 1. Fechar alertas se houver
        try:
            driver.switch_to.alert.accept()
        except:
            pass
        
        time.sleep(1) 
        
        # 2. Clicar na tab E-mail (necessário para habilitar troca)
        try:
            tab_email = wait.until(EC.element_to_be_clickable((By.XPATH, SELETORES.get("tab_email", "//div[contains(text(),'E-mail')]"))))
            driver.execute_script("arguments[0].click();", tab_email)
            time.sleep(1)
        except TimeoutException:
            pass # Pode já estar na tab ou não ser necessário
            
        # 3. Verificar departamento atual
        try:
            dropdown_selector = SELETORES.get("dropdown_departamento", 'span[data-id="qdeptcontainer_value"]')
            dropdown = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, dropdown_selector)))
            dept_atual = dropdown.get_attribute("data-title") or dropdown.text.strip()
            
            if dept_atual == nome_departamento:
                logging.info(f"Departamento '{nome_departamento}' já selecionado.")
                voltar_para_whatsapp(driver)
                return True
        except Exception:
            logging.warning("Não foi possível ler o departamento atual.")

        # 4. Abrir Dropdown
        dropdown_aberto = False
        for _ in range(3):
            try:
                driver.execute_script("arguments[0].click();", dropdown)
                dropdown_aberto = True
                break
            except:
                time.sleep(1)
        
        if not dropdown_aberto:
            logging.error("Falha ao abrir dropdown de departamentos.")
            return False
                
        # 5. Selecionar Opção
        try:
            item_selector = SELETORES.get("item_departamento", "div.zd_v2-listitem-multiLineValue")
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, item_selector)))
            time.sleep(1)
            
            itens = driver.find_elements(By.CSS_SELECTOR, item_selector)
            for item in itens:
                if item.text and item.text.strip() == nome_departamento:
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", item)
                    item.click()
                    logging.info(f"Departamento '{nome_departamento}' clicado.")
                    time.sleep(2)
                    voltar_para_whatsapp(driver)
                    return True
                    
            logging.error(f"Departamento '{nome_departamento}' não encontrado na lista.")
            return False
            
        except Exception as e:
            logging.error(f"Erro ao selecionar item da lista: {e}")
            return False

    except Exception as e:
        logging.error(f"Erro crítico ao trocar departamento: {e}")
        return False

def voltar_para_whatsapp(driver):
    """Clica na aba WhatsApp."""
    try:
        wait = WebDriverWait(driver, 10)
        tab_wpp_selector = SELETORES.get("tab_whatsapp", "//div[contains(text(),'WhatsApp')]")
        tab = wait.until(EC.element_to_be_clickable((By.XPATH, tab_wpp_selector)))
        driver.execute_script("arguments[0].click();", tab)
        time.sleep(1)
    except:
        pass