# -*- coding: utf-8 -*-
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from core.messaging import abrir_modal_whatsapp, selecionar_canal_e_modelo, enviar_mensagem_whatsapp, trocar_departamento_zoho

def processar_pagina_cliente(driver, nome_cliente, departamento, template_nome, ancoras, dry_run=False):
    """Processa um cliente individual."""
    logging.info(f"--- Processando: {nome_cliente} ---")
    
    # 1. Validar Telefone (Simples verificação se existe o ícone)
    try:
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'span[data-title="Enviar mensagens via WhatsApp (canal de IM)"]')))
    except:
        logging.warning(f"Cliente {nome_cliente} sem botão de WhatsApp visível.")
        return False

    # 2. Abrir Modal
    if not abrir_modal_whatsapp(driver, nome_cliente, dry_run):
        return False

    # 3. Selecionar Template e Canal
    # Importante: O 'departamento' aqui é usado para selecionar o CANAL no dropdown do modal
    if not selecionar_canal_e_modelo(driver, canal_substr=departamento, nome_template=template_nome, ancoras=ancoras):
        return False

    # 4. Enviar
    return enviar_mensagem_whatsapp(driver, nome_cliente, dry_run, modo_semi_assistido=False)
