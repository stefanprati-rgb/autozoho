# Arquivo: core/processing_adapter.py
# -*- coding: utf-8 -*-
"""
Adapter para usar helpers melhorados mantendo compatibilidade com código existente

Este módulo permite usar as funções melhoradas com SelectorManager
sem modificar o código original em processing.py
"""

from core.processing_helpers import (
    corrigir_telefones_modal_inline,
    processar_contato_completo,
    verificar_e_preparar_correcoes
)

# Importar funções originais que não foram refatoradas ainda
from core.processing import processar_pagina_cliente as processar_pagina_cliente_original


def corrigir_telefones_na_interface(driver, correcoes, nome_cliente):
    """
    Wrapper compatível com assinatura original que usa helper melhorado
    
    VANTAGENS sobre a versão original:
    - Usa SelectorManager com fallback automático
    - Código mais limpo e manutenível
    - Logs automáticos melhorados
    
    Args:
        driver: WebDriver do Selenium
        correcoes: Lista de dicts com {'campo_tipo': 'mobile'/'phone', 'numero': '+55...', 'label': '...'}
        nome_cliente: Nome do cliente para logs
    
    Returns:
        bool: True se corrigiu com sucesso
    """
    return corrigir_telefones_modal_inline(driver, correcoes, nome_cliente)


def processar_pagina_cliente(driver, nome_cliente, departamento, template_nome, ancoras, dry_run=False):
    """
    Wrapper que mantém compatibilidade com código existente
    
    NOTA: Esta função ainda usa a implementação original de processing.py
    para manter compatibilidade total. A correção de telefones já usa
    o helper melhorado através do adapter acima.
    
    Para usar versão totalmente melhorada, use:
    from core.processing_helpers import processar_contato_completo
    """
    # Por enquanto, delega para função original
    # A função original já vai usar corrigir_telefones_na_interface melhorado
    # se você importar deste adapter em vez de processing.py
    return processar_pagina_cliente_original(
        driver, nome_cliente, departamento, template_nome, ancoras, dry_run
    )


# Exportar funções para uso externo
__all__ = [
    'corrigir_telefones_na_interface',
    'processar_pagina_cliente',
    'processar_contato_completo',
    'verificar_e_preparar_correcoes'
]
