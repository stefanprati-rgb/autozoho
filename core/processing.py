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