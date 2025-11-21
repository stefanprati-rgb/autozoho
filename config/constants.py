# Arquivo: config/constants.py
import os
from types import SimpleNamespace

# --- 1. CREDENCIAIS (Preencha com os seus dados reais) ---
ZOHO_EMAIL = "gestao.gdc@grupogera.com" 
ZOHO_SENHA = "Ger@2357"  # <--- ATENÇÃO: Coloque a senha correta aqui

# --- 2. URLS ---
URL_ZOHO_DESK = "https://desk.zoho.com/agent/"

# --- 3. DEPARTAMENTOS (Extraídos do script original) ---
DEPARTAMENTOS_DISPONIVEIS = {
    "1": "Alagoas Energia",
    "2": "EGS",
    "3": "Era Verde Energia",
    "4": "Hube",
    "5": "Lua Nova Energia"
}

# --- 4. TEMPLATES (Lista completa extraída do monolito) ---
TEMPLATES_DISPONIVEIS = {
    "1": {
        "nome": "Reunião Contrato",
        "ancoras": [
            "Aqui é Stefan, da Era Verde Energia.",
            "atualização importante em sua parceria"
        ]
    },
    "2": {
        "nome": "Cobrança 1.4",
        "ancoras": [
            "O pagamento da fatura ainda não foi localizado",
            "Para seguirmos com a regularização"
        ]
    },
    "3": {
        "nome": "Acordo em Atraso",
        "ancoras": [
            "seu boleto unificado de acordo",
            "ainda não foi pago e está vencido"
        ]
    },
    "4": {
        "nome": "Protocolo aberto",
        "ancoras": [
            "protocolo em aberto",
            "continuidade ao atendimento"
        ]
    },
    "5": {
        "nome": "Boas Vindas + Cobrança",
        "ancoras": [
            "Olá, querido cliente!",
            "Seja muito bem-vindo à Era Verde Energia!",
            "redução no valor da sua conta da CPFL"
        ]
    },
    "6": {
        "nome": "Comunicado_faturamento",
        "ancoras": [
            "Prezado cliente",
            "não haverá faturamento",
            "problema técnico identificado na usina"
        ]
    },
    "7": {
        "nome": "Boas Vindas Padrão",
        "ancoras": [
            "Prezado cliente",
            "Era Verde",
            "sua gestora de energia",
            "Reverde era o seu canal",
            "seremos seu ponto focal"
        ]
    },
    "8": {
        "nome": "Contato",
        "ancoras": [
            "Olá! Tudo bem?",
            "retomar a nossa conversa",
            "clique no botão abaixo"
        ]
    },
    "9": {
        "nome": "Boas-vindas",
        "ancoras": [
            "Olá! Tudo bem?",
            "Me chamo Isabella",
            "prosseguir com o seu atendimento"
        ]
    },
    "10": {
        "nome": "Cobranca Setembro",
        "ancoras": [
            "Estamos com dificuldades em localizar seu pagamento",
            "fatura Setembro/25",
            "regularização do valor"
        ]
    },
    "11": {
        "nome": "Data_Vencimento",
        "ancoras": [
            "Gostariamos de informar que partir dso p´roximos faturamentos",
            "os boletos da EGS terão 10 dias corridos entre a amissão e vencimento",
            "e as datas de vencimento ficarão entre os dias 15 e 20 de cada mês."
        ]
    },
    "12": {
        "nome": "Black November",
        "ancoras": [
            "Era Verde Energia: Mega Desconto para Você! 💚",
            "Olá Cliente, volte a economizar com a gente!",
            "15% de DESCONTO no valor total para quitação imediata!"
        ]
    }
}

# --- 5. CONFIGURAÇÕES TÉCNICAS ---
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

# Alias para compatibilidade
SETTINGS = CONFIG