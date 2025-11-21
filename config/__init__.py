# Arquivo: config/__init__.py

# Importa tudo dos sub-arquivos para ficar disponivel diretamente em 'config'
from .settings import *
from .constants import *
from .selectors import *

# Se SETTINGS e CONFIG nao existirem nos arquivos acima,
# definimos alias para garantir compatibilidade com scripts antigos
try:
    # Tenta encontrar variaveis comuns que o auth.py pode estar procurando
    if 'SETTINGS' not in globals():
        SETTINGS = {} # Define vazio para evitar crash se nao existir
    if 'CONFIG' not in globals():
        # Geralmente CONFIG sao as constantes
        CONFIG = locals() 
except Exception:
    pass
