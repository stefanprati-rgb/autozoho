# -*- coding: utf-8 -*-
"""
Módulo de verificação inteligente de telefone.
Verifica e prepara número de telefone para envio WhatsApp.
Usa celular se disponível, senão tenta usar telefone (se for celular).
"""

import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from utils.telefone import normalizar_numero, validar_telefone_whatsapp

# Seletores para busca de telefones
SELETORES_TELEFONE = {
    # Campo celular (pode estar vazio ou preenchido)
    "celular_link": "//div[@data-id='mobile']//a[contains(@href, 'tel:')]",
    "celular_vazio": "//div[@data-id='mobile' and contains(@class, 'zd_v2-accountprofile-noData')]",
    
    # Campo telefone
    "telefone_link": "//div[@data-id='phone']//a[contains(@href, 'tel:')]",
}


def buscar_numero_celular(driver, timeout=2):
    """
    Busca o número de celular do cliente na página.
    
    Returns:
        str ou None: Número normalizado se encontrado e válido, None caso contrário
    """
    try:
        # Verifica se campo celular está vazio
        try:
            celular_vazio = driver.find_element(By.XPATH, SELETORES_TELEFONE["celular_vazio"])
            if celular_vazio.is_displayed():
                logging.debug("Campo celular está vazio.")
                return None
        except (NoSuchElementException, TimeoutException):
            pass  # Campo não está vazio, continua
        
        # Tenta buscar link do celular
        celular_link = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, SELETORES_TELEFONE["celular_link"]))
        )
        
        if celular_link.is_displayed():
            numero = celular_link.text.strip()
            if numero:
                # Normaliza e valida
                numero_normalizado = normalizar_numero(numero)
                if numero_normalizado:
                    valido, _ = validar_telefone_whatsapp(numero_normalizado)
                    if valido:
                        logging.debug(f"Celular encontrado e válido: {numero_normalizado}")
                        return numero_normalizado
                    else:
                        logging.debug(f"Celular encontrado mas inválido: {numero}")
                        return None
        
        return None
    except (TimeoutException, NoSuchElementException):
        logging.debug("Campo celular não encontrado ou vazio.")
        return None
    except Exception as e:
        logging.error(f"Erro ao buscar celular: {e}")
        return None


def extrair_numero_telefone(driver, timeout=2):
    """
    Extrai o número do campo telefone (link tel:).
    
    Returns:
        str ou None: Número extraído (não normalizado) ou None se não encontrado
    """
    try:
        telefone_link = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, SELETORES_TELEFONE["telefone_link"]))
        )
        
        if telefone_link.is_displayed():
            numero = telefone_link.text.strip()
            if numero:
                logging.debug(f"Telefone encontrado: {numero}")
                return numero
        
        return None
    except (TimeoutException, NoSuchElementException):
        logging.debug("Campo telefone não encontrado ou vazio.")
        return None
    except Exception as e:
        logging.error(f"Erro ao extrair telefone: {e}")
        return None


def verificar_e_preparar_telefone(driver, nome_cliente):
    """
    Verifica e prepara número de telefone para envio WhatsApp.
    Usa celular se disponível, senão tenta usar telefone (se for celular).
    
    Fluxo:
    1. Tenta buscar celular
    2. Se celular válido, retorna celular
    3. Se não, tenta buscar telefone
    4. Normaliza telefone
    5. Valida se telefone é celular (não fixo)
    6. Retorna telefone se válido
    
    Args:
        driver: WebDriver do Selenium
        nome_cliente: Nome do cliente (para logs)
    
    Returns:
        dict: {
            'sucesso': bool,
            'numero': str ou None,
            'origem': 'celular' ou 'telefone' ou None,
            'motivo_falha': str ou None
        }
    """
    logging.info(f"[{nome_cliente}] 🔍 Verificando telefones disponíveis...")
    
    # 1. Tenta buscar celular
    celular = buscar_numero_celular(driver)
    if celular:
        logging.info(f"[{nome_cliente}] ✅ Celular válido encontrado: {celular}")
        return {
            'sucesso': True,
            'numero': celular,
            'origem': 'celular',
            'motivo_falha': None
        }
    
    logging.info(f"[{nome_cliente}] ℹ️ Celular não disponível, verificando telefone...")
    
    # 2. Se não tem celular válido, tenta telefone
    telefone = extrair_numero_telefone(driver)
    if not telefone:
        logging.warning(f"[{nome_cliente}] ❌ Cliente não possui celular nem telefone")
        return {
            'sucesso': False,
            'numero': None,
            'origem': None,
            'motivo_falha': 'Cliente não possui celular nem telefone cadastrado'
        }
    
    # 3. Normaliza telefone
    telefone_normalizado = normalizar_numero(telefone)
    if not telefone_normalizado:
        logging.error(f"[{nome_cliente}] ❌ Não foi possível normalizar telefone: {telefone}")
        return {
            'sucesso': False,
            'numero': None,
            'origem': None,
            'motivo_falha': f'Não foi possível normalizar telefone: {telefone}'
        }
    
    # 4. Valida se é celular (não fixo)
    valido, motivo = validar_telefone_whatsapp(telefone_normalizado)
    if not valido:
        logging.warning(f"[{nome_cliente}] ❌ Telefone inválido ou fixo: {motivo}")
        return {
            'sucesso': False,
            'numero': None,
            'origem': None,
            'motivo_falha': f'Telefone inválido ou fixo: {motivo}'
        }
    
    # 5. Telefone é válido e é celular
    logging.info(f"[{nome_cliente}] ✅ Usando telefone como fallback: {telefone_normalizado}")
    return {
        'sucesso': True,
        'numero': telefone_normalizado,
        'origem': 'telefone',
        'motivo_falha': None
    }
