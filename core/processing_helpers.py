# Arquivo: core/processing_helpers.py
# -*- coding: utf-8 -*-
"""
Helpers melhorados para processamento de contatos usando SelectorManager

Este módulo fornece funções de alto nível que usam o sistema de seletores
mapeados, oferecendo fallback automático e melhor manutenibilidade.
"""

import time
import logging
from utils.selector_manager import SelectorManager
from utils.telefone import normalizar_numero, validar_telefone_whatsapp
from utils.screenshots import take_screenshot

# Carregar seletores das telas mapeadas
sm_detalhes = SelectorManager('config/contato_detalhes_selectors.json')
sm_modal = SelectorManager('config/modal_whatsapp_selectors.json')
sm_formulario = SelectorManager('config/editar_contato_selectors.json')


# ============================================================================
# CORREÇÃO DE TELEFONES - Versão Melhorada
# ============================================================================

def corrigir_telefones_modal_inline(driver, correcoes, nome_cliente):
    """
    Corrige telefones usando o modal inline (botão editar na página de detalhes)
    
    VANTAGEM: Mais rápido, não precisa navegar para outra página
    
    Args:
        driver: WebDriver
        correcoes: Lista de dicts com {'campo_tipo': 'mobile'/'phone', 'numero': '+55...', 'label': '...'}
        nome_cliente: Nome do cliente
    
    Returns:
        bool: True se corrigiu com sucesso
    """
    if not correcoes:
        return True
    
    try:
        campos_str = ", ".join([c['label'] for c in correcoes])
        logging.info(f"[{nome_cliente}] 🛠️ Corrigindo {len(correcoes)} campo(s): {campos_str}")
        
        # 1. Clicar no botão editar
        if not sm_detalhes.click_element(driver, 'edicao', 'botao_editar'):
            logging.error(f"[{nome_cliente}] ❌ Falha ao abrir edição")
            return False
        
        time.sleep(1.5)
        
        # 2. Preencher todos os campos
        for correcao in correcoes:
            campo_tipo = correcao['campo_tipo']
            numero = correcao['numero']
            label = correcao['label']
            
            # Usar SelectorManager para localizar e preencher
            campo_nome = 'celular' if campo_tipo == 'mobile' else 'telefone'
            
            if sm_detalhes.send_keys(driver, numero, 'edicao', 'campos_input', campo_nome, clear_first=True):
                logging.info(f"[{nome_cliente}] ✏️ {label}: {numero}")
            else:
                logging.warning(f"[{nome_cliente}] ⚠️ Falha ao preencher {label}")
        
        time.sleep(0.5)
        
        # 3. Salvar
        if sm_detalhes.click_element(driver, 'edicao', 'botao_salvar'):
            logging.info(f"[{nome_cliente}] ✅ Correções salvas!")
            time.sleep(2)
            return True
        
        logging.error(f"[{nome_cliente}] ❌ Falha ao salvar")
        return False
        
    except Exception as e:
        logging.error(f"[{nome_cliente}] ❌ Erro na correção: {e}")
        take_screenshot(driver, f"erro_correcao_{nome_cliente}")
        return False


def corrigir_telefones_formulario_completo(driver, contato_id, correcoes, nome_cliente):
    """
    Corrige telefones usando o formulário completo de edição
    
    VANTAGEM: Mais robusto, permite editar outros campos também
    
    Args:
        driver: WebDriver
        contato_id: ID do contato
        correcoes: Lista de dicts com correções
        nome_cliente: Nome do cliente
    
    Returns:
        bool: True se corrigiu com sucesso
    """
    try:
        # 1. Navegar para formulário de edição
        url = f"https://desk.zoho.com/agent/hubedesk/era-verde-energia/contato/edit/{contato_id}"
        driver.get(url)
        time.sleep(2)
        
        # 2. Preencher campos
        for correcao in correcoes:
            campo_tipo = correcao['campo_tipo']
            numero = correcao['numero']
            
            campo_nome = 'celular' if campo_tipo == 'mobile' else 'telefone'
            
            if sm_formulario.send_keys(driver, numero, 'formulario', 'campos', campo_nome, 'input', clear_first=True):
                logging.info(f"[{nome_cliente}] ✏️ {campo_nome}: {numero}")
        
        time.sleep(0.5)
        
        # 3. Salvar
        if sm_formulario.click_element(driver, 'formulario', 'acoes', 'botao_salvar'):
            logging.info(f"[{nome_cliente}] ✅ Formulário salvo!")
            time.sleep(2)
            return True
        
        return False
        
    except Exception as e:
        logging.error(f"[{nome_cliente}] ❌ Erro no formulário: {e}")
        return False


# ============================================================================
# VERIFICAÇÃO E VALIDAÇÃO
# ============================================================================

def verificar_e_preparar_correcoes(driver, nome_cliente):
    """
    Verifica telefones na página de detalhes e prepara lista de correções
    
    Returns:
        list: Lista de correções necessárias (vazia se nada precisa corrigir)
    """
    correcoes = []
    
    campos_verificar = [
        ('mobile', 'Celular', "//label[contains(., 'Celular')]/following::a[1] | //label[contains(., 'Celular')]/following::span[1]"),
        ('phone', 'Telefone', "//label[contains(., 'Telefone')]/following::a[1] | //label[contains(., 'Telefone')]/following::span[1]")
    ]
    
    from selenium.webdriver.common.by import By
    
    for campo_tipo, label, xpath in campos_verificar:
        try:
            elem = driver.find_element(By.XPATH, xpath)
            texto_tel = elem.text.strip()
            
            if texto_tel and texto_tel.lower() not in ['adicionar celular', 'adicionar telefone', '']:
                valido, msg = validar_telefone_whatsapp(texto_tel)
                
                if not valido:
                    logging.warning(f"[{nome_cliente}] {label} '{texto_tel}' inválido ({msg})")
                    
                    novo_numero = normalizar_numero(texto_tel)
                    
                    if novo_numero:
                        novo_valido, _ = validar_telefone_whatsapp(novo_numero)
                        if novo_valido:
                            logging.info(f"[{nome_cliente}] {label}: '{texto_tel}' → '{novo_numero}'")
                            correcoes.append({
                                'campo_tipo': campo_tipo,
                                'numero': novo_numero,
                                'label': label
                            })
                else:
                    logging.info(f"[{nome_cliente}] {label} '{texto_tel}' OK")
        except:
            continue
    
    return correcoes


# ============================================================================
# WORKFLOW COMPLETO - Versão Melhorada
# ============================================================================

def processar_contato_completo(driver, contato_id, nome_cliente, usar_formulario=False):
    """
    Workflow completo: verifica, corrige telefones se necessário
    
    Args:
        driver: WebDriver
        contato_id: ID do contato
        nome_cliente: Nome do cliente
        usar_formulario: Se True, usa formulário completo. Se False, usa modal inline
    
    Returns:
        bool: True se processou com sucesso
    """
    logging.info(f"[{nome_cliente}] 🚀 Processando contato {contato_id}")
    
    # 1. Navegar para detalhes (se não estiver lá)
    url_atual = driver.current_url
    if contato_id not in url_atual:
        url = f"https://desk.zoho.com/agent/hubedesk/era-verde-energia/contato/details/{contato_id}"
        driver.get(url)
        time.sleep(2)
    
    # 2. Verificar e preparar correções
    correcoes = verificar_e_preparar_correcoes(driver, nome_cliente)
    
    if not correcoes:
        logging.info(f"[{nome_cliente}] ✅ Nenhuma correção necessária")
        return True
    
    # 3. Aplicar correções
    if usar_formulario:
        return corrigir_telefones_formulario_completo(driver, contato_id, correcoes, nome_cliente)
    else:
        return corrigir_telefones_modal_inline(driver, correcoes, nome_cliente)


# ============================================================================
# INTEGRAÇÃO COM CÓDIGO EXISTENTE
# ============================================================================

def corrigir_telefones_na_interface_v2(driver, correcoes, nome_cliente):
    """
    Versão melhorada da função original usando SelectorManager
    
    COMPATÍVEL com a assinatura da função original em processing.py
    Pode ser usada como drop-in replacement
    """
    return corrigir_telefones_modal_inline(driver, correcoes, nome_cliente)


# ============================================================================
# COMPARAÇÃO DE PERFORMANCE
# ============================================================================

def comparar_metodos(driver, contato_id, nome_cliente):
    """
    Compara performance entre modal inline e formulário completo
    
    Útil para decidir qual método usar
    """
    import time as time_module
    
    # Preparar correções
    correcoes = verificar_e_preparar_correcoes(driver, nome_cliente)
    
    if not correcoes:
        logging.info("Nenhuma correção necessária para comparação")
        return
    
    # Método 1: Modal inline
    inicio = time_module.time()
    sucesso1 = corrigir_telefones_modal_inline(driver, correcoes, nome_cliente)
    tempo1 = time_module.time() - inicio
    
    # Método 2: Formulário completo
    inicio = time_module.time()
    sucesso2 = corrigir_telefones_formulario_completo(driver, contato_id, correcoes, nome_cliente)
    tempo2 = time_module.time() - inicio
    
    logging.info(f"📊 Comparação:")
    logging.info(f"   Modal inline: {tempo1:.2f}s - {'✅' if sucesso1 else '❌'}")
    logging.info(f"   Formulário: {tempo2:.2f}s - {'✅' if sucesso2 else '❌'}")
