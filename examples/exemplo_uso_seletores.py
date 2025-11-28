# Arquivo: examples/exemplo_uso_seletores.py
# -*- coding: utf-8 -*-
"""
EXEMPLO PRÁTICO: Como usar o SelectorManager no código real

Este arquivo demonstra como refatorar o código existente para usar
o sistema de seletores com fallback automático.
"""

from utils.selector_manager import get_selector_manager
import logging

# ============================================================================
# EXEMPLO 1: Refatorar a correção de telefones
# ============================================================================

def corrigir_telefones_com_seletores(driver, correcoes, nome_cliente):
    """
    Versão melhorada usando SelectorManager
    
    ANTES: Seletores hardcoded no código
    AGORA: Seletores carregados do JSON com fallback automático
    """
    sm = get_selector_manager()
    
    if not correcoes:
        return True
    
    try:
        # 1. Clicar no botão editar usando o seletor do JSON
        if not sm.click_element(driver, 'contato', 'edicao', 'botao_editar'):
            logging.error(f"[{nome_cliente}] Falha ao clicar em editar")
            return False
        
        # 2. Corrigir cada campo
        for correcao in correcoes:
            campo_tipo = correcao['campo_tipo']  # 'mobile' ou 'phone'
            numero = correcao['numero']
            
            # Localiza o campo usando o seletor do JSON
            campo = sm.find_element_safe(driver, 'contato', 'campos', 
                                         'celular' if campo_tipo == 'mobile' else 'telefone')
            
            if campo:
                # Envia o número corrigido
                sm.send_keys(driver, numero, 'contato', 'campos',
                           'celular' if campo_tipo == 'mobile' else 'telefone',
                           clear_first=True)
                logging.info(f"[{nome_cliente}] ✏️ {campo_tipo}: {numero}")
        
        # 3. Salvar usando o seletor do JSON
        if sm.click_element(driver, 'contato', 'edicao', 'botao_salvar'):
            logging.info(f"[{nome_cliente}] ✅ Salvou com sucesso!")
            return True
        
        return False
        
    except Exception as e:
        logging.error(f"[{nome_cliente}] ❌ Erro: {e}")
        return False


# ============================================================================
# EXEMPLO 2: Buscar informações do contato
# ============================================================================

def obter_informacoes_contato(driver, nome_cliente):
    """
    Extrai informações do painel de contato
    """
    sm = get_selector_manager()
    
    info = {
        'email': sm.get_text(driver, 'contato', 'campos', 'email', default='N/A'),
        'celular': sm.get_text(driver, 'contato', 'campos', 'celular', default='N/A'),
        'telefone': sm.get_text(driver, 'contato', 'campos', 'telefone', default='N/A'),
        'proprietario': sm.get_text(driver, 'contato', 'campos', 'proprietario', default='N/A')
    }
    
    logging.info(f"[{nome_cliente}] Informações: {info}")
    return info


# ============================================================================
# EXEMPLO 3: Enviar mensagem com template
# ============================================================================

def enviar_mensagem_template(driver, nome_cliente, template_nome):
    """
    Abre o modal de templates e seleciona um template
    """
    sm = get_selector_manager()
    
    # 1. Clicar no botão de templates
    if not sm.click_element(driver, 'mensagens', 'editor', 'botao_templates'):
        logging.error(f"[{nome_cliente}] Falha ao abrir templates")
        return False
    
    # 2. Aguardar modal abrir e selecionar template
    # (aqui você adicionaria a lógica específica de seleção)
    
    logging.info(f"[{nome_cliente}] Template '{template_nome}' selecionado")
    return True


# ============================================================================
# EXEMPLO 4: Navegação entre telas
# ============================================================================

def navegar_para_whatsapp(driver):
    """
    Navega para a tela de WhatsApp
    """
    sm = get_selector_manager()
    
    if sm.click_element(driver, 'navegacao', 'superior', 'whatsapp'):
        logging.info("✅ Navegou para WhatsApp")
        return True
    
    logging.error("❌ Falha ao navegar para WhatsApp")
    return False


def navegar_para_clientes(driver):
    """
    Navega para a tela de Clientes
    """
    sm = get_selector_manager()
    
    if sm.click_element(driver, 'navegacao', 'superior', 'clientes'):
        logging.info("✅ Navegou para Clientes")
        return True
    
    return False


# ============================================================================
# EXEMPLO 5: Verificar múltiplos campos
# ============================================================================

def verificar_campos_preenchidos(driver):
    """
    Verifica quais campos do contato estão preenchidos
    """
    sm = get_selector_manager()
    
    campos = ['email', 'celular', 'telefone']
    preenchidos = {}
    
    for campo in campos:
        texto = sm.get_text(driver, 'contato', 'campos', campo, default='')
        preenchidos[campo] = bool(texto and texto.lower() not in ['adicionar', 'n/a', ''])
    
    logging.info(f"Campos preenchidos: {preenchidos}")
    return preenchidos


# ============================================================================
# COMPARAÇÃO: ANTES vs DEPOIS
# ============================================================================

"""
ANTES (Hardcoded):
-----------------
SELETOR_BOTAO_EDITAR = 'button[data-id="iconContainer"]'
btn_editar = driver.find_element(By.CSS_SELECTOR, SELETOR_BOTAO_EDITAR)
btn_editar.click()

PROBLEMAS:
- Se o seletor mudar, precisa alterar o código
- Sem fallback automático
- Difícil de manter


DEPOIS (Com SelectorManager):
-----------------------------
sm = get_selector_manager()
sm.click_element(driver, 'contato', 'edicao', 'botao_editar')

VANTAGENS:
✅ Seletores centralizados no JSON
✅ Fallback automático (CSS → XPath)
✅ Fácil de manter
✅ Logs automáticos
✅ Reutilizável em todos os scripts
"""
