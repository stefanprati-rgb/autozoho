# Arquivo: config/constants.py
import os
from types import SimpleNamespace

# --- 1. CREDENCIAIS (Preencha com os seus dados reais) ---
ZOHO_EMAIL = "seu_email@exemplo.com" 
ZOHO_SENHA = "sua_senha"

# --- 2. URLS ---
URL_ZOHO_DESK = "https://desk.zoho.com/agent/"

# --- 3. LISTAS PARA O MENU (Isto é o que estava a faltar!) ---
DEPARTAMENTOS_DISPONIVEIS = {
    "1": "Alagoas Energia",
    "2": "EGS",
    "3": "Era Verde Energia",
    "4": "Hube",
    "5": "Lua Nova Energia"
}

TEMPLATES_DISPONIVEIS = {
    "1": {
        "nome": "Cobranca Padrao",
        "ancoras": ["fatura", "vencimento"]
    },
    "2": {
        "nome": "Aviso de Corte",
        "ancoras": ["corte", "suspensao"]
    },
    "3": {
        "nome": "Confirmacao de Pagamento",
        "ancoras": ["recebemos", "obrigado"]
    }
    # Adicione mais templates aqui conforme necessário
}

# --- 4. CONFIGURAÇÕES TÉCNICAS (Para compatibilidade) ---
retry_config = SimpleNamespace()
retry_config.tentativas = 3
retry_config.delay = 1
retry_config.backoff = 2

CONFIG = SimpleNamespace()
CONFIG.email = ZOHO_EMAIL
CONFIG.senha = ZOHO_SENHA
CONFIG.url = URL_ZOHO_DESK
CONFIG.retry = retry_config
CONFIG.headless = False

# Alias para compatibilidade com scripts antigos
SETTINGS = CONFIG