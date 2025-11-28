# Arquivo: examples/exemplo_contato_detalhes.py
# -*- coding: utf-8 -*-
"""
EXEMPLO: Usando seletores da tela de Detalhes de Contato

Demonstra como usar o SelectorManager para interagir com a página
de detalhes de um contato específico.
"""

from utils.selector_manager import SelectorManager
import logging

# Carregar seletores da tela de detalhes de contato
sm = SelectorManager('config/contato_detalhes_selectors.json')


# ============================================================================
# EXEMPLO 1: Navegar para a tela de detalhes
# ============================================================================

def abrir_detalhes_contato(driver, contato_id):
    """
    Navega para a página de detalhes de um contato
    
    Args:
        driver: WebDriver
        contato_id: ID do contato no Zoho
    """
    url = f"https://desk.zoho.com/agent/hubedesk/era-verde-energia/contato/details/{contato_id}"
    driver.get(url)
    logging.info(f"✅ Navegou para detalhes do contato {contato_id}")


# ============================================================================
# EXEMPLO 2: Extrair todas as informações do contato
# ============================================================================

def extrair_informacoes_completas(driver):
    """
    Extrai todas as informações visíveis do contato
    
    Returns:
        dict: Dicionário com todas as informações
    """
    info = {
        # Informações básicas
        'nome': sm.get_text(driver, 'painel_central', 'cabecalho', 'nome_contato'),
        
        # Contatos
        'email': sm.get_text(driver, 'painel_central', 'propriedades', 'campos', 'email'),
        'celular': sm.get_text(driver, 'painel_central', 'propriedades', 'campos', 'celular'),
        'telefone': sm.get_text(driver, 'painel_central', 'propriedades', 'campos', 'telefone'),
        
        # Redes sociais
        'facebook': sm.get_text(driver, 'painel_central', 'propriedades', 'campos', 'facebook'),
        'twitter': sm.get_text(driver, 'painel_central', 'propriedades', 'campos', 'twitter'),
        
        # Outros
        'idioma': sm.get_text(driver, 'painel_central', 'propriedades', 'campos', 'idioma'),
    }
    
    logging.info(f"📋 Informações extraídas: {info}")
    return info


# ============================================================================
# EXEMPLO 3: Verificar campos vazios
# ============================================================================

def verificar_campos_vazios(driver):
    """
    Verifica quais campos ainda não foram preenchidos
    
    Returns:
        list: Lista de campos vazios
    """
    campos_vazios = []
    
    campos_verificar = {
        'telefone': 'Adicionar Telefone',
        'idioma': 'Adicionar Idioma',
        'facebook': 'Adicionar Facebook',
        'twitter': 'Adicionar Twitter'
    }
    
    for campo, placeholder in campos_verificar.items():
        texto = sm.get_text(driver, 'painel_central', 'propriedades', 'campos', campo)
        if placeholder in texto:
            campos_vazios.append(campo)
    
    if campos_vazios:
        logging.warning(f"⚠️ Campos vazios: {', '.join(campos_vazios)}")
    else:
        logging.info("✅ Todos os campos estão preenchidos!")
    
    return campos_vazios


# ============================================================================
# EXEMPLO 4: Editar múltiplos campos
# ============================================================================

def editar_contato(driver, dados):
    """
    Edita informações do contato
    
    Args:
        dados: dict com {'celular': '+5511...', 'telefone': '+5511...', etc}
    
    Returns:
        bool: True se editou com sucesso
    """
    # 1. Clicar no botão editar
    if not sm.click_element(driver, 'edicao', 'botao_editar'):
        logging.error("❌ Falha ao abrir modo de edição")
        return False
    
    # 2. Preencher os campos
    for campo, valor in dados.items():
        if campo in ['celular', 'telefone', 'email']:
            if sm.send_keys(driver, valor, 'edicao', 'campos_input', campo, clear_first=True):
                logging.info(f"✏️ {campo}: {valor}")
            else:
                logging.warning(f"⚠️ Falha ao preencher {campo}")
    
    # 3. Salvar
    if sm.click_element(driver, 'edicao', 'botao_salvar'):
        logging.info("✅ Contato atualizado com sucesso!")
        return True
    
    logging.error("❌ Falha ao salvar")
    return False


# ============================================================================
# EXEMPLO 5: Adicionar ticket para o contato
# ============================================================================

def adicionar_ticket(driver):
    """
    Clica no botão para adicionar um novo ticket
    """
    if sm.click_element(driver, 'painel_central', 'botoes_acao', 'adicionar_ticket'):
        logging.info("✅ Modal de novo ticket aberto")
        return True
    
    logging.error("❌ Falha ao abrir modal de ticket")
    return False


# ============================================================================
# EXEMPLO 6: Navegar entre abas
# ============================================================================

def navegar_para_aba(driver, aba):
    """
    Navega para uma aba específica
    
    Args:
        aba: 'visao_geral', 'historico', 'atividades', 'ticket_interaction', 'email'
    """
    if sm.click_element(driver, 'painel_central', 'abas_conteudo', aba):
        logging.info(f"✅ Navegou para aba: {aba}")
        return True
    
    logging.error(f"❌ Falha ao navegar para aba: {aba}")
    return False


# ============================================================================
# EXEMPLO 7: Voltar para lista de contatos
# ============================================================================

def voltar_lista_contatos(driver):
    """
    Volta para a lista de contatos
    """
    # Opção 1: Usar botão voltar
    if sm.click_element(driver, 'painel_esquerdo', 'navegacao', 'botao_voltar'):
        logging.info("✅ Voltou para lista (botão voltar)")
        return True
    
    # Opção 2: Usar link de navegação
    if sm.click_element(driver, 'navegacao', 'superior', 'clientes'):
        logging.info("✅ Voltou para lista (link clientes)")
        return True
    
    logging.error("❌ Falha ao voltar para lista")
    return False


# ============================================================================
# EXEMPLO 8: Workflow completo - Corrigir telefones
# ============================================================================

def workflow_corrigir_telefones(driver, contato_id, celular_novo, telefone_novo):
    """
    Workflow completo: abre contato, corrige telefones, salva
    
    Args:
        contato_id: ID do contato
        celular_novo: Novo número de celular com +55
        telefone_novo: Novo número de telefone com +55
    """
    logging.info(f"🚀 Iniciando correção de telefones para contato {contato_id}")
    
    # 1. Abrir página de detalhes
    abrir_detalhes_contato(driver, contato_id)
    
    # 2. Verificar informações atuais
    info_atual = extrair_informacoes_completas(driver)
    logging.info(f"📋 Celular atual: {info_atual.get('celular', 'N/A')}")
    logging.info(f"📋 Telefone atual: {info_atual.get('telefone', 'N/A')}")
    
    # 3. Editar com novos valores
    dados_novos = {
        'celular': celular_novo,
        'telefone': telefone_novo
    }
    
    if editar_contato(driver, dados_novos):
        logging.info("✅ Workflow concluído com sucesso!")
        return True
    
    logging.error("❌ Workflow falhou")
    return False


# ============================================================================
# EXEMPLO 9: Comparação com código antigo
# ============================================================================

"""
ANTES (Hardcoded):
------------------
# Abrir edição
btn_editar = driver.find_element(By.CSS_SELECTOR, 'button[data-id="iconContainer"]')
btn_editar.click()

# Preencher celular
input_celular = driver.find_element(By.CSS_SELECTOR, 'input[data-id="mobile"]')
input_celular.clear()
input_celular.send_keys('+5511999999999')

# Salvar
btn_salvar = driver.find_element(By.CSS_SELECTOR, 'button[data-id="saveButtonId"]')
btn_salvar.click()


DEPOIS (Com SelectorManager):
-----------------------------
sm = SelectorManager('config/contato_detalhes_selectors.json')

# Tudo em 3 linhas!
sm.click_element(driver, 'edicao', 'botao_editar')
sm.send_keys(driver, '+5511999999999', 'edicao', 'campos_input', 'celular')
sm.click_element(driver, 'edicao', 'botao_salvar')

VANTAGENS:
✅ Mais legível
✅ Fallback automático
✅ Logs automáticos
✅ Fácil manutenção
"""


# ============================================================================
# EXEMPLO 10: Integração com código existente
# ============================================================================

def integrar_com_processing(driver, nome_cliente):
    """
    Exemplo de como integrar com o código existente em processing.py
    """
    # Usar o SelectorManager da tela de detalhes
    sm_detalhes = SelectorManager('config/contato_detalhes_selectors.json')
    
    # Extrair telefones atuais
    celular = sm_detalhes.get_text(driver, 'painel_central', 'propriedades', 'campos', 'celular')
    telefone = sm_detalhes.get_text(driver, 'painel_central', 'propriedades', 'campos', 'telefone')
    
    logging.info(f"[{nome_cliente}] Celular: {celular}")
    logging.info(f"[{nome_cliente}] Telefone: {telefone}")
    
    # Aqui você pode chamar as funções de validação e correção
    # que já existem em utils/telefone.py
    from utils.telefone import validar_telefone_whatsapp, normalizar_numero
    
    # Validar e corrigir se necessário
    # ... (lógica existente)
    
    return celular, telefone
