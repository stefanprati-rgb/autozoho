import os
import logging
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options as EdgeOptions

def iniciar_driver(headless=False, use_user_profile=False, instance_id=None):
    """
    Inicia uma instância do Microsoft Edge.
    
    Args:
        headless: Se True, executa sem interface gráfica
        use_user_profile: Se True, usa o perfil do usuário para manter sessão
        instance_id: ID da instância (1-4) para posicionamento de janelas lado a lado
                    Se None, usa comportamento padrão (maximizado)
    
    Returns:
        WebDriver instance ou None em caso de erro
    """
    # Configurações de tela para múltiplas instâncias
    SCREEN_WIDTH = 1920
    SCREEN_HEIGHT = 1080
    
    if instance_id:
        logging.info(f"Iniciando Microsoft Edge (Instância {instance_id})...")
    else:
        logging.info("Iniciando Microsoft Edge...")
    
    driver_path = r"C:\msedgedriver\msedgedriver.exe"
    user_data_dir = os.path.join(os.environ['LOCALAPPDATA'], r'Microsoft\Edge\User Data')
    
    options = EdgeOptions()
    if headless:
        options.add_argument("--headless=new")
    
    if use_user_profile:
        logging.info(f"Usando perfil do usuário: {user_data_dir}")
        options.add_argument(f"user-data-dir={user_data_dir}")
        options.add_argument("profile-directory=Default")
    
    # Posicionamento para múltiplas instâncias
    # NOTA: Agora abre maximizado para melhor compatibilidade com interface do Zoho
    if instance_id is not None and not headless:
        logging.info(f"Abrindo janela maximizada (instância {instance_id})")
        options.add_argument("--start-maximized")
    else:
        options.add_argument("--start-maximized")
        
    options.add_experimental_option("detach", True)
    options.add_argument("--disable-notifications")
    
    # Suprimir logs de erro do console (opcional)
    options.add_argument("--log-level=3")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    try:
        if os.path.exists(driver_path):
            logging.info(f"Usando driver local: {driver_path}")
            service = Service(executable_path=driver_path)
            driver = webdriver.Edge(service=service, options=options)
        else:
            logging.warning(f"Driver não encontrado em {driver_path}. Tentando Selenium Manager...")
            driver = webdriver.Edge(options=options)
            
        return driver
    except Exception as e:
        logging.error(f"Erro ao iniciar Edge: {e}")
        return None
