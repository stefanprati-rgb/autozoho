# -*- coding: utf-8 -*-
import re
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def normalizar_numero(numero):
    """
    Normaliza número para formato internacional +55.
    Lógica do v3.1: Trata 10 e 11 dígitos, injeta '9' se necessário.
    """
    if not numero:
        return None
        
    # Limpa tudo que não é dígito
    n = re.sub(r'\D', '', str(numero))
    
    # Se já começa com 55 (DDI Brasil), remove para padronizar a análise
    if n.startswith('55'):
        n = n[2:]
        
    # Análise pelo comprimento (sem DDI)
    if len(n) == 11: # DDD + 9 + 8 dígitos (Ex: 21 99999 8888) -> Perfeito
        if n[2] == '9': # Validação extra
            return f"+55{n}"
            
    elif len(n) == 10: # DDD + 8 dígitos (Ex: 21 8888 7777) -> Legado
        # Injeta o 9 após o DDD
        return f"+55{n[:2]}9{n[2:]}"
        
    # Outros formatos (8 ou 9 dígitos sem DDD) são descartados por segurança
    return None

def validar_numero_whatsapp(numero):
    """Valida se o número está no formato WhatsApp Brasil (+55 DDD 9 XXXX-XXXX)."""
    if not numero:
        return False, "Vazio"
        
    # Validação Regex Estrita
    match = re.match(r'^\+55(\d{2})9\d{8}$', numero)
    if not match:
        return False, f"Formato inválido: {numero}"
        
    # Validação de DDD (Blacklist de inexistentes)
    try:
        ddd = int(match.group(1))
        ddds_invalidos = {
            0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 23, 25, 26, 29, 30, 
            36, 39, 52, 56, 57, 58, 59, 70, 72, 76, 78, 80, 90
        }
        if ddd in ddds_invalidos:
            return False, f"DDD inválido: {ddd}"
        return True, "Válido"
    except:
        return False, "Erro Validação"

def buscar_numeros_telefone_cliente(driver, nome_cliente, wait_timeout=10):
    """
    Busca e normaliza números dos campos 'Celular' e 'Telefone'.
    Retorna lista de dicionários únicos.
    """
    wait = WebDriverWait(driver, wait_timeout)
    numeros_encontrados = []
    
    # 1. Buscar campo CELULAR
    try:
        celulares = driver.find_elements(By.XPATH, "//label[contains(., 'Celular')]/following::a[contains(@href, 'tel:')]")
        if celulares and celulares[0].text.strip():
            texto_original = celulares[0].text.strip()
            norm = normalizar_numero(texto_original)
            if norm:
                valido, msg = validar_numero_whatsapp(norm)
                if valido:
                    numeros_encontrados.append({'numero': norm, 'campo': 'celular', 'original': texto_original})
                    logging.info(f"[{nome_cliente}] ✅ CELULAR válido: {norm}")
    except Exception: pass
    
    # 2. Buscar campo TELEFONE
    try:
        telefones = driver.find_elements(By.XPATH, "//label[contains(., 'Telefone')]/following::a[contains(@href, 'tel:')]")
        if telefones and telefones[0].text.strip():
            texto_original = telefones[0].text.strip()
            norm = normalizar_numero(texto_original)
            if norm:
                valido, msg = validar_numero_whatsapp(norm)
                if valido:
                    numeros_encontrados.append({'numero': norm, 'campo': 'telefone', 'original': texto_original})
                    logging.info(f"[{nome_cliente}] ✅ TELEFONE válido: {norm}")
    except Exception: pass
    
    # 3. Deduplicação (Se celular == telefone, remove um)
    unicos = []
    vistos = set()
    for item in numeros_encontrados:
        if item['numero'] not in vistos:
            unicos.append(item)
            vistos.add(item['numero'])
            
    return unicos