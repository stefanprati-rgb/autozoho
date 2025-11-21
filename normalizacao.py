"""
Utilitários de normalização e validação de dados.

Responsabilidades:
- Normalizar nomes (remover acentos, caracteres inválidos)
- Validar e normalizar números WhatsApp (+55 DDD 9XXXX-XXXX)
- Calcular similaridade fuzzy entre nomes
- Classificar PF vs PJ
- Cache de performance para fuzzy
- Testes básicos integrados
"""

import re
import unicodedata
from functools import lru_cache
from typing import List, Tuple, Dict, Optional

# ---------- Configuração Centralizada ----------
CONFIG = None

def _load_config():
    global CONFIG
    if CONFIG is None:
        from config import CONFIG as cfg
        CONFIG = cfg
    return CONFIG


# ---------- Constantes Locais (fallback) ----------
STOPWORDS_NOME = {
    "de", "da", "do", "das", "dos", "e", "d", "jr", "jr.", "junior", "júnior",
    "filho", "neto", "sobrinho", "me", "epp", "s/a", "sa", "s.a", "s.a.", "ltda", "ltda.",
    "holding", "group", "grupogera"
}

SOBRENOMES_COMUNS_IGNORAR = {
    "silva", "santos", "souza", "oliveira", "pereira", "lima", "ferreira",
    "costa", "rodrigues", "almeida", "nascimento", "gomes", "martins",
    "araujo", "melo", "barbosa", "cardoso", "teixeira", "dias", "vieira", "batista"
}

EMPRESA_PALAVRAS_DESCARTAR = {
    "ltda", "ltda.", "me", "epp", "eireli", "s/a", "sa", "s.a", "s.a.", "holding",
    "associação", "associacao", "associacão", "condomínio", "condominio", "condominios",
    "residencial", "edificio", "edifício", "centro", "clínica", "clinica", "auto",
    "automotivo", "empresa", "comercial", "industria", "industrial", "cooperativa",
    "igreja", "paróquia", "paroquia", "sindicato", "escola", "faculdade", "universidade"
}

# DDDs válidos no Brasil
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


# ---------- Funções de Normalização ----------
def normalizar_nome(nome: str, remover_invalidos: bool = False) -> str:
    """
    Normaliza nome para comparação:
    - Remove acentos
    - Remove caracteres especiais (opcional)
    - Converte para minúsculas
    - Remove espaços duplos
    """
    if not nome:
        return ""

    texto = str(nome)

    if remover_invalidos:
        texto = texto.replace("\ufffd", " ")
        texto = re.sub(r"[^\w\s\-]", " ", texto)

    # Remove acentos
    texto = (
        unicodedata.normalize("NFKD", texto)
        .encode("ascii", "ignore")
        .decode("utf-8", "ignore")
    )

    # Remove caracteres não alfanuméricos (exceto espaço e hífen)
    texto = re.sub(r"[^\w\s\-]", "", texto).lower()
    texto = re.sub(r"\s+", " ", texto).strip()

    return texto


# ---------- Funções de Telefone ----------
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


# ---------- Funções de Fuzzy (com cache) ----------
@lru_cache(maxsize=5000)
def _similaridade(a: str, b: str) -> float:
    """Cache local para SequenceMatcher (performance)."""
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a, b).ratio()


def calcular_fuzzy_score(nome_a: str, nome_b: str) -> Dict[str, float]:
    """
    Calcula similaridade fuzzy entre dois nomes normalizados.
    Usa configurações do CONFIG centralizado.
    """
    cfg = _load_config()
    threshold = cfg.fuzzy.threshold
    primeiro_ultimo = cfg.fuzzy.primeiro_ultimo

    if not nome_a or not nome_b:
        return {"match": False, "ratio": 0.0}

    ratio_geral = _similaridade(nome_a, nome_b)
    if ratio_geral <=