# -*- coding: utf-8 -*-
import logging
import os
import json
from datetime import datetime

def setup_logging(loglevel, logfile):
    """Configura o sistema de logs."""
    level = getattr(logging, loglevel.upper(), logging.INFO)
    handlers = [logging.StreamHandler()]
    if logfile:
        handlers.append(logging.FileHandler(logfile, encoding='utf-8'))
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

def dump_browser_logs(driver):
    """Salva logs do console do navegador (erros de JS/Rede)."""
    try:
        logs = driver.get_log('browser')
        if logs:
            # Filtra apenas erros ou warnings para não poluir
            logs_relevantes = [l for l in logs if l['level'] in ['SEVERE', 'WARNING']]
            if logs_relevantes:
                with open("browser_console_errors.txt", "a", encoding="utf-8") as f:
                    f.write(f"\n--- {datetime.now()} ---\n")
                    for entry in logs_relevantes:
                        f.write(f"{entry}\n")
    except:
        pass

def salvar_snapshot_erro(driver, contexto):
    """
    Salva um 'Raio-X' do erro: Screenshot + HTML da página.
    Isso permite ver elementos invisíveis ou sobrepostos.
    """
    try:
        if not os.path.exists("debug_erro"):
            os.makedirs("debug_erro")
            
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_ctx = contexto.replace(" ", "_")
        
        # 1. Salva Screenshot
        img_path = f"debug_erro/{ts}_{safe_ctx}.png"
        driver.save_screenshot(img_path)
        
        # 2. Salva HTML (O código fonte da página naquele momento exato)
        html_path = f"debug_erro/{ts}_{safe_ctx}.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
            
        logging.error(f"📸 Snapshot de erro salvo em: debug_erro/ ({ts}_{safe_ctx})")
        
    except Exception as e:
        logging.error(f"Falha ao salvar snapshot de erro: {e}")