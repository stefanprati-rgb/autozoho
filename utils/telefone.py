# Arquivo: utils/telefone.py
# -*- coding: utf-8 -*-
import re
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def normalizar_numero(numero):
    """
    Normaliza número para formato internacional +55.
    Lógica aprimorada (v3.2): 
    - Remove zeros à esquerda (ex: 011... -> 11...).
    - Remove DDI 55 se presente.
    - Trata 10 dígitos (injeta o 9).
    - Trata 11 dígitos.
    """
    if not numero:
        return None
        
    # 1. Limpa tudo que não é dígito
    n = re.sub(r'\D', '', str(numero))
    
    # 2. Remove zeros à esquerda (ex: '0219999...' vira '219999...')
    n = n.lstrip('0')
    
    # 3. Se começar com 55 (DDI), remove.
    # Verifica novamente zeros após remover o 55 (caso '55021...')
    if n.startswith('55'):
        n = n[2:]
        n = n.lstrip('0')
        
    # 4. Análise pelo comprimento restante (DDD + Número)
    
    # Caso ideal: 11 dígitos (DDD 2 + 9 + 8 dígitos)
    if len(n) == 11: 
        if n[2] == '9': # Validação básica se é celular
            return f"+55{n}"
            
    # Caso legado: 10 dígitos (DDD 2 + 8 dígitos)
    # Ex: 21 8888 7777 -> Transforma em 21 98888 7777
    elif len(n) == 10: 
        return f"+55{n[:2]}9{n[2:]}"
        
    # Se chegou aqui, o número não se encaixa nos padrões (ex: 8 dígitos sem DDD)
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
        # DDDs que tecnicamente não existem ou são de testes
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
    
    # Função auxiliar para evitar repetição de código
    def processar_elemento(elem, tipo_campo):
        try:
            texto_original = elem.text.strip()
            if texto_original:
                norm = normalizar_numero(texto_original)
                if norm:
                    valido, msg = validar_numero_whatsapp(norm)
                    if valido:
                        numeros_encontrados.append({
                            'numero': norm, 
                            'campo': tipo_campo, 
                            'original': texto_original
                        })
                        logging.info(f"[{nome_cliente}] ✅ {tipo_campo.upper()} corrigido e válido: {texto_original} -> {norm}")
                    else:
                        logging.warning(f"[{nome_cliente}] ⚠️ {tipo_campo.upper()} normalizado mas inválido ({msg}): {texto_original}")
        except Exception as e:
            logging.debug(f"Erro ao processar elemento de telefone: {e}")

    # 1. Buscar campo CELULAR (Tenta link tel: e texto puro se falhar)
    try:
        # Tenta pegar pelo link (padrão Zoho)
        celulares = driver.find_elements(By.XPATH, "//label[contains(., 'Celular')]/following::a[contains(@href, 'tel:')]")
        # Se não achar link, tenta pegar o texto do span/div seguinte (caso o Zoho não tenha gerado link)
        if not celulares:
             celulares = driver.find_elements(By.XPATH, "//label[contains(., 'Celular')]/following::span[1]")
        
        if celulares: processar_elemento(celulares[0], 'celular')
    except Exception: pass
    
    # 2. Buscar campo TELEFONE
    try:
        telefones = driver.find_elements(By.XPATH, "//label[contains(., 'Telefone')]/following::a[contains(@href, 'tel:')]")
        if not telefones:
            telefones = driver.find_elements(By.XPATH, "//label[contains(., 'Telefone')]/following::span[1]")
            
        if telefones: processar_elemento(telefones[0], 'telefone')
    except Exception: pass
    
    # 3. Deduplicação
    unicos = []
    vistos = set()
    for item in numeros_encontrados:
        if item['numero'] not in vistos:
            unicos.append(item)
            vistos.add(item['numero'])
            
    return unicos