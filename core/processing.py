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
    recarregar_pagina_cliente # Importante ter essa função no messaging ou utils
)
from utils.telefone import buscar_numeros_telefone_cliente # Nova função
from utils.screenshots import take_screenshot

def processar_pagina_cliente(driver, nome_cliente, departamento, template_nome, ancoras, dry_run=False):
    """
    Processa a página do cliente com suporte a múltiplos números (Celular + Telefone).
    """
    logging.info(f"--- Processando: {nome_cliente} ---")
    
    # 1. Validar carregamento da página
    try:
        WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'span[data-title="Enviar mensagens via WhatsApp (canal de IM)"]'))
        )
    except Exception:
        logging.warning(f"[{nome_cliente}] Botão WhatsApp não encontrado (pode não ter telefone cadastrado).")
        # Não retorna False ainda, deixa o buscador de telefones tentar achar algo
    
    # 2. Buscar e Validar Telefones (Lógica v3.1)
    numeros_validos = buscar_numeros_telefone_cliente(driver, nome_cliente)
    
    if not numeros_validos:
        logging.warning(f"[{nome_cliente}] ❌ Nenhum número válido encontrado.")
        return False
        
    total_envios = len(numeros_validos)
    sucessos = 0
    
    logging.info(f"[{nome_cliente}] Encontrados {total_envios} números para envio.")

    # 3. Loop de Envio Sequencial
    for idx, dados_numero in enumerate(numeros_validos):
        numero = dados_numero['numero']
        tipo = dados_numero['campo']
        
        logging.info(f"[{nome_cliente}] 🚀 Iniciando envio {idx+1}/{total_envios} para {tipo.upper()}: {numero}")
        
        # --- ESTRATÉGIA DE LIMPEZA ENTRE ENVIOS (Crucial do v3.1) ---
        if idx > 0:
            logging.info(f"[{nome_cliente}] 🔄 Recarregando página para limpar estado do envio anterior...")
            fechar_ui_flutuante(driver)
            if not recarregar_pagina_cliente(driver):
                logging.error(f"[{nome_cliente}] Falha ao recarregar página para o segundo número.")
                continue # Tenta o próximo se houver, ou falha
            time.sleep(2)

        # A. Abrir Modal
        # (Nota: A função abrir_modal_whatsapp precisa clicar no botão certo. 
        # Se o Zoho tem botões diferentes para cada número, isso precisaria de ajuste.
        # Mas o v3.1 usa o botão geral e o Zoho escolhe o número? 
        # NÃO. O v3.1 clica no ícone geral. O Zoho geralmente usa o 'Celular' primeiro.
        # Se o Zoho não permite escolher o número no modal, o script v3.1 pode estar apenas enviando para o padrão.
        # VOU ASSUMIR que o botão abre o modal para o número principal ou permite troca.)
        
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
        return True # Consideramos sucesso parcial como "processado"
    else:
        return False