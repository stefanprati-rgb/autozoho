# Arquivo: examples/exemplo_modal_whatsapp.py
# -*- coding: utf-8 -*-
"""
EXEMPLO: Usando seletores do Modal de Envio WhatsApp

Demonstra como usar o SelectorManager para interagir com o modal
de envio de mensagens WhatsApp.
"""

from utils.selector_manager import SelectorManager
import logging
import time
from selenium.webdriver.common.keys import Keys

# Carregar seletores do modal WhatsApp
sm = SelectorManager('config/modal_whatsapp_selectors.json')


# ============================================================================
# EXEMPLO 1: Verificar se o modal está aberto
# ============================================================================

def modal_esta_aberto(driver):
    """
    Verifica se o modal de WhatsApp está aberto
    
    Returns:
        bool: True se o modal está visível
    """
    modal = sm.find_element_safe(driver, 'modal', 'container', 'dialog', 
                                  wait_time=2, required=False)
    
    if modal:
        logging.info("✅ Modal WhatsApp está aberto")
        return True
    
    logging.info("❌ Modal WhatsApp não está aberto")
    return False


# ============================================================================
# EXEMPLO 2: Aguardar modal abrir
# ============================================================================

def aguardar_modal_abrir(driver, timeout=10):
    """
    Aguarda o modal de WhatsApp abrir
    
    Returns:
        bool: True se o modal abriu no tempo esperado
    """
    modal = sm.find_element_safe(driver, 'modal', 'container', 'dialog', 
                                  wait_time=timeout, required=False)
    
    if modal:
        logging.info("✅ Modal abriu com sucesso")
        time.sleep(0.5)  # Pequena pausa para estabilizar
        return True
    
    logging.error("❌ Modal não abriu no tempo esperado")
    return False


# ============================================================================
# EXEMPLO 3: Selecionar departamento
# ============================================================================

def selecionar_departamento(driver, departamento_nome):
    """
    Seleciona um departamento no dropdown
    
    Args:
        departamento_nome: Nome do departamento (ex: 'Era Verde Energia')
    """
    # Clicar no dropdown de departamento
    if sm.click_element(driver, 'modal', 'body', 'departamento', 'dropdown'):
        time.sleep(0.5)
        
        # Selecionar a opção específica
        xpath = f"//menuitem[contains(text(), '{departamento_nome}')]"
        try:
            from selenium.webdriver.common.by import By
            opcao = driver.find_element(By.XPATH, xpath)
            opcao.click()
            logging.info(f"✅ Departamento '{departamento_nome}' selecionado")
            return True
        except Exception as e:
            logging.error(f"❌ Erro ao selecionar departamento: {e}")
            return False
    
    return False


# ============================================================================
# EXEMPLO 4: Selecionar canal WhatsApp (com busca)
# ============================================================================

def selecionar_canal_whatsapp(driver, canal_nome_parcial):
    """
    Seleciona um canal WhatsApp digitando no campo de busca
    
    Args:
        canal_nome_parcial: Parte do nome do canal para buscar
    
    Returns:
        bool: True se selecionou com sucesso
    """
    # Clicar no campo de canal
    campo_canal = sm.find_element_safe(driver, 'modal', 'body', 'canal_whatsapp', 'input')
    
    if not campo_canal:
        # Tentar fallback genérico
        campo_canal = sm.find_element_safe(driver, 'modal', 'body', 'canal_whatsapp', 'input_generico')
    
    if campo_canal:
        # Limpar e digitar
        campo_canal.click()
        time.sleep(0.3)
        campo_canal.send_keys(Keys.CONTROL, "a")
        campo_canal.send_keys(Keys.DELETE)
        time.sleep(0.3)
        campo_canal.send_keys(canal_nome_parcial)
        time.sleep(1)  # Aguardar resultados da busca
        
        # Selecionar primeira opção que aparecer
        try:
            from selenium.webdriver.common.by import By
            opcao = driver.find_element(By.XPATH, "//menuitem[contains(@role, 'option')]")
            opcao.click()
            logging.info(f"✅ Canal '{canal_nome_parcial}' selecionado")
            return True
        except Exception as e:
            logging.error(f"❌ Erro ao selecionar canal: {e}")
            return False
    
    return False


# ============================================================================
# EXEMPLO 5: Selecionar template de mensagem
# ============================================================================

def selecionar_template(driver, template_nome):
    """
    Seleciona um template de mensagem
    
    Args:
        template_nome: Nome do template (ex: 'Cobrança .')
    """
    # Clicar no campo de template
    campo_template = sm.find_element_safe(driver, 'modal', 'body', 'modelo_mensagem', 'dropdown')
    
    if not campo_template:
        # Tentar fallback
        campo_template = sm.find_element_safe(driver, 'modal', 'body', 'modelo_mensagem', 'dropdown_generico')
    
    if campo_template:
        campo_template.click()
        time.sleep(0.5)
        
        # Buscar e selecionar o template
        try:
            from selenium.webdriver.common.by import By
            xpath = f"//menuitem[contains(text(), '{template_nome}')]"
            opcao = driver.find_element(By.XPATH, xpath)
            opcao.click()
            logging.info(f"✅ Template '{template_nome}' selecionado")
            return True
        except Exception as e:
            logging.error(f"❌ Erro ao selecionar template: {e}")
            return False
    
    return False


# ============================================================================
# EXEMPLO 6: Verificar se botão enviar está habilitado
# ============================================================================

def botao_enviar_habilitado(driver):
    """
    Verifica se o botão Enviar está habilitado
    """
    botao = sm.find_element_safe(driver, 'estados', 'botao_enviar_habilitado',
                                  wait_time=2, required=False)
    
    if botao:
        logging.info("✅ Botão Enviar está habilitado")
        return True
    
    logging.warning("⚠️ Botão Enviar ainda está desabilitado")
    return False


# ============================================================================
# EXEMPLO 7: Clicar em Enviar
# ============================================================================

def clicar_enviar(driver):
    """
    Clica no botão Enviar
    """
    if sm.click_element(driver, 'modal', 'footer', 'botao_enviar'):
        logging.info("✅ Clicou em Enviar")
        return True
    
    logging.error("❌ Falha ao clicar em Enviar")
    return False


# ============================================================================
# EXEMPLO 8: Cancelar e fechar modal
# ============================================================================

def cancelar_modal(driver):
    """
    Clica no botão Cancelar para fechar o modal
    """
    if sm.click_element(driver, 'modal', 'footer', 'botao_cancelar'):
        logging.info("✅ Modal cancelado")
        return True
    
    logging.error("❌ Falha ao cancelar modal")
    return False


# ============================================================================
# EXEMPLO 9: Obter número do celular exibido
# ============================================================================

def obter_numero_celular_modal(driver):
    """
    Obtém o número de celular exibido no modal
    """
    numero = sm.get_text(driver, 'modal', 'header', 'numero_celular', default='N/A')
    logging.info(f"📱 Número no modal: {numero}")
    return numero


# ============================================================================
# EXEMPLO 10: Workflow completo - Enviar mensagem
# ============================================================================

def enviar_mensagem_whatsapp_completo(driver, departamento, canal, template, dry_run=False):
    """
    Workflow completo para enviar uma mensagem WhatsApp
    
    Args:
        departamento: Nome do departamento
        canal: Substring do nome do canal
        template: Nome do template
        dry_run: Se True, não clica em Enviar
    
    Returns:
        bool: True se enviou com sucesso
    """
    logging.info("🚀 Iniciando envio de mensagem WhatsApp")
    
    # 1. Aguardar modal abrir
    if not aguardar_modal_abrir(driver):
        return False
    
    # 2. Verificar número do celular
    numero = obter_numero_celular_modal(driver)
    logging.info(f"📱 Enviando para: {numero}")
    
    # 3. Selecionar departamento (se necessário)
    # Nota: Às vezes o departamento já vem selecionado
    # selecionar_departamento(driver, departamento)
    
    # 4. Selecionar canal
    if not selecionar_canal_whatsapp(driver, canal):
        logging.error("❌ Falha ao selecionar canal")
        return False
    
    time.sleep(1)
    
    # 5. Selecionar template
    if not selecionar_template(driver, template):
        logging.error("❌ Falha ao selecionar template")
        return False
    
    time.sleep(1)
    
    # 6. Verificar se botão está habilitado
    if not botao_enviar_habilitado(driver):
        logging.error("❌ Botão Enviar não está habilitado")
        return False
    
    # 7. Enviar (ou simular)
    if dry_run:
        logging.info("[DRY-RUN] Simularia clique em Enviar")
        cancelar_modal(driver)
        return True
    else:
        if clicar_enviar(driver):
            logging.info("✅ Mensagem enviada com sucesso!")
            return True
        else:
            logging.error("❌ Falha ao enviar mensagem")
            return False


# ============================================================================
# EXEMPLO 11: Integração com código existente
# ============================================================================

def integrar_com_messaging_py(driver, nome_cliente, departamento, template_nome, ancoras, dry_run=False):
    """
    Exemplo de como integrar com o código existente em core/messaging.py
    
    Esta função pode substituir partes do código atual para usar os seletores do JSON
    """
    logging.info(f"[{nome_cliente}] Abrindo modal WhatsApp...")
    
    # Aguardar modal abrir
    if not aguardar_modal_abrir(driver, timeout=10):
        logging.error(f"[{nome_cliente}] Modal não abriu")
        return False
    
    # Selecionar canal usando substring do departamento
    # Ex: departamento='Era Verde' → busca canal que contenha 'Era Verde'
    if not selecionar_canal_whatsapp(driver, departamento):
        logging.error(f"[{nome_cliente}] Falha ao selecionar canal")
        return False
    
    # Selecionar template
    # Aqui você pode usar a lógica de ancoras se necessário
    if not selecionar_template(driver, template_nome):
        logging.error(f"[{nome_cliente}] Falha ao selecionar template")
        return False
    
    # Verificar e enviar
    if botao_enviar_habilitado(driver):
        if not dry_run:
            return clicar_enviar(driver)
        else:
            logging.info(f"[{nome_cliente}] [DRY-RUN] Simularia envio")
            cancelar_modal(driver)
            return True
    
    return False


# ============================================================================
# COMPARAÇÃO: ANTES vs DEPOIS
# ============================================================================

"""
ANTES (Hardcoded em messaging.py):
-----------------------------------
# Selecionar canal
campo_canal = driver.find_element(By.XPATH, "//input[@type='text']")
campo_canal.send_keys(departamento)
time.sleep(1)
opcao = driver.find_element(By.XPATH, "//menuitem[1]")
opcao.click()

# Selecionar template
campo_template = driver.find_element(By.XPATH, "//input[@placeholder='Choose templates']")
campo_template.click()
template = driver.find_element(By.XPATH, f"//menuitem[contains(text(), '{template_nome}')]")
template.click()

# Enviar
botao = driver.find_element(By.XPATH, "//button[contains(text(), 'Enviar')]")
botao.click()


DEPOIS (Com SelectorManager):
-----------------------------
sm = SelectorManager('config/modal_whatsapp_selectors.json')

# Tudo em uma função!
enviar_mensagem_whatsapp_completo(driver, departamento, canal, template)

# Ou passo a passo com fallback automático:
selecionar_canal_whatsapp(driver, canal)
selecionar_template(driver, template)
clicar_enviar(driver)

VANTAGENS:
✅ Código mais limpo e legível
✅ Fallback automático entre seletores
✅ Logs detalhados automáticos
✅ Fácil manutenção
✅ Reutilizável
"""
