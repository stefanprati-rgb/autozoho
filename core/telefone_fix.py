# -*- coding: utf-8 -*-
"""
Módulo de correção automática de telefone.
Detecta e corrige casos onde o cliente não tem celular mas tem telefone válido.
"""

import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from utils.telefone import normalizar_numero, validar_telefone_whatsapp

# Seletores para correção de telefone
SELETORES_TELEFONE_FIX = {
    # Erro de telefone inválido
    "erro_telefone_invalido": "//div[contains(@class, 'zd_v2-globalnotification-text') and contains(., 'número de telefone/celular do contato é inválido')]",
    
    Detecta se o erro de telefone inválido está sendo exibido.
    Retorna True se o erro foi detectado.
    """
    try:
        erro = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, SELETORES_TELEFONE_FIX["erro_telefone_invalido"]))
        )
        if erro.is_displayed():
            logging.warning("⚠️ Erro de telefone inválido detectado!")
            return True
    except (TimeoutException, NoSuchElementException):
        pass
    return False


def fechar_erro_telefone_invalido(driver):
    """
    Fecha o alerta de erro de telefone inválido.
    """
    try:
        btn_fechar = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.XPATH, SELETORES_TELEFONE_FIX["botao_fechar_erro"]))
        )
        driver.execute_script("arguments[0].click();", btn_fechar)
        time.sleep(0.5)
        logging.info("Alerta de erro fechado.")
        return True
    except Exception as e:
        logging.debug(f"Não foi possível fechar o erro: {e}")
        return False


def fechar_modal_whatsapp(driver):
    """
    Fecha o modal do WhatsApp clicando em Cancelar.
    """
    try:
        btn_cancelar = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.XPATH, SELETORES_TELEFONE_FIX["botao_cancelar_modal_wpp"]))
        )
        driver.execute_script("arguments[0].click();", btn_cancelar)
        time.sleep(0.5)
        logging.info("Modal WhatsApp fechado.")
        return True
    except Exception as e:
        logging.debug(f"Não foi possível fechar o modal WhatsApp: {e}")
        return False


def verificar_celular_vazio(driver, timeout=2):
    """
    Verifica se o campo celular está vazio (mostrando "Adicionar Celular").
    Retorna True se estiver vazio.
    """
    try:
        celular_vazio = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, SELETORES_TELEFONE_FIX["celular_vazio"]))
        )
        if celular_vazio.is_displayed():
            logging.info("Campo celular está vazio.")
            return True
    except (TimeoutException, NoSuchElementException):
        logging.debug("Campo celular parece estar preenchido.")
    return False


def extrair_numero_telefone(driver, timeout=3):
    """
    Extrai o número do campo telefone (link tel:).
    Retorna o número extraído ou None se não encontrado.
    """
    try:
        links_telefone = driver.find_elements(By.XPATH, SELETORES_TELEFONE_FIX["link_telefone"])
        
        for link in links_telefone:
            if link.is_displayed():
                numero = link.text.strip()
                if numero:
                    logging.info(f"Número encontrado no campo telefone: {numero}")
                    return numero
        
        logging.warning("Nenhum número de telefone encontrado na página.")
        return None
    except Exception as e:
        logging.error(f"Erro ao extrair número de telefone: {e}")
        return None


def abrir_modal_edicao_cliente(driver, timeout=5):
    """
    Abre o modal de edição do cliente clicando no ícone de editar.
    Retorna True se conseguiu abrir.
    """
    try:
        # Procura pelo botão de editar (ícone de lápis)
        botao_editar = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, SELETORES_TELEFONE_FIX["botao_editar"]))
        )
        
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", botao_editar)
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", botao_editar)
        
        # Aguarda o modal abrir (verifica se o campo celular do modal apareceu)
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, SELETORES_TELEFONE_FIX["input_celular_modal"]))
        )
        
        logging.info("✅ Modal de edição do cliente aberto.")
        time.sleep(1)
        return True
    except Exception as e:
        logging.error(f"❌ Erro ao abrir modal de edição: {e}")
        return False


def preencher_campo_celular(driver, numero_normalizado, timeout=5):
    """
    Preenche o campo celular no modal de edição com o número normalizado.
    Retorna True se conseguiu preencher.
    """
    try:
        input_celular = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, SELETORES_TELEFONE_FIX["input_celular_modal"]))
        )
        
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", input_celular)
        time.sleep(0.3)
        
        # Limpa o campo
        input_celular.clear()
        time.sleep(0.2)
        
        # Preenche com o número normalizado
        input_celular.send_keys(numero_normalizado)
        time.sleep(0.5)
        
        logging.info(f"✅ Campo celular preenchido com: {numero_normalizado}")
        return True
    except Exception as e:
        logging.error(f"❌ Erro ao preencher campo celular: {e}")
        return False


def salvar_edicao_cliente(driver, timeout=5):
    """
    Salva as alterações no modal de edição do cliente.
    Retorna True se conseguiu salvar.
    """
    try:
        botao_salvar = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, SELETORES_TELEFONE_FIX["botao_salvar_modal"]))
        )
        
        driver.execute_script("arguments[0].click();", botao_salvar)
        
        # Aguarda o modal fechar (o campo do modal deve desaparecer)
        WebDriverWait(driver, timeout).until(
            EC.invisibility_of_element_located((By.XPATH, SELETORES_TELEFONE_FIX["input_celular_modal"]))
        )
        
        logging.info("✅ Alterações salvas com sucesso.")
        time.sleep(2)  # Aguarda a página atualizar
        return True
    except Exception as e:
        logging.error(f"❌ Erro ao salvar alterações: {e}")
        return False


def corrigir_telefone_cliente(driver, nome_cliente):
    """
    Função principal que orquestra todo o processo de correção de telefone.
    
    Fluxo:
    1. Detecta erro de telefone inválido
    2. Fecha o alerta de erro
    3. Fecha o modal do WhatsApp
    4. Verifica se o celular está vazio
    5. Extrai número do campo telefone
    6. Normaliza o número
    7. Abre modal de edição
    8. Preenche campo celular
    9. Salva alterações
    
    Retorna True se conseguiu corrigir, False caso contrário.
    """
    logging.info(f"[{nome_cliente}] 🔧 Iniciando correção automática de telefone...")
    
    # 1. Detecta erro
    if not detectar_erro_telefone_invalido(driver):
        logging.debug("Erro de telefone inválido não detectado. Nada a corrigir.")
        return False
    
    # 2. Fecha o alerta de erro
    fechar_erro_telefone_invalido(driver)
    
    # 3. Fecha o modal do WhatsApp
    fechar_modal_whatsapp(driver)
    time.sleep(0.5)
    
    # 4. Verifica se celular está vazio
    if not verificar_celular_vazio(driver):
        logging.warning(f"[{nome_cliente}] Campo celular não está vazio. Pode estar com número inválido.")
        # Ainda assim, vamos tentar corrigir usando o telefone
    
    # 5. Extrai número do telefone
    numero_original = extrair_numero_telefone(driver)
    if not numero_original:
        logging.error(f"[{nome_cliente}] ❌ Não foi possível extrair número do campo telefone.")
        return False
    
    # 6. Normaliza o número
    numero_normalizado = normalizar_numero(numero_original)
    if not numero_normalizado:
        logging.error(f"[{nome_cliente}] ❌ Não foi possível normalizar o número: {numero_original}")
        return False
    
    # Valida o número normalizado
    valido, motivo = validar_telefone_whatsapp(numero_normalizado)
    if not valido:
        logging.error(f"[{nome_cliente}] ❌ Número normalizado inválido: {numero_normalizado} - {motivo}")
        return False
    
    logging.info(f"[{nome_cliente}] ✅ Número normalizado: {numero_normalizado}")
    
    # 7. Abre modal de edição
    if not abrir_modal_edicao_cliente(driver):
        return False
    
    # 8. Preenche campo celular
    if not preencher_campo_celular(driver, numero_normalizado):
        return False
    
    # 9. Salva alterações
    if not salvar_edicao_cliente(driver):
        return False
    
    logging.info(f"[{nome_cliente}] ✅ Telefone corrigido com sucesso! Novo celular: {numero_normalizado}")
    return True
