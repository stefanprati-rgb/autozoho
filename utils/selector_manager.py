# Arquivo: utils/selector_manager.py
# -*- coding: utf-8 -*-
"""
Gerenciador de Seletores com Fallback Automático
Carrega seletores do JSON e tenta múltiplas estratégias para localizar elementos.
"""
import json
import os
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class SelectorManager:
    """Gerencia seletores CSS e XPath com fallback automático"""
    
    def __init__(self, json_path='config/zoho_selectors.json'):
        """
        Inicializa o gerenciador carregando os seletores do JSON
        
        Args:
            json_path: Caminho relativo ao diretório raiz do projeto
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full_path = os.path.join(base_dir, json_path)
        
        with open(full_path, 'r', encoding='utf-8') as f:
            self.selectors = json.load(f)
        
        logging.info(f"✅ Seletores carregados de: {json_path}")
    
    def get_selector(self, *path):
        """
        Navega pelo JSON usando path notation
        
        Exemplo:
            get_selector('contato', 'campos', 'celular', 'input_css')
            
        Returns:
            str: O seletor encontrado ou None
        """
        current = self.selectors
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current
    
    def find_element_safe(self, driver, *path, wait_time=10, required=True):
        """
        Tenta localizar um elemento usando múltiplas estratégias:
        1. CSS Selector
        2. XPath
        3. Seletores alternativos (se disponíveis)
        
        Args:
            driver: WebDriver do Selenium
            *path: Caminho para o seletor no JSON (ex: 'contato', 'campos', 'celular')
            wait_time: Tempo máximo de espera
            required: Se True, loga erro quando não encontra. Se False, apenas aviso.
            
        Returns:
            WebElement ou None
        """
        wait = WebDriverWait(driver, wait_time)
        
        # Navega até o objeto que contém os seletores
        selector_obj = self.selectors
        for key in path:
            if isinstance(selector_obj, dict) and key in selector_obj:
                selector_obj = selector_obj[key]
            else:
                if required:
                    logging.error(f"❌ Caminho inválido no JSON: {' > '.join(path)}")
                return None
        
        # Lista de estratégias (ordem de prioridade)
        strategies = [
            ('css', By.CSS_SELECTOR),
            ('xpath', By.XPATH),
            ('label_css', By.CSS_SELECTOR),
            ('label_xpath', By.XPATH),
            ('input_css', By.CSS_SELECTOR),
            ('valor_xpath', By.XPATH)
        ]
        
        for key, by_type in strategies:
            if key in selector_obj:
                selector = selector_obj[key]
                try:
                    element = wait.until(EC.presence_of_element_located((by_type, selector)))
                    logging.debug(f"✅ Elemento encontrado usando '{key}': {selector}")
                    return element
                except Exception as e:
                    logging.debug(f"⚠️ Falha com '{key}': {selector} - {e}")
                    continue
        
        # Se chegou aqui, nenhuma estratégia funcionou
        nivel = "ERROR" if required else "WARNING"
        logging.log(
            logging.ERROR if required else logging.WARNING,
            f"❌ Elemento não encontrado: {' > '.join(path)}"
        )
        return None
    
    def find_elements_safe(self, driver, *path, wait_time=10):
        """
        Similar ao find_element_safe, mas retorna uma lista de elementos
        """
        wait = WebDriverWait(driver, wait_time)
        
        selector_obj = self.selectors
        for key in path:
            if isinstance(selector_obj, dict) and key in selector_obj:
                selector_obj = selector_obj[key]
            else:
                return []
        
        strategies = [
            ('css', By.CSS_SELECTOR),
            ('xpath', By.XPATH)
        ]
        
        for key, by_type in strategies:
            if key in selector_obj:
                selector = selector_obj[key]
                try:
                    elements = driver.find_elements(by_type, selector)
                    if elements:
                        logging.debug(f"✅ {len(elements)} elemento(s) encontrado(s) usando '{key}'")
                        return elements
                except Exception as e:
                    logging.debug(f"⚠️ Falha com '{key}': {e}")
                    continue
        
        return []
    
    def click_element(self, driver, *path, wait_time=10):
        """
        Localiza e clica em um elemento de forma segura
        
        Returns:
            bool: True se clicou com sucesso, False caso contrário
        """
        element = self.find_element_safe(driver, *path, wait_time=wait_time)
        if element:
            try:
                element.click()
                logging.info(f"✅ Clicou em: {' > '.join(path)}")
                return True
            except Exception as e:
                logging.error(f"❌ Erro ao clicar em {' > '.join(path)}: {e}")
                return False
        return False
    
    def get_text(self, driver, *path, wait_time=10, default=""):
        """
        Localiza um elemento e retorna seu texto
        
        Returns:
            str: Texto do elemento ou valor default
        """
        element = self.find_element_safe(driver, *path, wait_time=wait_time, required=False)
        if element:
            return element.text.strip()
        return default
    
    def send_keys(self, driver, text, *path, wait_time=10, clear_first=True):
        """
        Localiza um campo e envia texto
        
        Args:
            text: Texto a ser enviado
            clear_first: Se True, limpa o campo antes de digitar
            
        Returns:
            bool: True se enviou com sucesso
        """
        element = self.find_element_safe(driver, *path, wait_time=wait_time)
        if element:
            try:
                if clear_first:
                    element.clear()
                element.send_keys(text)
                logging.info(f"✅ Texto enviado para: {' > '.join(path)}")
                return True
            except Exception as e:
                logging.error(f"❌ Erro ao enviar texto para {' > '.join(path)}: {e}")
                return False
        return False


# Instância global (singleton)
_selector_manager = None

def get_selector_manager():
    """Retorna a instância singleton do SelectorManager"""
    global _selector_manager
    if _selector_manager is None:
        _selector_manager = SelectorManager()
    return _selector_manager
