"""
Utilitários de telefone (Brasil / WhatsApp).

Responsabilidades:
- Validar números de WhatsApp (+55 DDD 9XXXX-XXXX)
- Normalizar números para E.164 (+55DDDNXXXXXXX), com heurística para inserir "9"
- Testes unitários básicos
"""

import re
from typing import Optional, Tuple

# Conjunto de DDDs válidos no Brasil (fixo/celular)
DDDS_VALIDOS = {
    11,12,13,14,15,16,17,18,19,
    21,22,24,27,28,
    31,32,33,34,35,37,38,
    41,42,43,44,45,46,47,48,49,
    51,53,54,55,
    61,62,63,64,65,66,67,68,69,
    71,73,74,75,77,79,
    81,82,83,84,85,86,87,88,89,
    91,92,93,94,95,96,97,98,99,
}

E164_BR_REGEX = re.compile(r"^\+55\d{2}9\d{8}$")  # +55 + DDD(2) + 9 + 8 dígitos


# ---------- Funções Públicas ----------
def validar_numero_whatsapp(numero: str) -> Tuple[bool, str]:
    """
    Valida número de WhatsApp Brasil em E.164.
    Retorna (válido, mensagem).
    Regras:
      - Formato: +55 DDD 9 XXXX-XXXX  (total 13 dígitos após +55)
      - DDD deve ser válido
    """
    if not numero:
        return False, "Número vazio"

    # Aceita com ou sem '+', com pontuação; valida sempre no formato E.164 ao final
    n = normalizar_numero_whatsapp(numero)
    if not n:
        return False, f"Formato inválido: {numero}"

    # Checa DDD
    ddd = int(n[3:5])  # +55[DD]9...
    if ddd not in DDDS_VALIDOS:
        return False, f"DDD inválido: {ddd}"

    # Já garantido pelo normalizar que tem o 9: regex final por segurança
    if not E164_BR_REGEX.match(n):
        return False, f"Número não corresponde ao padrão WhatsApp: {n}"

    return True, "Válido"


def normalizar_numero_whatsapp(numero: str) -> Optional[str]:
    """
    Normaliza número para E.164 Brasil: +55DDDNXXXXXXX
    Heurísticas:
      - Remove tudo que não é dígito
      - Aceita entradas com: +55..., 55..., 0DD..., DDD..., etc.
      - Se vier DDD + 8 dígitos (10 no total), insere o '9' após o DDD
      - Rejeita tamanhos que não batem (não tenta “adivinhar” DDD ausente)
    """
    if not numero:
        return None

    raw = re.sub(r"\D", "", numero)

    # Casos com país
    if raw.startswith("55"):
        local = raw[2:]  # DDD + número
    elif raw.startswith("0") and len(raw) >= 11:
        # Remoção do prefixo de longa distância: 0 + DDD + ...
        local = raw[1:]
    else:
        local = raw

    # Agora esperamos ter DDD + número (10, 11 ou 12+ dígitos). Filtramos pelos plausíveis.
    # Celular BR (sem +55) é 11 dígitos: DDD(2) + 9 + 8.
    if len(local) == 11:
        # já tem DDD + 9 + 8
        pass
    elif len(local) == 10:
        # DDD + 8 (sem 9): inserir o 9
        local = local[:2] + "9" + local[2:]
    else:
        # Outros comprimentos não são suportados para WhatsApp BR com DDD
        return None

    # DDD válido?
    try:
        ddd = int(local[:2])
    except ValueError:
        return None
    if ddd not in DDDS_VALIDOS:
        return None

    e164 = f"+55{local}"
    return e164 if E164_BR_REGEX.match(e164) else None


# ---------- Testes Unitários Básicos ----------
if __name__ == "__main__":
    # Normalização
    assert normalizar_numero_whatsapp("(11) 91234-5678") == "+5511912345678"
    assert normalizar_numero_whatsapp("+55 (11) 91234-5678") == "+5511912345678"
    assert normalizar_numero_whatsapp("5511912345678") == "+5511912345678"
    assert normalizar_numero_whatsapp("011912345678") == "+5511912345678"  # com 0 de longa distância
    assert normalizar_numero_whatsapp("11912345678") == "+5511912345678"
    assert normalizar_numero_whatsapp("1191234567") == "+5511912345678"    # insere '9'
    assert normalizar_numero_whatsapp("123") is None

    # Validação
    assert validar_numero_whatsapp("+5511912345678")[0] is True
    assert validar_numero_whatsapp("11912345678")[0] is True
    assert validar_numero_whatsapp("1131234567")[0] is False   # fixo (sem 9)
    assert validar_numero_whatsapp("+5590912345678")[0] is False  # DDD 90 inválido

    print("✓ Todos os testes básicos passaram.")
