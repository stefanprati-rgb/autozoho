# Arquivo: normalizacao.py
import re
import unicodedata
from difflib import SequenceMatcher

def normalizar_nome(nome, remover_invalidos=False):
    """
    Remove acentos, caracteres especiais e espaços extras.
    """
    if not nome:
        return ""
    
    # Garante que é string
    nome = str(nome)
    
    if remover_invalidos:
        # Substitui caractere de 'substituição' comum em erros de encoding
        nome = nome.replace('\ufffd', ' ')
    
    # Remove acentos (Decomposição NFKD)
    nfkd = unicodedata.normalize('NFKD', nome)
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    
    # Mantém apenas letras, números e espaços (remove pontuação)
    # O 'lower()' converte para minúsculo
    limpo = re.sub(r'[^a-zA-Z0-9\s]', ' ', sem_acento).lower()
    
    # Remove espaços duplicados e espaços nas pontas
    return " ".join(limpo.split())

def tipo_cliente(nome):
    """
    Tenta adivinhar se é PJ ou PF baseado em palavras-chave.
    Retorna "PJ" ou "PF".
    """
    if not nome:
        return "PF"
        
    nome_norm = normalizar_nome(nome).upper()
    
    # Lista de termos comuns em nomes de empresas
    termos_pj = [
        "LTDA", " S A", " S/A", "COND.", "CONDOMINIO", "IGREJA", 
        "ASSOCIA", "ME", "EPP", "EIRELI", "COMERCIO", "INDUSTRIA",
        "SERVICOS", "HOLDING", "GRUPO", "ENGENHARIA"
    ]
    
    for termo in termos_pj:
        if termo in nome_norm:
            return "PJ"
            
    return "PF"

def calcular_fuzzy_score(nome1, nome2):
    """
    Calcula a similaridade entre dois nomes (0.0 a 1.0).
    Retorna um dicionário no formato esperado pelo busca.py.
    """
    n1 = normalizar_nome(nome1)
    n2 = normalizar_nome(nome2)
    
    if not n1 or not n2:
        return {"ratio": 0.0}
    
    # Usa o algoritmo padrão do Python para comparação
    ratio = SequenceMatcher(None, n1, n2).ratio()
    
    return {"ratio": ratio}