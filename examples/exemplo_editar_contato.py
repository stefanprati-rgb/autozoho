# Arquivo: examples/exemplo_editar_contato.py
# -*- coding: utf-8 -*-
"""
EXEMPLO: Usando seletores do Formulário de Edição de Contato

Demonstra como usar o SelectorManager para preencher e salvar
o formulário completo de edição de contato.
"""

from utils.selector_manager import SelectorManager
import logging
import time

# Carregar seletores do formulário de edição
sm = SelectorManager('config/editar_contato_selectors.json')


# ============================================================================
# EXEMPLO 1: Abrir formulário de edição
# ============================================================================

def abrir_formulario_edicao(driver, contato_id):
    """
    Navega para o formulário de edição de um contato
    
    Args:
        contato_id: ID do contato no Zoho
    """
    url = f"https://desk.zoho.com/agent/hubedesk/era-verde-energia/contato/edit/{contato_id}"
    driver.get(url)
    logging.info(f"✅ Abriu formulário de edição do contato {contato_id}")
    time.sleep(2)


# ============================================================================
# EXEMPLO 2: Preencher campo específico
# ============================================================================

def preencher_campo(driver, campo_nome, valor):
    """
    Preenche um campo específico do formulário
    
    Args:
        campo_nome: 'nome', 'sobrenome', 'email', 'telefone', 'celular', etc
        valor: Valor a ser preenchido
    """
    if sm.send_keys(driver, valor, 'formulario', 'campos', campo_nome, 'input', clear_first=True):
        logging.info(f"✅ Campo '{campo_nome}' preenchido: {valor}")
        return True
    
    logging.error(f"❌ Falha ao preencher '{campo_nome}'")
    return False


# ============================================================================
# EXEMPLO 3: Corrigir telefones (caso de uso principal)
# ============================================================================

def corrigir_telefones_formulario(driver, celular_novo=None, telefone_novo=None):
    """
    Corrige os campos de telefone e celular no formulário
    
    Args:
        celular_novo: Novo número de celular com +55 (opcional)
        telefone_novo: Novo número de telefone com +55 (opcional)
    """
    campos_corrigidos = []
    
    # Corrigir celular
    if celular_novo:
        if preencher_campo(driver, 'celular', celular_novo):
            campos_corrigidos.append('celular')
    
    # Corrigir telefone
    if telefone_novo:
        if preencher_campo(driver, 'telefone', telefone_novo):
            campos_corrigidos.append('telefone')
    
    if campos_corrigidos:
        logging.info(f"✅ Campos corrigidos: {', '.join(campos_corrigidos)}")
        return True
    
    logging.warning("⚠️ Nenhum campo foi corrigido")
    return False


# ============================================================================
# EXEMPLO 4: Preencher múltiplos campos
# ============================================================================

def preencher_formulario_completo(driver, dados):
    """
    Preenche múltiplos campos do formulário
    
    Args:
        dados: dict com {'nome': 'João', 'sobrenome': 'Silva', 'email': '...', etc}
    """
    campos_preenchidos = []
    
    for campo, valor in dados.items():
        if valor:  # Só preenche se tiver valor
            if preencher_campo(driver, campo, valor):
                campos_preenchidos.append(campo)
            time.sleep(0.3)  # Pequena pausa entre campos
    
    logging.info(f"✅ {len(campos_preenchidos)} campos preenchidos")
    return len(campos_preenchidos)


# ============================================================================
# EXEMPLO 5: Salvar formulário
# ============================================================================

def salvar_formulario(driver):
    """Clica no botão Salvar"""
    if sm.click_element(driver, 'formulario', 'acoes', 'botao_salvar'):
        logging.info("✅ Formulário salvo")
        time.sleep(2)  # Aguardar salvar
        return True
    
    logging.error("❌ Falha ao salvar formulário")
    return False


# ============================================================================
# EXEMPLO 6: Cancelar edição
# ============================================================================

def cancelar_edicao(driver):
    """Clica no botão Cancelar"""
    if sm.click_element(driver, 'formulario', 'acoes', 'botao_cancelar'):
        logging.info("✅ Edição cancelada")
        time.sleep(1)
        return True
    
    return False


# ============================================================================
# EXEMPLO 7: Obter valor de um campo
# ============================================================================

def obter_valor_campo(driver, campo_nome):
    """
    Obtém o valor atual de um campo
    
    Args:
        campo_nome: Nome do campo
    
    Returns:
        str: Valor do campo
    """
    campo = sm.find_element_safe(driver, 'formulario', 'campos', campo_nome, 'input')
    
    if campo:
        valor = campo.get_attribute('value') or campo.text
        logging.info(f"📋 {campo_nome}: {valor}")
        return valor
    
    return None


# ============================================================================
# EXEMPLO 8: Verificar campos obrigatórios
# ============================================================================

def verificar_campos_obrigatorios(driver):
    """
    Verifica se todos os campos obrigatórios estão preenchidos
    """
    # Sobrenome é obrigatório
    sobrenome = obter_valor_campo(driver, 'sobrenome')
    
    if not sobrenome:
        logging.error("❌ Campo obrigatório 'Sobrenome' está vazio!")
        return False
    
    logging.info("✅ Campos obrigatórios preenchidos")
    return True


# ============================================================================
# EXEMPLO 9: Workflow completo - Corrigir e salvar
# ============================================================================

def workflow_corrigir_telefones(driver, contato_id, celular_novo, telefone_novo):
    """
    Workflow completo: abre formulário, corrige telefones, salva
    
    Args:
        contato_id: ID do contato
        celular_novo: Novo celular com +55
        telefone_novo: Novo telefone com +55
    """
    logging.info(f"🚀 Iniciando correção de telefones - Contato {contato_id}")
    
    # 1. Abrir formulário
    abrir_formulario_edicao(driver, contato_id)
    
    # 2. Verificar valores atuais
    celular_atual = obter_valor_campo(driver, 'celular')
    telefone_atual = obter_valor_campo(driver, 'telefone')
    
    logging.info(f"📋 Valores atuais:")
    logging.info(f"   Celular: {celular_atual}")
    logging.info(f"   Telefone: {telefone_atual}")
    
    # 3. Corrigir telefones
    if not corrigir_telefones_formulario(driver, celular_novo, telefone_novo):
        logging.error("❌ Falha ao corrigir telefones")
        return False
    
    # 4. Verificar campos obrigatórios
    if not verificar_campos_obrigatorios(driver):
        logging.error("❌ Campos obrigatórios não preenchidos")
        cancelar_edicao(driver)
        return False
    
    # 5. Salvar
    if salvar_formulario(driver):
        logging.info("✅ Workflow concluído com sucesso!")
        return True
    
    logging.error("❌ Workflow falhou")
    return False


# ============================================================================
# EXEMPLO 10: Integração com lista de contatos
# ============================================================================

def processar_contatos_em_massa(driver, lista_contatos, funcao_correcao):
    """
    Processa múltiplos contatos aplicando uma função de correção
    
    Args:
        lista_contatos: Lista de IDs de contatos
        funcao_correcao: Função que recebe (driver, contato_id)
    """
    total = len(lista_contatos)
    sucessos = 0
    
    for idx, contato_id in enumerate(lista_contatos, 1):
        logging.info(f"📝 Processando {idx}/{total}: {contato_id}")
        
        try:
            if funcao_correcao(driver, contato_id):
                sucessos += 1
            else:
                logging.warning(f"⚠️ Falha ao processar {contato_id}")
        except Exception as e:
            logging.error(f"❌ Erro ao processar {contato_id}: {e}")
            continue
        
        time.sleep(1)  # Pausa entre contatos
    
    logging.info(f"🎉 Processamento concluído: {sucessos}/{total} sucessos")
    return sucessos


# ============================================================================
# EXEMPLO 11: Validar antes de salvar
# ============================================================================

def validar_telefones_antes_salvar(driver):
    """
    Valida os telefones antes de salvar o formulário
    """
    from utils.telefone import validar_telefone_whatsapp
    
    celular = obter_valor_campo(driver, 'celular')
    telefone = obter_valor_campo(driver, 'telefone')
    
    erros = []
    
    # Validar celular
    if celular:
        valido, msg = validar_telefone_whatsapp(celular)
        if not valido:
            erros.append(f"Celular inválido: {msg}")
    
    # Validar telefone
    if telefone:
        valido, msg = validar_telefone_whatsapp(telefone)
        if not valido:
            erros.append(f"Telefone inválido: {msg}")
    
    if erros:
        for erro in erros:
            logging.error(f"❌ {erro}")
        return False
    
    logging.info("✅ Telefones válidos")
    return True


# ============================================================================
# EXEMPLO 12: Integração com código existente
# ============================================================================

def integrar_com_processing(driver, nome_cliente, celular_corrigido, telefone_corrigido):
    """
    Exemplo de integração com o fluxo existente em processing.py
    """
    # Esta função pode ser chamada após detectar que um número precisa correção
    
    logging.info(f"[{nome_cliente}] Aplicando correções no formulário...")
    
    # Corrigir usando o formulário
    if corrigir_telefones_formulario(driver, celular_corrigido, telefone_corrigido):
        # Validar antes de salvar
        if validar_telefones_antes_salvar(driver):
            # Salvar
            if salvar_formulario(driver):
                logging.info(f"[{nome_cliente}] ✅ Correções aplicadas e salvas")
                return True
    
    logging.error(f"[{nome_cliente}] ❌ Falha ao aplicar correções")
    return False


# ============================================================================
# COMPARAÇÃO: ANTES vs DEPOIS
# ============================================================================

"""
ANTES (Hardcoded):
------------------
# Preencher celular
campo_celular = driver.find_element(By.XPATH, "//textbox[@id='ZD_109']")
campo_celular.clear()
campo_celular.send_keys('+5511999999999')

# Preencher telefone
campo_telefone = driver.find_element(By.XPATH, "//textbox[@id='ZD_108']")
campo_telefone.clear()
campo_telefone.send_keys('+5511888888888')

# Salvar
botao_salvar = driver.find_element(By.XPATH, "//button[contains(text(), 'Salvar')]")
botao_salvar.click()


DEPOIS (Com SelectorManager):
-----------------------------
sm = SelectorManager('config/editar_contato_selectors.json')

# Workflow completo em uma função!
workflow_corrigir_telefones(
    driver,
    contato_id='919191000005272169',
    celular_novo='+5511999999999',
    telefone_novo='+5511888888888'
)

VANTAGENS:
✅ Muito mais simples
✅ Validação automática
✅ Logs detalhados
✅ Tratamento de erros
✅ Reutilizável
"""
