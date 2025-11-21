# Arquivo: config/constants.py
import os
from types import SimpleNamespace

# --- 1. CREDENCIAIS (Preencha aqui) ---
ZOHO_EMAIL = "seu_email@exemplo.com"
ZOHO_SENHA = "sua_senha"

# --- 2. URLS ---
URL_ZOHO_DESK = "https://desk.zoho.com/agent/"

# --- 3. CONFIGURAÇÕES AVANÇADAS (Objeto de Configuração) ---

# Cria a configuração de Retry (Tentativas)
retry_config = SimpleNamespace()
retry_config.tentativas = 3
retry_config.delay = 1
retry_config.backoff = 2

# Cria o objeto CONFIG principal
CONFIG = SimpleNamespace()
CONFIG.email = ZOHO_EMAIL
CONFIG.senha = ZOHO_SENHA
CONFIG.url = URL_ZOHO_DESK
CONFIG.retry = retry_config  # <-- Aqui está a correção para o erro 'retry'
CONFIG.headless = False      # Outra configuração comum que pode fazer falta

# Alias para compatibilidade (caso algum arquivo procure por SETTINGS)
SETTINGS = CONFIG
