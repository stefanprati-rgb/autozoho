# -*- coding: utf-8 -*-
import logging
from selenium import webdriver
from selenium.webdriver.edge.options import Options as EdgeOptions

def iniciar_driver(headless=False):
    logging.info("Iniciando Microsoft Edge...")
    options = EdgeOptions()
    if headless:
        options.add_argument("--headless=new")
    
    options.add_experimental_option("detach", True)
    options.add_argument("--disable-notifications")
    
    try:
        driver = webdriver.Edge(options=options)
        driver.maximize_window()
        return driver
    except Exception as e:
        logging.error(f"Erro ao iniciar Edge: {e}")
        return None
