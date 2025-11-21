# -*- coding: utf-8 -*-
import logging
import os
import json
import time

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
    """Salva logs do console do navegador em arquivo (para debug)."""
    try:
        logs = driver.get_log('browser')
        if logs:
            with open("browser_logs.txt", "a", encoding="utf-8") as f:
                for entry in logs:
                    f.write(f"{entry}\n")
    except:
        pass