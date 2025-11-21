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

# Seletores CSS e XPaths para o sistema de mensagens
SELETORES_MESSAGING = {
    # Botão do WhatsApp
    "botao_whatsapp": 'span[data-title="Enviar mensagens via WhatsApp (canal de IM)"]',
    
    # Modal de mensagem
    "modal_mensagem": 'div.zd_v2-lookup-box',  # Modal antigo (fallback)
    "modal_dialog_xpath": "//div[contains(@class,'zd_v2') and .//button[contains(.,'Enviar')]]",
    
    # Dropdown de templates
    "dropdown_templates_xpath": "//div[@role='dialog']//label[contains(., 'Modelo') or contains(., 'Template')]/following::div[contains(@class,'textbox') or contains(@class,'input') or contains(@class,'dropdown')][1]",
    
    # Botão de concordo para alerta de marketing
    "botao_concordo_marketing": 'button[data-id="alertConfirmButton"]',  # Botão "Concordo"
    
    # Seleção de departamento
    "dropdown_departamento": 'span[data-id="qdeptcontainer_value"]',
    "item_departamento": "div.zd_v2-listitem-multiLineValue",
    "tab_whatsapp": "//div[@class='zd_v2-tab-tabText zd_v24af66c9aeb zd_v2050393fdda zd_v2eb439ba1e6 zd_v2577c9fa95f' and text()='WhatsApp']",
    "tab_email": "//div[@class='zd_v2-tab-tabText zd_v24af66c9aeb zd_v2050393fdda zd_v2eb439ba1e6 zd_v2577c9fa95f' and text()='E-mail']",
}


def avisar_modal_abriu():
    """Loga que o modal do WhatsApp foi aberto."""
    logging.info(">>> MODAL DO WHATSAPP ABERTO.")


def modal_esta_aberto(driver, timeout=3):
    """
    Verifica se o modal do WhatsApp está aberto.
    """
    try:
        modal = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((
                By.XPATH,
                "//div[contains(@class,'zd_v2') and .//button[contains(.,'Enviar')]]"
            ))
        )
        return modal.is_displayed()
    except TimeoutException:
        try:
            el = driver.find_element(By.CSS_SELECTOR, "div.zd_v2-lookup-box")
            return el.is_displayed()
        except Exception:
            return False


def fechar_ui_flutuante(driver):
    """Fecha dropdowns/backdrops/overlays que possam travar o próximo passo."""
    try:
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        time.sleep(0.2)
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
    except Exception:
        pass
    try:
        driver.execute_script("""
            (function(){
                var sels = [
                    '[class*="overlay"]',
                    '[class*="backdrop"]',
                    '[class*="modal-backdrop"]',
                    '[class*="scrim"]'
                ];
                sels.forEach(function(s){
                    document.querySelectorAll(s).forEach(function(el){ el.style.display='none'; });
                });
            })();
        """)
    except Exception:
        pass


def clicar_seguro(driver, wait, by, selector, dry_run=False, tentativas=3, timeout_total=10, timeout_por_tentativa=None, scroll=True, **kwargs):
    """Clique resiliente com compatibilidade retroativa."""
    last_err = None
    max_tentativas = tentativas or 1

    for i in range(1, max_tentativas + 1):
        try:
            tmo = timeout_por_tentativa if timeout_por_tentativa is not None else max(2, int((timeout_total or 10) / max_tentativas))
            _wait = WebDriverWait(driver, tmo)

            el = _wait.until(EC.presence_of_element_located((by, selector)))
            if scroll:
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'nearest'});", el)
                except Exception:
                    pass
            el = _wait.until(EC.element_to_be_clickable((by, selector)))

            if dry_run:
                logging.info(f"[DRY-RUN] Clique em {selector}")
                return True

            el.click()
            return True

        except Exception as e:
            last_err = e
            logging.debug(f"[clicar_seguro] tentativa {i}/{max_tentativas} falhou: {type(e).__name__}")
            if i < max_tentativas:
                time.sleep(0.4 * i)
            
            if i == max_tentativas:
                try:
                    el = driver.find_element(by, selector)
                    if not dry_run:
                        driver.execute_script("arguments[0].click();", el)
                    return True
                except Exception:
                    pass

    logging.error(f"[clicar_seguro] Falha ao clicar em {selector}: {last_err}")
    return False


def take_screenshot(driver, base_name: str, folder: str = "screenshots") -> str:
    """Salva um screenshot com timestamp."""
    try:
        import os
        os.makedirs(folder, exist_ok=True)
        from datetime import datetime
        import re
        
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_name = re.sub(r"[^0-9A-Za-z_-]+", "_", base_name)[:80] or "screenshot"
        out_path = os.path.join(folder, f"{safe_name}_{ts}.png")
        
        driver.save_screenshot(out_path)
        abs_path = os.path.abspath(out_path)
        logging.error(f"Screenshot salvo em: {abs_path}")
        return abs_path
    except Exception as e:
        logging.error(f"Falha ao salvar screenshot: {e}")
        return ""


def fechar_alerta_sem_telefone(driver):
    """Fecha o alerta quando não há telefone vinculado."""
    try:
        alerta = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[contains(., 'nenhum número') or contains(., 'no phone number') or contains(., 'sem número')]")
            )
        )
        try:
            botao_ok = alerta.find_element(By.XPATH, ".//button[.//span[normalize-space()='Ok'] or normalize-space()='Ok']")
        except NoSuchElementException:
            botao_ok = driver.find_element(By.XPATH, "//button[normalize-space()='Ok']")
        driver.execute_script("arguments[0].click();", botao_ok)
        logging.warning("Fechado alerta: cliente sem telefone cadastrado.")
        return True
    except TimeoutException:
        return False
    except Exception:
        return False


def abrir_modal_whatsapp(driver, nome_cliente, dry_run=False, max_tentativas=2):
    """Abre o modal do WhatsApp."""
    wait = WebDriverWait(driver, 15)
    
    logging.info(f"[{nome_cliente}] Abrindo modal WhatsApp...")
    fechar_ui_flutuante(driver)
    
    if not clicar_seguro(driver, WebDriverWait(driver, 12),
                        By.CSS_SELECTOR, SELETORES_MESSAGING["botao_whatsapp"],
                        timeout_total=10, timeout_por_tentativa=5, scroll=True):
        logging.warning(f"[{nome_cliente}] Falha ao clicar no ícone WhatsApp")
        return False
    
    if fechar_alerta_sem_telefone(driver):
        take_screenshot(driver, f"alerta_sem_telefone_{nome_cliente}")
        return False
    
    apareceu = False
    for _ in range(14):
        if modal_esta_aberto(driver, timeout=3):
            apareceu = True
            break
        time.sleep(0.6)
    
    if apareceu:
        logging.info(f"[{nome_cliente}] ✅ Modal do WhatsApp aberto com sucesso")
        avisar_modal_abriu()
        time.sleep(2.5)
        return True
    else:
        logging.error(f"[{nome_cliente}] ❌ Falha ao abrir modal do WhatsApp")
        return False


def selecionar_canal_e_modelo(driver, canal_substr: str, nome_template: str, ancoras: list, timeout=15) -> bool:
    """Seleciona o Modelo de mensagem."""
    wait = WebDriverWait(driver, timeout)
    short = WebDriverWait(driver, 5)

    # --- SELEÇÃO DE CANAL ---
    fechar_ui_flutuante(driver)
    
    try:
        lbl_canal = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//label[normalize-space()='Canal do WhatsApp']"))
        )
        canal_input = lbl_canal.find_element(
            By.XPATH, ".//following::input[contains(@class,'secondarydropdown-textBox')][1]"
        )

        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", canal_input)
        try:
            short.until(EC.element_to_be_clickable(canal_input)).click()
        except Exception:
            driver.execute_script("arguments[0].click();", canal_input)

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//li[@role='option']")))
    except Exception as e:
        logging.error(f"Falha ao abrir dropdown do CANAL: {e}")
        return False
    
    try:
        opcoes = [li for li in driver.find_elements(By.XPATH, "//li[@role='option']") if li.is_displayed()]
        for op in opcoes:
            if canal_substr in op.text:
                op.click()
                logging.info(f"Canal '{canal_substr}' selecionado.")
                time.sleep(0.5)
                break
    except Exception:
        pass

    # --- SELEÇÃO DE TEMPLATE ---
    try:
        label = wait.until(EC.presence_of_element_located((By.XPATH, "//label[normalize-space()='Modelo de mensagem']")))
        modelo_input = label.find_element(By.XPATH, ".//following::input[contains(@class,'secondarydropdown-textBox')][1]")
    except Exception:
        logging.error("Input de 'Modelo de mensagem' não encontrado.")
        return False

    fechar_ui_flutuante(driver)

    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", modelo_input)
        try:
            modelo_input.click()
        except Exception:
            driver.execute_script("arguments[0].click();", modelo_input)
        wait.until(EC.presence_of_element_located((By.XPATH, "//li[@role='option']")))
    except Exception as e:
        logging.error(f"Falha ao abrir o dropdown de modelos: {e}")
        return False

    # Busca template
    candidato = None
    
    # 1. Nome exato
    try:
        candidatos = driver.find_elements(By.XPATH, f"//li[@role='option' and .//div[contains(@class,'listTitle') and normalize-space()='{nome_template}']]")
        candidatos = [c for c in candidatos if c.is_displayed()]
        if candidatos: candidato = candidatos[0]
    except Exception: pass

    # 2. Nome parcial
    if not candidato:
        try:
            nome_norm = nome_template.lower()
            itens = [e for e in driver.find_elements(By.XPATH, "//li[@role='option']") if e.is_displayed()]
            for it in itens:
                try:
                    t = it.text.strip().lower()
                    if nome_norm in t:
                        candidato = it
                        break
                except: continue
        except Exception: pass

    if candidato:
        try:
            candidato.click()
            logging.info(f"Template '{nome_template}' selecionado.")
            time.sleep(0.5)
            return True
        except Exception:
            driver.execute_script("arguments[0].click();", candidato)
            return True
            
    logging.error(f"Template '{nome_template}' não encontrado.")
    return False


def enviar_mensagem_whatsapp(driver, nome_cliente, dry_run=False, modo_semi_assistido=True, 
                           timeout_envio_manual=600, template_nome=None, ancoras_template=None):
    """Envia a mensagem."""
    wait = WebDriverWait(driver, 15)
    xpath_btn_enviar = "//div[contains(@class,'zd_v2')]//button[contains(.,'Enviar')]"
    
    logging.info(f"[{nome_cliente}] 📝 Preparando envio")
    
    try:
        WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, xpath_btn_enviar)))
    except TimeoutException:
        logging.error(f"[{nome_cliente}] ❌ Botão 'Enviar' não ficou clicável")
        return False
    
    if modo_semi_assistido:
        if dry_run:
            logging.info(f"[{nome_cliente}] [DRY-RUN] Simulando espera manual...")
            return True
        else:
            logging.info(f"[{nome_cliente}] ⏸️ AGUARDANDO USUÁRIO CLICAR EM 'ENVIAR'...")
            try:
                WebDriverWait(driver, timeout_envio_manual).until(
                    EC.invisibility_of_element_located((By.XPATH, SELETORES_MESSAGING["modal_dialog_xpath"]))
                )
                logging.info(f"[{nome_cliente}] ✅ Modal fechado (envio manual concluído)")
                return True
            except TimeoutException:
                logging.warning(f"[{nome_cliente}] ⏱️ Timeout envio manual")
                return False
    else:
        if dry_run:
            logging.info(f"[{nome_cliente}] [DRY-RUN] Simulando clique 'Enviar'")
            return True
        else:
            logging.info(f"[{nome_cliente}] 🚀 Clicando em 'Enviar'...")
            if clicar_seguro(driver, wait, By.XPATH, xpath_btn_enviar, timeout_por_tentativa=5):
                time.sleep(2)
                logging.info(f"[{nome_cliente}] ✅ Mensagem enviada (assumido)!")
                return True
            return False