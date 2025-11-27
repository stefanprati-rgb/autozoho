# -*- coding: utf-8 -*-
"""
Módulo de messaging do sistema de automação Zoho Desk.
Versão Otimizada: Busca em 2 Etapas e Detecção de Créditos Insuficientes.
"""

import time
import logging
import re
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
    # Novo seletor para o aviso de créditos
    "aviso_creditos": "//div[contains(@class, 'zd_v2-globalnotification-text') and (contains(., 'Créditos insuficientes') or contains(., 'Insufficient credits'))]"
}

def avisar_modal_abriu():
    logging.info(">>> MODAL DO WHATSAPP ABERTO.")

def verificar_creditos_insuficientes(driver):
    """
    Verifica se o aviso de créditos insuficientes apareceu.
    Se sim, PAUSA o script até o usuário resolver.
    """
    try:
        avisos = driver.find_elements(By.XPATH, SELETORES_MESSAGING["aviso_creditos"])
        if avisos and avisos[0].is_displayed():
            logging.critical("⛔ ALERTA CRÍTICO: CRÉDITOS INSUFICIENTES DETECTADOS!")
            print("\n" + "!"*60)
            print("🚨 PAUSA OBRIGATÓRIA: O ZOHO ESTÁ SEM CRÉDITOS 🚨")
            print("Aviso detectado: 'Desculpe! Créditos insuficientes.'")
            print("O script foi PAUSADO para evitar erros em cascata.")
            print("👉 AÇÃO: Recarregue os créditos no Zoho manualmente agora.")
            print("!"*60 + "\n")
            
            # Toca um som de alerta (bip) no Windows
            try: print("\a")
            except: pass
            
            # Pausa a execução bloqueando o terminal
            input(">>> Pressione [ENTER] aqui no terminal APÓS recarregar os créditos para continuar...")
            logging.info("Usuário retomou a execução após pausa por créditos.")
            
            # Tenta fechar o aviso se ele ainda estiver lá (clicando no X se possível ou apenas ignorando)
            try:
                btn_fechar = driver.find_element(By.XPATH, "//div[contains(@class, 'zd_v2-globalnotification-close')]")
                driver.execute_script("arguments[0].click();", btn_fechar)
            except: pass
            
            return True
    except Exception as e:
        # Não queremos que a verificação quebre o script
        pass
    return False

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
    """
    Tenta fechar modais e dropdowns pressionando ESC.
    """
    try:
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        time.sleep(0.3)
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
    
    # Verifica créditos antes mesmo de tentar abrir (caso o aviso já esteja lá de um erro anterior)
    verificar_creditos_insuficientes(driver)

    fechar_ui_flutuante(driver)
    
    if not clicar_seguro(driver, WebDriverWait(driver, 12), By.CSS_SELECTOR, SELETORES_MESSAGING["botao_whatsapp"], timeout_total=10, timeout_por_tentativa=5):
        logging.warning(f"[{nome_cliente}] Falha ao clicar no ícone WhatsApp")
        return False
    
    if fechar_alerta_sem_telefone(driver): return False
    
    for _ in range(14):
        # Verifica a cada passo do loop se apareceu o erro de crédito
        verificar_creditos_insuficientes(driver)
        
        if modal_esta_aberto(driver, timeout=3):
            logging.info(f"[{nome_cliente}] ✅ Modal aberto")
            avisar_modal_abriu()
            time.sleep(2.5)
            # Verifica novamente após o modal estabilizar
            verificar_creditos_insuficientes(driver)
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

def _buscar_e_selecionar_visual(driver, nome_template, ancoras, busca_realizada=False):
    """
    Helper interno que varre a lista visualmente para encontrar o candidato e clica.
    Retorna True se clicou, False se não achou.
    """
    try:
        # Espera opções aparecerem
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//li[@role='option']")))
        
        candidato = None
        nome_limpo = nome_template.strip()
        
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
        
        # 2. Busca pela Descrição (listdesc)
        if not candidato and ancoras:
            for ancora in ancoras:
                ancora_limpa = ancora.replace("'", "\\'")[:60]
                for op in opcoes:
                    try:
                        desc_el = op.find_element(By.XPATH, ".//div[contains(@class, 'listdesc')]")
                        if ancora_limpa in desc_el.text:
                            candidato = op
                            logging.info(f"Template encontrado (Âncora): '{ancora_limpa}...'")
                            break
                    except: continue
                if candidato: break

        if candidato:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", candidato)
            try: candidato.click()
            except: driver.execute_script("arguments[0].click();", candidato)
            time.sleep(1.5)
            return True
        
        # Log de diagnóstico se falhar
        if busca_realizada:
             titulos = []
             for op in opcoes[:5]:
                 try: titulos.append(op.find_element(By.XPATH, ".//div[contains(@class, 'listTitle')]").text)
                 except: pass
             logging.debug(f"Itens visíveis na busca: {titulos}")
             
        return False

    except Exception:
        return False

def selecionar_canal_e_modelo(driver, canal_substr: str, nome_template: str, ancoras: list, timeout=15) -> bool:
    """
    Seleciona Canal e Template em 2 ETAPAS (Nome -> Conteúdo).
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

    # --- 2. SELECIONAR TEMPLATE (Lógica em 2 Etapas) ---
    logging.info(f"Procurando template: '{nome_template}'")
    try:
        label = wait.until(EC.presence_of_element_located((By.XPATH, "//label[normalize-space()='Modelo de mensagem' or contains(.,'Template')]")))
        modelo_input = label.find_element(By.XPATH, ".//following::input[contains(@class,'secondarydropdown-textBox')][1]")
        
        if nome_template.lower() in (modelo_input.get_attribute("value") or "").lower():
            return True

        # Abre Dropdown
        fechar_ui_flutuante(driver)
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", modelo_input)
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", modelo_input)
        # Aguarda dropdown abrir (otimizado)
        time.sleep(0.5) 
        
        search_box = None
        try:
            search_box = driver.find_element(By.CSS_SELECTOR, "input[placeholder='Search']")
        except: pass

        if search_box and search_box.is_displayed():
            # --- TENTATIVA 1: BUSCA PELO NOME SANITIZADO ---
            nome_busca_safe = re.sub(r'[^\w\s]', '', nome_template).strip()
            logging.info(f"Tentativa 1: Digitando nome '{nome_busca_safe}'...")
            
            search_box.click()
            search_box.clear()
            for char in nome_busca_safe:
                search_box.send_keys(char)
                time.sleep(0.03)  # 3x mais rápido
            time.sleep(0.8)  # Aguarda filtro processar (otimizado)

            if _buscar_e_selecionar_visual(driver, nome_template, ancoras, busca_realizada=True):
                return True
            
            # --- TENTATIVA 2: BUSCA PELO CONTEÚDO (ÂNCORA) ---
            if ancoras:
                # Pega a primeira âncora, limpa e usa as primeiras 4 palavras
                ancora_texto = ancoras[0]
                # Remove caracteres especiais para a busca
                ancora_busca = re.sub(r'[^\w\s]', '', ancora_texto).strip()
                # Pega apenas o início para não ser muito específico
                palavras = ancora_busca.split()[:4] 
                termo_ancora = " ".join(palavras)
                
                if len(termo_ancora) > 3:
                    logging.info(f"Tentativa 2: Falha no nome. Buscando por conteúdo: '{termo_ancora}'...")
                    search_box.click()
                    # Limpa (CTRL+A + DEL é mais seguro aqui)
                    search_box.send_keys(Keys.CONTROL + "a")
                    search_box.send_keys(Keys.DELETE)
                    time.sleep(0.3)
                    
                    for char in termo_ancora:
                        search_box.send_keys(char)
                        time.sleep(0.03)  # 3x mais rápido
                    time.sleep(0.8)  # Aguarda filtro processar (otimizado)

                    if _buscar_e_selecionar_visual(driver, nome_template, ancoras, busca_realizada=True):
                        return True

        # --- TENTATIVA 3: LISTA COMPLETA (Sem busca) ---
        logging.warning("Buscas falharam. Resetando filtro para tentar lista completa...")
        try:
            if search_box:
                search_box.send_keys(Keys.CONTROL + "a")
                search_box.send_keys(Keys.DELETE)
                time.sleep(0.5)  # Otimizado
        except: pass
        
        if _buscar_e_selecionar_visual(driver, nome_template, ancoras):
            return True

        logging.error(f"Template '{nome_template}' não encontrado após todas as tentativas.")
        fechar_ui_flutuante(driver)
        return False

    except Exception as e:
        logging.error(f"Erro template: {e}")
        fechar_ui_flutuante(driver)
        return False

def enviar_mensagem_whatsapp(driver, nome_cliente, dry_run=False, modo_semi_assistido=True, timeout_envio_manual=600, template_nome=None, ancoras_template=None):
    # Verificação Crítica de Créditos antes de iniciar o processo de envio
    verificar_creditos_insuficientes(driver)

    wait = WebDriverWait(driver, 15)
    xpath_btn = "//div[contains(@class,'zd_v2')]//button[contains(.,'Enviar')]"
    
    logging.info(f"[{nome_cliente}] 4️⃣ Enviando mensagem...")
    try:
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, xpath_btn)))
    except:
        logging.warning(f"[{nome_cliente}] Botão Enviar não habilitou.")
        # Pode ser que não habilitou porque não tem créditos, verifica de novo
        verificar_creditos_insuficientes(driver)
    
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
                # Verifica créditos de novo logo após clicar (caso o erro apareça só depois do clique)
                time.sleep(0.5)
                verificar_creditos_insuficientes(driver)
                
                WebDriverWait(driver, 12).until(EC.any_of(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@class,'toast')][contains(.,'envi') or contains(.,'sucesso')]")),
                    EC.presence_of_element_located((By.XPATH, "//button[contains(.,'Enviar') and @disabled]"))
                ))
                logging.info(f"[{nome_cliente}] ✅ Sucesso detectado.")
                try:
                    fechar_ui_flutuante(driver)
                except: pass
                time.sleep(1)
                return True
            except:
                logging.error("Erro pós-envio.")
                # Se falhou, pode ser crédito
                verificar_creditos_insuficientes(driver)
        else:
            logging.error("Falha clique Enviar.")
            return False
    return False

def processar_envio_completo_whatsapp(driver, nome_cliente, departamento, template_nome, ancoras_template, dry_run=False, modo_semi_assistido=True):
    logging.info(f"INICIANDO ENVIO WHATSAPP: {nome_cliente}")
    
    if not abrir_modal_whatsapp(driver, nome_cliente, dry_run): return False
    
    if not selecionar_canal_e_modelo(driver, departamento, template_nome, ancoras_template):
        take_screenshot(driver, f"falha_template_{nome_cliente}")
        logging.warning("Seleção falhou. Fechando modal...")
        fechar_ui_flutuante(driver)
        time.sleep(1)
        return False
        
    tratar_alerta_marketing(driver, nome_cliente, dry_run)
    sucesso = enviar_mensagem_whatsapp(driver, nome_cliente, dry_run, modo_semi_assistido, template_nome=template_nome, ancoras_template=ancoras_template)
    if sucesso: logging.info(f"[{nome_cliente}] ✅ ENVIO CONCLUÍDO!")
    return sucesso