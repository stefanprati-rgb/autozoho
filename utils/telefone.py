# Arquivo: utils/telefone.py
# -*- coding: utf-8 -*-
import re
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def validar_telefone_whatsapp(numero):
    """
    Valida se o número está estritamente no formato WhatsApp Brasil (+55 DDD 9 XXXX-XXXX).
    Retorna (Bool, Motivo).
    """
    if not numero:
        return False, "Vazio"
        
    # Remove formatação visual para validar
    limpo = re.sub(r'\D', '', str(numero))
    
    # 1. Deve ter DDI 55
    if not limpo.startswith('55'):
        return False, "Sem DDI 55"
        
    # 2. Deve ter 13 dígitos no total (55 + 2 DDD + 9 + 8 num)
    # Ex: 55 21 9 8888 7777
    if len(limpo) != 13:
        return False, f"Tamanho incorreto ({len(limpo)} dígitos)"
        
    # 3. O nono dígito (índice 4 na string sem +) deve ser '9'
    if limpo[4] != '9':
        return False, "Sem 9º dígito"

    # 4. Validação de DDD (Blacklist de inexistentes)
    try:
        ddd = int(limpo[2:4])
        ddds_invalidos = {
            0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 23, 25, 26, 29, 30, 
            36, 39, 52, 56, 57, 58, 59, 70, 72, 76, 78, 80, 90
        }
        if ddd in ddds_invalidos:
            return False, f"DDD inválido: {ddd}"
        return True, "Válido"
    except:
        return False, "Erro Validação DDD"

def normalizar_numero(numero):
    """
    Tenta corrigir e formatar o número para o padrão +55DD9XXXXXXXX.
    Corrige falhas comuns: sem 9º dígito, zeros à esquerda, sem DDI.
    """
    if not numero:
        return None
        
    # 1. Limpeza agressiva (apenas dígitos)
    n = re.sub(r'\D', '', str(numero))
    
    # 2. Remove zeros à esquerda (ex: 011... -> 11...)
    n = n.lstrip('0')
    
    # 3. Remove DDI 55 temporariamente para padronizar a análise
    # (Assim tratamos tudo como DDD + Numero)
    if n.startswith('55'):
        n = n[2:]
        n = n.lstrip('0') # Garante limpeza pós-DDI (ex: 55021...)

    # Agora 'n' deve conter apenas DDD + Telefone
    
    # Caso 1: 11 dígitos (DDD + 9 + 8 dígitos) -> Já está no padrão
    if len(n) == 11:
        if n[2] == '9':
            return f"+55{n}" 
            
    # Caso 2: 10 dígitos (DDD + 8 dígitos) -> Falta o 9 (Formato Antigo)
    elif len(n) == 10:
        # Injeta o 9 na posição correta
        return f"+55{n[:2]}9{n[2:]}"
        
    # Outros casos (8 ou 9 dígitos sem DDD) são arriscados demais para corrigir automaticamente
    return None

def buscar_numeros_telefone_cliente(driver, nome_cliente, wait_timeout=5):
    """
    Busca números na tela para fins de log e tentativa de envio secundário.
    A correção principal é feita via UI antes desta função ser crítica.
    """
    wait = WebDriverWait(driver, wait_timeout)
    numeros_encontrados = []
    
    # Helper
    def adicionar_se_valido(elem, tipo):
        try:
            txt = elem.text.strip()
            if txt:
                norm = normalizar_numero(txt)
                if norm:
                    valido, _ = validar_telefone_whatsapp(norm)
                    if valido:
                        numeros_encontrados.append({
                            'numero': norm, 
                            'campo': tipo, 
                            'original': txt
                        })
        except Exception: pass

    # 1. Tenta buscar links tel:
    try:
        links = driver.find_elements(By.XPATH, "//a[contains(@href, 'tel:')]")
        for link in links:
            adicionar_se_valido(link, 'link_tel')
    except Exception: pass
    
    # 2. Tenta buscar texto próximo a labels (fallback)
    if not numeros_encontrados:
        try:
            spans = driver.find_elements(By.XPATH, "//label[contains(., 'Celular') or contains(., 'Mobile')]/following::span[1]")
            for span in spans:
                adicionar_se_valido(span, 'texto_label')
        except Exception: pass

    # Deduplicação
    unicos = []
    vistos = set()
    for item in numeros_encontrados:
        if item['numero'] not in vistos:
            unicos.append(item)
            vistos.add(item['numero'])
            
    return unicos