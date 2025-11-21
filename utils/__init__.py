"""
Pacote de utilitários da automação Zoho Desk.

API pública:
- normalizar_nome
- validar_numero_whatsapp
- normalizar_numero_whatsapp
- calcular_fuzzy_score
- tipo_cliente
"""

from typing import TYPE_CHECKING

__all__ = [
    "normalizar_nome",
    "validar_numero_whatsapp",
    "normalizar_numero_whatsapp",
    "calcular_fuzzy_score",
    "tipo_cliente",
    "__version__",
]

__version__ = "0.1.0"


# ---------- Lazy Loading (evita import no init) ----------
def __getattr__(name: str):
    """Só importa normalizacao.py quando a função for realmente usada."""
    if name in __all__:
        from . import normalizacao  # import local, sob demanda
        return getattr(normalizacao, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# ---------- Suporte a Type Checkers ----------
if TYPE_CHECKING:
    from .normalizacao import (
        normalizar_nome,
        validar_numero_whatsapp,
        normalizar_numero_whatsapp,
        calcular_fuzzy_score,
        tipo_cliente,
    )