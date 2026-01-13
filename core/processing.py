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
    recarregar_pagina_cliente,
    modal_esta_aberto
)
# IMPORTANTE: Importamos as funções de validação atualizadas
from utils.telefone import (
    buscar_numeros_telefone_cliente, 
    normalizar_numero, 
    validar_telefone_whatsapp
)
from utils.screenshots import take_screenshot


def fechar_modal_robusto(driver, nome_cliente="", tentativas=3):
    """
    Tenta fechar o modal do WhatsApp de forma robusta usando múltiplas estratégias.
    Isso é crítico para garantir que o próximo cliente seja processado corretamente.
    """
    for i in range(tentativas):
        try:
            # 1. Verifica se o modal está aberto
            if not modal_esta_aberto(driver, timeout=2):
                logging.debug(f"[{nome_cliente}] Modal já está fechado.")
                return True
            
            # 2. Tenta clicar no botão X (se existir)
            try:
                btn_fechar = driver.find_element(
                    By.XPATH, 
                    "//button[contains(@class, 'close') or @aria-label='Close' or contains(@title, 'Fechar')] | "
                    "//div[contains(@class, 'zd_v2')]//button[.//span[text()='×' or text()='X']]"
                )
                driver.execute_script("arguments[0].click();", btn_fechar)
                time.sleep(0.5)
                if not modal_esta_aberto(driver, timeout=1):
                    logging.debug(f"[{nome_cliente}] Modal fechado via botão X.")
                    return True
            except:
                pass
            
            # 3. Tenta ESC múltiplas vezes
            fechar_ui_flutuante(driver)
            time.sleep(0.3)
            
            # 4. Verifica novamente
            if not modal_esta_aberto(driver, timeout=1):
                logging.debug(f"[{nome_cliente}] Modal fechado via ESC.")
                return True
            
            # 5. Último recurso: Clica fora do modal (no background)
            try:
                body = driver.find_element(By.TAG_NAME, "body")
                ActionChains(driver).move_to_element_with_offset(body, 10, 10).click().perform()
                time.sleep(0.3)
            except:
                pass
                
        except Exception as e:
            logging.debug(f"[{nome_cliente}] Erro ao fechar modal (tentativa {i+1}): {e}")
    
    logging.warning(f"[{nome_cliente}] ⚠️ Modal pode não ter sido fechado corretamente.")
    return False

# Seletores para Edição de Contato (Baseado na v1 e estrutura padrão Zoho)
SELETOR_BOTAO_EDITAR = 'button[data-id="iconContainer"]' 
SELETOR_BOTAO_SALVAR = 'button[data-id="saveButtonId"]' 

def corrigir_telefones_na_interface(driver, correcoes, nome_cliente):
    """
    Abre o modo de edição UMA VEZ e corrige todos os campos necessários (Celular e/ou Telefone).
    
    Args:
        driver: WebDriver do Selenium
        correcoes: Lista de dicts com {'campo_tipo': 'mobile'/'phone', 'numero': '+55...', 'label': 'Celular'/'Telefone'}
        nome_cliente: Nome do cliente para logs
    """
    if not correcoes:
        return True
        
    wait = WebDriverWait(driver, 10)
    
    try:
        campos_str = ", ".join([c['label'] for c in correcoes])
        logging.info(f"[{nome_cliente}] 🛠️ Iniciando correção de {len(correcoes)} campo(s): {campos_str}")
        
        # 1. Clicar no botão de editar (lápis) - UMA VEZ
        try:
            btn_editar = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, SELETOR_BOTAO_EDITAR)))
        except Exception:
            btn_editar = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Edit') or contains(@class, 'edit')]")
            
        btn_editar.click()
        time.sleep(1.5)
        
        # 2. Corrigir TODOS os campos necessários
        for correcao in correcoes:
            campo_tipo = correcao['campo_tipo']
            numero_corrigido = correcao['numero']
            label_texto = correcao['label']
            
            try:
                # Localizar o campo
                campo_input = None
                try:
                    seletor_input = f'input[data-id="{campo_tipo}"]'
                    campo_input = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, seletor_input)))
                except Exception:
                    campo_input = driver.find_element(By.XPATH, f"//label[contains(., '{label_texto}')]/following::input[1]")

                # Limpar e Inserir novo número
                campo_input.click()
                time.sleep(0.3)
                campo_input.send_keys(Keys.CONTROL, "a")
                campo_input.send_keys(Keys.DELETE)
                time.sleep(0.3)
                campo_input.send_keys(numero_corrigido)
                time.sleep(0.3)
                
                logging.info(f"[{nome_cliente}] ✏️ {label_texto}: {numero_corrigido}")
                
            except Exception as e:
                logging.error(f"[{nome_cliente}] ⚠️ Erro ao preencher '{label_texto}': {e}")
                # Continua para tentar corrigir os outros campos
        
        # 3. Salvar UMA VEZ (todos os campos de uma vez)
        time.sleep(0.5)
        btn_salvar = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, SELETOR_BOTAO_SALVAR)))
        btn_salvar.click()
        time.sleep(2)
        
        logging.info(f"[{nome_cliente}] ✅ Todos os campos salvos com sucesso!")
        time.sleep(2)
        return True
        
    except Exception as e:
        logging.error(f"[{nome_cliente}] ❌ Falha ao editar telefones: {e}")
        take_screenshot(driver, f"erro_edicao_telefones_{nome_cliente}")
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        time.sleep(1)
        return False

def processar_pagina_cliente(driver, nome_cliente, departamento, template_nome, ancoras, dry_run=False):
    """
    Processa a página do cliente:
    1. Verifica se os números (Celular E Telefone) precisam de correção (falta +55 e/ou 9º dígito).
    2. Se precisar, corrige AMBOS na UI de uma vez.
    3. Busca os números (agora corrigidos).
    4. Envia a mensagem.
    """
    logging.info(f"--- Processando: {nome_cliente} ---")
    wait = WebDriverWait(driver, 10)
    
    # -----------------------------------------------------------
    # ETAPA 1: VERIFICAÇÃO E CORREÇÃO PRÉVIA (Auto-Healing)
    # -----------------------------------------------------------
    # Verifica AMBOS os campos e acumula as correções necessárias
    campos_para_verificar = [
        ('mobile', 'Celular', "//label[contains(., 'Celular')]/following::a[1] | //label[contains(., 'Celular')]/following::span[1]"),
        ('phone', 'Telefone', "//label[contains(., 'Telefone')]/following::a[1] | //label[contains(., 'Telefone')]/following::span[1]")
    ]
    
    correcoes_necessarias = []
    
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
                    logging.warning(f"[{nome_cliente}] {label_campo} '{texto_tel}' inválido ({msg})")
                    
                    # Tenta calcular a correção (ex: adicionar o +55 e/ou 9)
                    novo_numero = normalizar_numero(texto_tel)
                    
                    # Verifica se a correção proposta é válida
                    if novo_numero:
                        novo_eh_valido, _ = validar_telefone_whatsapp(novo_numero)
                        if novo_eh_valido:
                            logging.info(f"[{nome_cliente}] {label_campo}: '{texto_tel}' → '{novo_numero}'")
                            correcoes_necessarias.append({
                                'campo_tipo': campo_tipo,
                                'numero': novo_numero,
                                'label': label_campo
                            })
                        else:
                            logging.warning(f"[{nome_cliente}] Correção '{novo_numero}' ainda inválida.")
                    else:
                        logging.warning(f"[{nome_cliente}] Não foi possível normalizar '{texto_tel}'.")
                else:
                    logging.info(f"[{nome_cliente}] {label_campo} '{texto_tel}' já está correto.")
                    
        except Exception as e:
            logging.debug(f"[{nome_cliente}] Erro ao verificar '{label_campo}': {e}")

    # Se houver correções necessárias, executa TODAS de uma vez
    if correcoes_necessarias and not dry_run:
        corrigir_telefones_na_interface(driver, correcoes_necessarias, nome_cliente)
    elif correcoes_necessarias and dry_run:
        logging.info(f"[DRY-RUN] Simularia {len(correcoes_necessarias)} correção(ões)")

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
            fechar_modal_robusto(driver, nome_cliente)
            continue

        # B. Selecionar Template
        if not selecionar_canal_e_modelo(driver, canal_substr=departamento, nome_template=template_nome, ancoras=ancoras):
            logging.error(f"[{nome_cliente}] Falha ao selecionar template.")
            # CRÍTICO: Fechar o modal antes de passar para o próximo cliente
            fechar_modal_robusto(driver, nome_cliente)
            time.sleep(1)  # Dar tempo para UI estabilizar
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