# -*- coding: utf-8 -*-
"""
Módulo de processamento principal da automação Zoho Desk.
"""

import os
import sys
import re
import csv
import time
import json
import logging
import unicodedata
from datetime import datetime
from difflib import SequenceMatcher

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
    InvalidSessionIdException,
    UnexpectedAlertPresentException
)

# CORREÇÃO: Importamos apenas o necessário de messaging
from core.messaging import abrir_modal_whatsapp, selecionar_canal_e_modelo, enviar_mensagem_whatsapp

# Importamos a troca de departamento do local correto
from core.departments import trocar_departamento_zoho

# =============================================================================
# FUNÇÃO DE PROCESSAMENTO DE CLIENTE (LÓGICA PRINCIPAL)
# =============================================================================

def processar_pagina_cliente(driver, nome_cliente, departamento, template_nome, ancoras, dry_run=False):
    """
    Processa a página do cliente: valida telefone e envia mensagem.
    """
    logging.info(f"--- Processando: {nome_cliente} ---")
    
    # 1. Validar se existe botão de WhatsApp (verifica se o cliente carregou)
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'span[data-title="Enviar mensagens via WhatsApp (canal de IM)"]'))
        )
    except Exception:
        logging.warning(f"Cliente {nome_cliente} sem botão de WhatsApp visível ou página não carregou.")
        return False

    # 2. Abrir Modal
    if not abrir_modal_whatsapp(driver, nome_cliente, dry_run):
        logging.error(f"Falha ao abrir modal para {nome_cliente}")
        return False

    # 3. Selecionar Template e Canal (Departamento)
    if not selecionar_canal_e_modelo(driver, canal_substr=departamento, nome_template=template_nome, ancoras=ancoras):
        logging.error(f"Falha ao selecionar template/canal para {nome_cliente}")
        return False

    # 4. Enviar Mensagem
    # Passamos modo_semi_assistido=False para envio automático
    return enviar_mensagem_whatsapp(driver, nome_cliente, dry_run, modo_semi_assistido=False)