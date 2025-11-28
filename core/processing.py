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
from core.telefone_fix import obter_lista_numeros_para_envio
from utils.screenshots import take_screenshot


def processar_pagina_cliente(driver, nome_cliente, departamento, template_nome, ancoras, dry_run=False):
    """
    Processa a página do cliente:
    1. Obtém lista inteligente de números para envio (com deduplicação)
    2. Para cada número, envia mensagem WhatsApp
    
    Regras de envio:
    - Se celular == telefone → envia 1 vez
    - Se celular != telefone e ambos celular → envia 2 vezes
    - Se telefone é fixo → envia só para celular
    - Se só tem um número → envia 1 vez
    """
    logging.info(f"--- Processando: {nome_cliente} ---")
    
    # -----------------------------------------------------------
    # ETAPA 1: OBTER LISTA DE NÚMEROS (COM DEDUPLICAÇÃO)
    # -----------------------------------------------------------
    numeros_para_envio = obter_lista_numeros_para_envio(driver, nome_cliente)
    
    # Validação crítica: Se não achou números válidos, aborta
    if not numeros_para_envio:
        logging.warning(f"[{nome_cliente}] ❌ Nenhum número válido encontrado para envio.")
        return False
        
    total_envios = len(numeros_para_envio)
    sucessos = 0
    
    logging.info(f"[{nome_cliente}] 📋 {total_envios} número(s) para envio")

    # -----------------------------------------------------------
    # ETAPA 2: LOOP DE ENVIO SEQUENCIAL
    # -----------------------------------------------------------
    for idx, dados_numero in enumerate(numeros_para_envio):
        numero = dados_numero['numero']
        origem = dados_numero['origem']
        campo = dados_numero['campo']
        
        logging.info(f"[{nome_cliente}] 🚀 Iniciando envio {idx+1}/{total_envios}")
        logging.info(f"[{nome_cliente}] 📞 Número: {numero} (origem: {campo})")
        
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
            
    # -----------------------------------------------------------
    # ETAPA 3: RETORNO FINAL
    # -----------------------------------------------------------
    if sucessos == total_envios:
        logging.info(f"[{nome_cliente}] ✅ Todos os envios concluídos ({sucessos}/{total_envios})")
        return True
    elif sucessos > 0:
        logging.warning(f"[{nome_cliente}] ⚠️ Envio parcial ({sucessos}/{total_envios}).")
        return True 
    else:
        logging.error(f"[{nome_cliente}] ❌ Nenhum envio bem-sucedido.")
        return False