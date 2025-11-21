# -*- coding: utf-8 -*-
import os
import re
from datetime import datetime
import logging

def take_screenshot(driver, base_name, folder="screenshots"):
    """Tira um screenshot e salva na pasta especificada."""
    try:
        if not os.path.exists(folder):
            os.makedirs(folder)
            
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_name = re.sub(r'[^\w\-]', '_', base_name)
        filename = f"{folder}/{safe_name}_{timestamp}.png"
        
        driver.save_screenshot(filename)
        logging.error(f"Screenshot salvo: {filename}")
        return filename
    except Exception as e:
        logging.error(f"Falha ao tirar screenshot: {e}")
        return None