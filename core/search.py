# -*- coding: utf-8 -*-
import time
import re
import logging
from difflib import SequenceMatcher
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

# Configurações de Delay
DELAY_DIGITACAO_CURTA = 0.02
DELAY_DIGITACAO_MEDIA = 0.03
DELAY_DIGITACAO_LONGA = 0.04

SELETORES = {
    "icone_pesquisa": 'button[data-id="globalSearchIcon"]',
    "barra_pesquisa": 'input[data-id="searchInput"]',
    "msg_sem_resultados": 'div.zd_v2-commonemptystate-title',
    "botao_whatsapp": 'span[data-title="Enviar mensagens via WhatsApp (canal de IM)"]',
    "linha_resultado": 'div.zd_v2-listlayout-innerContainer',
    "tab_clientes": 'a[data-id="qtab_Contacts_Tab"]'
}

STOPWORDS_NOME = {"de","da","do","dos","e","ltda","me","epp","s/a","sa"}

def _sanear_termo(s):
    if not s: return ""
    return str(s).strip().lower()

def _tokens_nome(nome):
    return [t for t in re.split(r"\s+", str(nome).strip()) if len(t) >= 2]

def normalizar_nome(nome):
    if not nome: return ""
    # Simplificado para brevidade (pode usar unicodedata se preferir)
    return str(nome).lower().strip()

def _gerar_variacoes_inteligentes(dados_cliente):
    """Gera variações baseado no TIPO de dado prioritário."""
    tipo = dados_cliente.get('tipo_busca', 'auto')
    valor = str(dados_cliente.get('busca', '')).strip()
    variacoes = []

    if tipo == 'email':
        # Busca exata por e-mail
        logging.info(f"📧 Buscando por E-mail: {valor}")
        return [valor]

    elif tipo == 'telefone':
        # Busca por telefone (apenas números)
        nums = re.sub(r'\D', '', valor)
        logging.info(f"📞 Buscando por Telefone: {nums}")
        return [nums]

    elif tipo == 'doc':
        # Formata CPF/CNPJ
        nums = re.sub(r'\D', '', valor)
        if len(nums) == 11:
            fmt = f"{nums[:3]}.{nums[3:6]}.{nums[6:9]}-{nums[9:]}"
            return [fmt]
        elif len(nums) == 14:
            fmt = f"{nums[:2]}.{nums[2:5]}.{nums[5:8]}/{nums[8:12]}-{nums[12:]}"
            return [fmt]
        return [valor]

    # Lógica de Nome (ou Auto)
    nome_limpo = normalizar_nome(valor)
    toks = _tokens_nome(nome_limpo)
    
    if not toks: return [valor]

    if len(toks) >= 2:
        variacoes.append(f"{toks[0]} {toks[1]}") # Primeiro + Segundo
        variacoes.append(f"{toks[0]} {toks[-1]}") # Primeiro + Último
    
    variacoes.append(valor) # Nome completo
    variacoes.append(toks[0]) # Só o primeiro nome
    
    return list(dict.fromkeys(variacoes))[:6]

def _validar_resultado(elemento_linha, dados_cliente):
    """
    Validação Cruzada: Verifica se o resultado na tela bate com os DADOS DO EXCEL.
    """
    texto_linha = elemento_linha.text.lower()
    pontos = 0
    
    # 1. Valida E-mail (Se tiver no Excel)
    if dados_cliente.get('email_excel'):
        email_alvo = _sanear_termo(dados_cliente['email_excel'])
        if email_alvo in texto_linha:
            logging.info(f"   ✅ Confirmação: E-mail '{email_alvo}' encontrado.")
            pontos += 3

    # 2. Valida Telefone (Últimos 4 dígitos)
    if dados_cliente.get('telefone_excel'):
        tel_alvo = re.sub(r'\D', '', str(dados_cliente['telefone_excel']))
        if len(tel_alvo) >= 4 and tel_alvo[-4:] in texto_linha:
            logging.info(f"   ✅ Confirmação: Telefone final '...{tel_alvo[-4:]}' encontrado.")
            pontos += 3

    # 3. Valida Nome (Se a busca não foi por nome)
    if dados_cliente.get('nome_excel') and dados_cliente.get('tipo_busca') != 'nome':
        nome_alvo = _sanear_termo(dados_cliente['nome_excel']).split()[0] # Pega 1º nome
        if nome_alvo in texto_linha:
            logging.info(f"   ✅ Confirmação: Nome '{nome_alvo}' encontrado.")
            pontos += 2

    # Se não temos dados extras para validar, confiamos na busca (pontos=0)
    # Se temos dados, exigimos pelo menos 1 ponto de confirmação
    tem_dados_extras = any([dados_cliente.get('email_excel'), dados_cliente.get('telefone_excel')])
    
    if not tem_dados_extras:
        return True
    
    return pontos > 0

def buscar_e_abrir_cliente(driver, dados_cliente):
    wait = WebDriverWait(driver, 15)
    
    # 1. Garante Aba Clientes
    try:
        aba = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, SELETORES["tab_clientes"])))
        if "zd_v2-topmenu-menuItemActive" not in (aba.get_attribute("class") or ""):
            driver.execute_script("arguments[0].click();", aba)
            time.sleep(2)
    except: pass

    # 2. Abre Pesquisa
    try:
        btn_lupa = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, SELETORES["icone_pesquisa"])))
        btn_lupa.click()
        campo = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, SELETORES["barra_pesquisa"])))
    except:
        logging.error("Erro ao abrir barra de pesquisa.")
        return False

    variacoes = _gerar_variacoes_inteligentes(dados_cliente)
    
    for termo in variacoes:
        logging.info(f"🔎 Buscando por: '{termo}'")
        
        try:
            campo.click()
            campo.send_keys(Keys.CONTROL, "a")
            campo.send_keys(Keys.DELETE)
            time.sleep(0.2)
            
            # Digitação adaptativa
            delay = DELAY_DIGITACAO_LONGA if len(termo) > 10 else DELAY_DIGITACAO_MEDIA
            for letra in termo:
                campo.send_keys(letra)
                time.sleep(delay)
            
            time.sleep(0.5)
            campo.send_keys(Keys.ENTER)
            
            # Espera resultados
            try:
                WebDriverWait(driver, 8).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-title]")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, SELETORES["msg_sem_resultados"]))
                    )
                )
            except: continue # Timeout, tenta próximo

            # Analisa Resultados
            resultados = driver.find_elements(By.CSS_SELECTOR, SELETORES["linha_resultado"])
            
            for linha in resultados:
                if _validar_resultado(linha, dados_cliente):
                    try:
                        link = linha.find_element(By.CSS_SELECTOR, "a[data-title]")
                        driver.execute_script("arguments[0].click();", link)
                        
                        WebDriverWait(driver, 15).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, SELETORES["botao_whatsapp"]))
                        )
                        return True
                    except: pass
                    
        except Exception as e:
            logging.error(f"Erro na tentativa de busca: {e}")
            try: campo = driver.find_element(By.CSS_SELECTOR, SELETORES["barra_pesquisa"])
            except: pass

    return False