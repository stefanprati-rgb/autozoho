import re


def formatar_documento_brasil(valor):
    """
    Recebe um número limpo e retorna formatado como CPF ou CNPJ.
    Ex: 62955505197360 -> 62.955.505/1973-60
    """
    if not valor:
        return ""
        
    # Remove tudo que não é dígito para garantir
    limpo = re.sub(r'\D', '', str(valor))
    
    # Lógica de formatação
    if len(limpo) == 11:  # CPF
        return f"{limpo[:3]}.{limpo[3:6]}.{limpo[6:9]}-{limpo[9:]}"
    elif len(limpo) == 14:  # CNPJ
        return f"{limpo[:2]}.{limpo[2:5]}.{limpo[5:8]}/{limpo[8:12]}-{limpo[12:]}"
    else:
        # Retorna original se não for nem CPF nem CNPJ (pode ser nome)
        return valor
