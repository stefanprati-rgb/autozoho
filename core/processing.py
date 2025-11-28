# Arquivo: core/processing.py
# -*- coding: utf-8 -*-
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains

# Importações Modulares
from core.messaging import (
    abrir_modal_whatsapp, 
    selecionar_canal_e_modelo, 
    enviar_mensagem_whatsapp, 
    tratar_alerta_marketing,
    fechar_ui_flutuante,
    recarregar_pagina_cliente 
)
# IMPORTANTE: Importamos as funções de validação atualizadas
from utils.telefone import (
    buscar_numeros_telefone_cliente, 
    normalizar_numero, 
    validar_telefone_whatsapp
)
from utils.screenshots import take_screenshot

# Seletores para Edição de Contato (Baseado na v1 e estrutura padrão Zoho)
SELETOR_BOTAO_EDITAR = 'button[data-id="iconContainer"]' 
SELETOR_BOTAO_SALVAR = 'button[data-id="saveButtonId"]' 

def corrigir_telefone_na_interface(driver, campo_tipo, numero_corrigido, nome_cliente):
    """
    Clica no botão editar, limpa o campo especificado (Celular ou Telefone), 
    insere o número corrigido com +55 e salva.
    
    Args:
        driver: WebDriver do Selenium
        campo_tipo: 'mobile' para Celular ou 'phone' para Telefone
        numero_corrigido: Número já normalizado com +55
        nome_cliente: Nome do cliente para logs
    """
    wait = WebDriverWait(driver, 10)
    label_texto = "Celular" if campo_tipo == "mobile" else "Telefone"
    
    try:
        logging.info(f"[{nome_cliente}] 🛠️ Iniciando correção automática do campo '{label_texto}'...")
        
        # 1. Clicar no botão de editar (lápis)
        try:
            btn_editar = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, SELETOR_BOTAO_EDITAR)))
        except Exception:
            btn_editar = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Edit') or contains(@class, 'edit')]")
            
        btn_editar.click()
        time.sleep(1.5)
        
        # 2. Localizar o campo correto (Celular ou Telefone)
        campo_input = None
        try:
            seletor_input = f'input[data-id="{campo_tipo}"]'
            campo_input = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, seletor_input)))
        except Exception:
            try:
                campo_input = driver.find_element(By.XPATH, f"//label[contains(., '{label_texto}')]/following::input[1]")
            except Exception as e:
                logging.error(f"[{nome_cliente}] ❌ Não foi possível localizar o campo '{label_texto}': {e}")
                ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                return False

        # 3. Limpar e Inserir novo número
        campo_input.click()
        time.sleep(0.3)
        campo_input.send_keys(Keys.CONTROL, "a")
        campo_input.send_keys(Keys.DELETE)
        time.sleep(0.3)
        campo_input.send_keys(numero_corrigido)
        time.sleep(0.5)
        
        # 4. Salvar
        btn_salvar = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, SELETOR_BOTAO_SALVAR)))
        btn_salvar.click()
        time.sleep(2)
        
        logging.info(f"[{nome_cliente}] ✅ Campo '{label_texto}' atualizado com sucesso para: {numero_corrigido}")
        time.sleep(2)
        return True
        
    except Exception as e:
        logging.error(f"[{nome_cliente}] ❌ Falha ao editar campo '{label_texto}' na interface: {e}")
        take_screenshot(driver, f"erro_edicao_{campo_tipo}_{nome_cliente}")
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        time.sleep(1)
        return False

def processar_pagina_cliente(driver, nome_cliente, departamento, template_nome, ancoras, dry_run=False):
    """
    Processa a página do cliente:
    1. Verifica se os números (Celular E Telefone) precisam de correção (falta +55 e/ou 9º dígito).
    2. Se precisar, corrige na UI.
    3. Busca os números (agora corrigidos).
    4. Envia a mensagem.
    """
    logging.info(f"--- Processando: {nome_cliente} ---")
    wait = WebDriverWait(driver, 10)
    
    # -----------------------------------------------------------
    # ETAPA 1: VERIFICAÇÃO E CORREÇÃO PRÉVIA (Auto-Healing)
    # -----------------------------------------------------------
    # Verifica e corrige AMBOS os campos: Celular E Telefone
    campos_para_verificar = [
        ('mobile', 'Celular', "//label[contains(., 'Celular')]/following::a[1] | //label[contains(., 'Celular')]/following::span[1]"),
        ('phone', 'Telefone', "//label[contains(., 'Telefone')]/following::a[1] | //label[contains(., 'Telefone')]/following::span[1]")
    ]
    
    for campo_tipo, label_campo, xpath_campo in campos_para_verificar:
        try:
            texto_tel = ""
            try:
                elem_tel = driver.find_element(By.XPATH, xpath_campo)
                texto_tel = elem_tel.text.strip()
            except:
                continue

            if texto_tel and texto_tel.lower() not in ['adicionar celular', 'adicionar telefone', '']:
                # Verifica se é válido
                valido, msg = validar_telefone_whatsapp(texto_tel)
                
                if not valido:
                    logging.warning(f"[{nome_cliente}] {label_campo} atual '{texto_tel}' inválido ({msg}). Tentando calcular correção...")
                    
                    # Tenta calcular a correção (ex: adicionar o +55 e/ou 9)
                    novo_numero = normalizar_numero(texto_tel)
                    
                    # Verifica se a correção proposta é válida
                    if novo_numero:
                        novo_eh_valido, _ = validar_telefone_whatsapp(novo_numero)
                        if novo_eh_valido:
                            if not dry_run:
                                # Executa a correção na UI
                                logging.info(f"[{nome_cliente}] Corrigindo {label_campo}: '{texto_tel}' → '{novo_numero}'")
                                corrigir_telefone_na_interface(driver, campo_tipo, novo_numero, nome_cliente)
                            else:
                                logging.info(f"[DRY-RUN] Simularia correção de '{texto_tel}' para '{novo_numero}'")
                        else:
                            logging.warning(f"[{nome_cliente}] Correção calculada '{novo_numero}' ainda é inválida.")
                    else:
                        logging.warning(f"[{nome_cliente}] Não foi possível normalizar o número '{texto_tel}'.")
                else:
                    logging.info(f"[{nome_cliente}] {label_campo} '{texto_tel}' já está correto.")
                    
        except Exception as e:
            logging.debug(f"[{nome_cliente}] Erro ao verificar campo '{label_campo}': {e}")

    # -----------------------------------------------------------
    # ETAPA 2: BUSCA E ENVIO (Fluxo Padrão)
    # -----------------------------------------------------------
    
    # Agora buscamos os números (se houve correção, o 'buscar' vai pegar o novo)
    numeros_validos = buscar_numeros_telefone_cliente(driver, nome_cliente)
    
    # Validação crítica: Se não achou números válidos, aborta
    if not numeros_validos:
        logging.warning(f"[{nome_cliente}] ❌ Nenhum número válido encontrado para envio.")
        return False
        
    total_envios = len(numeros_validos)
    sucessos = 0
    
    logging.info(f"[{nome_cliente}] Encontrados {total_envios} números para envio.")

    # Loop de Envio Sequencial
    for idx, dados_numero in enumerate(numeros_validos):
        numero = dados_numero['numero']
        tipo = dados_numero['campo']
        
        logging.info(f"[{nome_cliente}] 🚀 Iniciando envio {idx+1}/{total_envios} para {tipo.upper()}: {numero}")
        
        # Limpeza entre envios múltiplos
        if idx > 0:
            logging.info(f"[{nome_cliente}] 🔄 Recarregando página para limpar estado do envio anterior...")
            fechar_ui_flutuante(driver)
            if not recarregar_pagina_cliente(driver):
                logging.error(f"[{nome_cliente}] Falha ao recarregar página.")
                continue 
            time.sleep(2)

        # A. Abrir Modal
        if not abrir_modal_whatsapp(driver, nome_cliente, dry_run):
            logging.error(f"[{nome_cliente}] Falha ao abrir modal.")
            continue

        # B. Selecionar Template
        if not selecionar_canal_e_modelo(driver, canal_substr=departamento, nome_template=template_nome, ancoras=ancoras):
            logging.error(f"[{nome_cliente}] Falha ao selecionar template.")
            continue

        # C. Marketing Check
        tratar_alerta_marketing(driver, nome_cliente, dry_run)

        # D. Enviar
        if enviar_mensagem_whatsapp(driver, nome_cliente, dry_run, modo_semi_assistido=False):
            logging.info(f"[{nome_cliente}] ✅ Envio {idx+1} concluído com sucesso!")
            sucessos += 1
        else:
            logging.error(f"[{nome_cliente}] ❌ Falha no envio {idx+1}.")
            
    # Retorno Final
    if sucessos == total_envios:
        return True
    elif sucessos > 0:
        logging.warning(f"[{nome_cliente}] ⚠️ Envio parcial ({sucessos}/{total_envios}).")
        return True 
    else:
        return False