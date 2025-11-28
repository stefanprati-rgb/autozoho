# Arquivo: examples/exemplo_lista_contatos.py
# -*- coding: utf-8 -*-
"""
EXEMPLO: Usando seletores da Lista de Contatos

Demonstra como usar o SelectorManager para interagir com a tela
de listagem de contatos em formato de grade.
"""

from utils.selector_manager import SelectorManager
import logging
import time

# Carregar seletores da lista de contatos
sm = SelectorManager('config/lista_contatos_selectors.json')


# ============================================================================
# EXEMPLO 1: Navegar para lista de contatos
# ============================================================================

def abrir_lista_contatos(driver):
    """Navega para a lista de contatos"""
    if sm.click_element(driver, 'navegacao', 'superior', 'clientes'):
        logging.info("✅ Navegou para lista de contatos")
        time.sleep(2)  # Aguardar carregar
        return True
    
    logging.error("❌ Falha ao navegar para lista")
    return False


# ============================================================================
# EXEMPLO 2: Buscar contato por nome
# ============================================================================

def buscar_contato_por_nome(driver, nome_parcial):
    """
    Busca um contato pelo nome na grade
    
    Args:
        nome_parcial: Parte do nome do contato
    
    Returns:
        WebElement ou None
    """
    from selenium.webdriver.common.by import By
    
    try:
        xpath = f"//a[contains(text(), '{nome_parcial}')]"
        contato = driver.find_element(By.XPATH, xpath)
        logging.info(f"✅ Contato '{nome_parcial}' encontrado")
        return contato
    except Exception as e:
        logging.warning(f"⚠️ Contato '{nome_parcial}' não encontrado: {e}")
        return None


# ============================================================================
# EXEMPLO 3: Clicar em um contato específico
# ============================================================================

def abrir_contato_por_nome(driver, nome):
    """
    Busca e clica em um contato pelo nome
    """
    contato = buscar_contato_por_nome(driver, nome)
    
    if contato:
        contato.click()
        logging.info(f"✅ Abriu detalhes de '{nome}'")
        time.sleep(2)
        return True
    
    return False


# ============================================================================
# EXEMPLO 4: Buscar contato por telefone
# ============================================================================

def buscar_contato_por_telefone(driver, telefone):
    """
    Busca um contato pelo número de telefone
    """
    from selenium.webdriver.common.by import By
    
    try:
        xpath = f"//a[contains(@href, 'tel:') and contains(text(), '{telefone}')]"
        contato = driver.find_element(By.XPATH, xpath)
        logging.info(f"✅ Contato com telefone '{telefone}' encontrado")
        return contato
    except Exception as e:
        logging.warning(f"⚠️ Contato com telefone '{telefone}' não encontrado")
        return None


# ============================================================================
# EXEMPLO 5: Listar todos os contatos visíveis
# ============================================================================

def listar_contatos_visiveis(driver):
    """
    Lista todos os contatos visíveis na página atual
    
    Returns:
        list: Lista de dicts com informações dos contatos
    """
    contatos = sm.find_elements_safe(driver, 'grade_contatos', 'card_contato', 'generico')
    
    lista = []
    for idx, card in enumerate(contatos, 1):
        try:
            nome = card.text.strip()
            href = card.get_attribute('href')
            contato_id = href.split('/')[-1] if href else 'N/A'
            
            lista.append({
                'index': idx,
                'nome': nome,
                'id': contato_id,
                'url': href
            })
        except Exception as e:
            logging.debug(f"Erro ao processar card {idx}: {e}")
    
    logging.info(f"📋 {len(lista)} contatos visíveis na página")
    return lista


# ============================================================================
# EXEMPLO 6: Extrair emails de todos os contatos visíveis
# ============================================================================

def extrair_emails_visiveis(driver):
    """
    Extrai todos os emails visíveis na página
    """
    from selenium.webdriver.common.by import By
    
    emails = driver.find_elements(By.XPATH, "//a[contains(@href, 'mailto:')]")
    
    lista_emails = []
    for email_elem in emails:
        email = email_elem.text.strip()
        if email and '@' in email:
            lista_emails.append(email)
    
    logging.info(f"📧 {len(lista_emails)} emails encontrados")
    return lista_emails


# ============================================================================
# EXEMPLO 7: Extrair telefones de todos os contatos visíveis
# ============================================================================

def extrair_telefones_visiveis(driver):
    """
    Extrai todos os telefones visíveis na página
    """
    from selenium.webdriver.common.by import By
    
    telefones = driver.find_elements(By.XPATH, "//a[contains(@href, 'tel:')]")
    
    lista_telefones = []
    for tel_elem in telefones:
        tel = tel_elem.text.strip()
        if tel:
            lista_telefones.append(tel)
    
    logging.info(f"📱 {len(lista_telefones)} telefones encontrados")
    return lista_telefones


# ============================================================================
# EXEMPLO 8: Navegar entre páginas
# ============================================================================

def ir_proxima_pagina(driver):
    """Vai para a próxima página de contatos"""
    if sm.click_element(driver, 'paginacao', 'proxima_pagina'):
        logging.info("✅ Foi para próxima página")
        time.sleep(2)
        return True
    
    logging.warning("⚠️ Não há próxima página ou botão não encontrado")
    return False


def ir_pagina_anterior(driver):
    """Volta para a página anterior"""
    if sm.click_element(driver, 'paginacao', 'pagina_anterior'):
        logging.info("✅ Voltou para página anterior")
        time.sleep(2)
        return True
    
    return False


# ============================================================================
# EXEMPLO 9: Workflow - Processar todos os contatos de uma página
# ============================================================================

def processar_contatos_pagina(driver, funcao_processamento):
    """
    Processa todos os contatos visíveis na página atual
    
    Args:
        funcao_processamento: Função que recebe (driver, contato_info) e processa
    
    Returns:
        int: Número de contatos processados
    """
    contatos = listar_contatos_visiveis(driver)
    processados = 0
    
    for contato in contatos:
        try:
            logging.info(f"Processando: {contato['nome']}")
            
            # Abrir detalhes do contato
            driver.get(contato['url'])
            time.sleep(2)
            
            # Executar função de processamento
            funcao_processamento(driver, contato)
            
            # Voltar para lista
            abrir_lista_contatos(driver)
            time.sleep(2)
            
            processados += 1
            
        except Exception as e:
            logging.error(f"❌ Erro ao processar {contato['nome']}: {e}")
            continue
    
    logging.info(f"✅ {processados}/{len(contatos)} contatos processados")
    return processados


# ============================================================================
# EXEMPLO 10: Workflow - Processar todas as páginas
# ============================================================================

def processar_todas_paginas(driver, funcao_processamento, max_paginas=None):
    """
    Processa contatos de todas as páginas
    
    Args:
        funcao_processamento: Função que processa cada contato
        max_paginas: Número máximo de páginas (None = todas)
    """
    pagina_atual = 1
    total_processados = 0
    
    while True:
        logging.info(f"📄 Processando página {pagina_atual}")
        
        # Processar contatos da página atual
        processados = processar_contatos_pagina(driver, funcao_processamento)
        total_processados += processados
        
        # Verificar se deve parar
        if max_paginas and pagina_atual >= max_paginas:
            logging.info(f"⚠️ Limite de {max_paginas} páginas atingido")
            break
        
        # Tentar ir para próxima página
        if not ir_proxima_pagina(driver):
            logging.info("✅ Última página processada")
            break
        
        pagina_atual += 1
    
    logging.info(f"🎉 Total: {total_processados} contatos processados em {pagina_atual} páginas")
    return total_processados


# ============================================================================
# EXEMPLO 11: Filtrar contatos
# ============================================================================

def aplicar_filtro_contatos(driver, filtro_nome):
    """
    Aplica um filtro na lista de contatos
    
    Args:
        filtro_nome: Nome do filtro (ex: 'Todos', 'Meus Contatos', etc)
    """
    # Clicar no dropdown de filtro
    if sm.click_element(driver, 'filtros_e_opcoes', 'dropdown_filtro', 'todos_contatos'):
        time.sleep(0.5)
        
        # Selecionar opção
        from selenium.webdriver.common.by import By
        try:
            xpath = f"//menuitem[contains(text(), '{filtro_nome}')]"
            opcao = driver.find_element(By.XPATH, xpath)
            opcao.click()
            logging.info(f"✅ Filtro '{filtro_nome}' aplicado")
            time.sleep(2)
            return True
        except Exception as e:
            logging.error(f"❌ Erro ao aplicar filtro: {e}")
            return False
    
    return False


# ============================================================================
# EXEMPLO 12: Exemplo de função de processamento
# ============================================================================

def exemplo_corrigir_telefones(driver, contato_info):
    """
    Exemplo de função que pode ser passada para processar_contatos_pagina
    
    Esta função seria chamada para cada contato
    """
    from utils.telefone import validar_telefone_whatsapp, normalizar_numero
    
    # Aqui você implementaria a lógica de correção
    # usando os seletores de contato_detalhes_selectors.json
    
    logging.info(f"Verificando telefones de: {contato_info['nome']}")
    
    # Exemplo: extrair e validar telefones
    # ... (implementar usando SelectorManager)
    
    pass


# ============================================================================
# COMPARAÇÃO: ANTES vs DEPOIS
# ============================================================================

"""
ANTES (Hardcoded):
------------------
# Buscar contato
contatos = driver.find_elements(By.XPATH, "//a[contains(@href, 'details/')]")
for contato in contatos:
    if 'Paulo' in contato.text:
        contato.click()
        break


DEPOIS (Com SelectorManager):
-----------------------------
# Buscar e abrir contato
abrir_contato_por_nome(driver, 'Paulo')

# Ou processar todos
processar_contatos_pagina(driver, minha_funcao_processamento)

VANTAGENS:
✅ Código mais limpo
✅ Reutilizável
✅ Fácil manutenção
✅ Logs automáticos
"""
