# Arquivo: config/constants.py
import os
from types import SimpleNamespace

# --- CREDENCIAIS ---
ZOHO_EMAIL = "gestao.gdc@grupogera.com"
ZOHO_SENHA = "Ger@2357" 
URL_ZOHO_DESK = "https://desk.zoho.com/agent/"

# --- DEPARTAMENTOS ---
DEPARTAMENTOS_DISPONIVEIS = {
    "1": "Alagoas Energia",
    "2": "EGS",
    "3": "Era Verde Energia",
    "4": "Hube",
    "5": "Lua Nova Energia"
}

# --- TEMPLATES (LISTA COMPLETA) ---
TEMPLATES_DISPONIVEIS = {
    "1": { "nome": "Reunião Contrato", "ancoras": ["Aqui é Stefan", "atualização importante"] },
    "2": { "nome": "Cobrança .", "ancoras": ["O pagamento da fatura ainda não foi localizado", "Para seguirmos com a regularização"] },
    "3": { "nome": "Acordo em Atraso", "ancoras": ["seu boleto unificado", "ainda não foi pago"] },
    "4": { "nome": "Protocolo aberto", "ancoras": ["protocolo em aberto", "continuidade ao atendimento"] },
    "5": { "nome": "Boas Vindas + Cobrança", "ancoras": ["Olá, querido cliente", "redução no valor"] },
    "6": { "nome": "Comunicado_faturamento", "ancoras": ["não haverá faturamento", "problema técnico"] },
    "7": { "nome": "Boas Vindas Padrão", "ancoras": ["sua gestora de energia", "Reverde era o seu canal"] },
    "8": { "nome": "Contato", "ancoras": ["retomar a nossa conversa", "clique no botão abaixo"] },
    "9": { "nome": "Boas-vindas", "ancoras": ["Me chamo Isabella", "prosseguir com o seu atendimento"] },
    "10": { "nome": "Cobranca Setembro", "ancoras": ["fatura Setembro/25", "regularização do valor"] },
    "11": { "nome": "Data_Vencimento", "ancoras": ["datas de vencimento ficarão entre", "próximos faturamentos", "boletos da EGS"] },
    "12": { "nome": "Black November", "ancoras": ["Mega Desconto para Você", "15% de DESCONTO"] },
    "13": { "nome": "Assinatura Pendente Contrato", "ancoras": ["Olá tudo bem", "Aqui é o Stefan da Era Verde Energia"] },
    "14": { "nome": "Cobranca Novembro", "ancoras": ["Estamos com dificuldades em localizar", "fatura Novembro/25", "vencida no dia 15/12"] },
    "15": { "nome": "Acordo Cobrança", "ancoras": ["parcela do acordo", "ainda não foi pago e está vencido"] },
    "16": { "nome": "Envio de Conta", "ancoras": ["conta digital da EGS Energia", "já está disponível", "o e-mail cadastrado"] }
}

# --- CONFIGURAÇÕES ---
retry_config = SimpleNamespace(tentativas=3, delay=1, backoff=2)
CONFIG = SimpleNamespace(
    email=ZOHO_EMAIL, 
    senha=ZOHO_SENHA, 
    url=URL_ZOHO_DESK, 
    retry=retry_config, 
    headless=False
)
SETTINGS = CONFIG