#!/usr/bin/env python3
# run_batch.py
from __future__ import annotations

import os, time, csv, re, unicodedata
from pathlib import Path
from typing import Optional, List

from loguru import logger
from tqdm import tqdm

from core.driver import DriverManager, _screenshot_fallback
from auth import LoginManager
from core.busca import buscar_e_abrir_cliente
from utils.whatsapp import abrir_canal_whatsapp, enviar_whatsapp, selecionar_template_whatsapp
from utils.departamento import trocar_departamento_zoho
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ----------------- CONFIG BÁSICA -----------------
COOLDOWN_INTERVALO_CLIENTES = 20
COOLDOWN_DURACAO_SEGUNDOS = 10

TEMPLATES_DISPONIVEIS = {
    "1": {"nome": "Reunião Contrato", "ancoras": ["Aqui é", "atualização importante"]},
    "2": {"nome": "Cobrança 1.4", "ancoras": ["pagamento", "regularização"]},
    "3": {"nome": "Acordo em Atraso", "ancoras": ["boleto unificado", "vencido"]},
    "4": {"nome": "Protocolo aberto", "ancoras": ["protocolo em aberto", "continuidade"]},
    "5": {"nome": "Boas Vindas + Cobrança", "ancoras": ["bem-vindo", "redução no valor"]},
    "6": {"nome": "Comunicado_faturamento", "ancoras": ["Prezado cliente", "não haverá faturamento"]},
    "7": {"nome": "Boas Vindas Padrão", "ancoras": ["Era Verde", "ponto focal"]},
    "8": {"nome": "Contato", "ancoras": ["retomar a nossa conversa"]},
    "9": {"nome": "Boas-vindas", "ancoras": ["prosseguir com o seu atendimento"]},
}

DEPARTAMENTOS_DISPONIVEIS = {
    "1": "Alagoas Energia",
    "2": "EGS",
    "3": "Era Verde Energia",
    "4": "Hube",
    "5": "Lua Nova Energia"
}

# ----------------- INPUT DA LISTA -----------------
def carregar_lista_clientes(caminho: Optional[str]) -> List[str]:
    if not caminho:
        print("Passe o caminho do arquivo (xlsx/csv/txt) via argumento ou edite no script.")
        return []
    p = Path(caminho)
    if not p.exists():
        print(f"Arquivo não encontrado: {p}")
        return []
    clientes: List[str] = []
    if p.suffix.lower() == ".xlsx":
        import openpyxl
        wb = openpyxl.load_workbook(p)
        for row in wb.active.iter_rows(min_row=1, values_only=True):
            if row and row[0]:
                clientes.append(str(row[0]).strip())
    else:
        encodings = ["utf-8", "latin-1", "cp1252"]
        for enc in encodings:
            try:
                txt = p.read_text(encoding=enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise RuntimeError("Não foi possível detectar encoding do arquivo.")
        if p.suffix.lower() == ".csv":
            try:
                dialect = csv.Sniffer().sniff(txt[:1024], delimiters=";,")
                rows = list(csv.reader(txt.splitlines(), dialect=dialect))
            except csv.Error:
                rows = list(csv.reader(txt.splitlines(), delimiter=";"))
            for r in rows:
                if r and r[0]:
                    clientes.append(r[0].strip())
        else:
            for line in txt.splitlines():
                if line.strip():
                    clientes.append(line.strip())
    # dedup preservando ordem
    seen, out = set(), []
    for c in clientes:
        if c not in seen:
            out.append(c); seen.add(c)
    return out

# ----------------- UI CONSOLE -----------------
def selecionar_departamento() -> Optional[str]:
    print("\nSelecione o DEPARTAMENTO:")
    for k in sorted(DEPARTAMENTOS_DISPONIVEIS, key=int):
        print(f"  {k}) {DEPARTAMENTOS_DISPONIVEIS[k]}")
    while True:
        esc = input(f"Escolha (1-{len(DEPARTAMENTOS_DISPONIVEIS)}): ").strip()
        if esc in DEPARTAMENTOS_DISPONIVEIS:
            return DEPARTAMENTOS_DISPONIVEIS[esc]
        print("Inválido.")

def selecionar_template() -> tuple[str, List[str]]:
    print("\nSelecione o TEMPLATE:")
    for k in sorted(TEMPLATES_DISPONIVEIS, key=int):
        print(f"  {k}) {TEMPLATES_DISPONIVEIS[k]['nome']}")
    while True:
        esc = input(f"Escolha (1-{len(TEMPLATES_DISPONIVEIS)}): ").strip()
        if esc in TEMPLATES_DISPONIVEIS:
            t = TEMPLATES_DISPONIVEIS[esc]
            return t["nome"], t["ancoras"]
        print("Inválido.")

# ----------------- DEPARTAMENTO -----------------
# trocar_departamento_zoho is provided by core.departamento now (imported above)

# ----------------- TEMPLATE -----------------
# selecionar_template_whatsapp is provided by core.whatsapp now (imported above)

# ----------------- LOOP PRINCIPAL -----------------
def processar_lote(caminho_lista: str, mensagem_padrao: Optional[str] = None):
    clientes = carregar_lista_clientes(caminho_lista)
    if not clientes:
        print("Lista vazia.")
        return

    dept = selecionar_departamento()
    if not dept:
        print("Sem departamento."); return

    tpl_nome, tpl_ancoras = selecionar_template()

    with DriverManager(headless=None) as driver:
        with LoginManager(driver) as ok:
            if not ok:
                raise SystemExit("Login falhou")

            # troca departamento
            if not trocar_departamento_zoho(driver, dept):
                raise SystemExit("Falhou trocar departamento")

            # percorre clientes
            for i, nome in enumerate(tqdm(clientes, desc="Clientes")):
                try:
                    if not buscar_e_abrir_cliente(driver, nome):
                        logger.warning(f"Cliente não encontrado: {nome}")
                        continue

                    # abre canal WhatsApp
                    if not abrir_canal_whatsapp(driver):
                        logger.error("Falha ao abrir canal WhatsApp")
                        continue

                    # seleciona template
                    if not selecionar_template_whatsapp(driver, tpl_nome, tpl_ancoras):
                        logger.error("Falha ao selecionar template")
                        continue

                    # envia (mensagem pode estar no template; aqui podemos enviar só para confirmar)
                    enviar_whatsapp(driver, mensagem=(mensagem_padrao or ""), anexos=None, abrir_canal=False, confirmar=True)

                except Exception as e:
                    logger.exception(f"Erro com '{nome}': {e}")
                    _screenshot_fallback(f"erro_{i}_{nome}", driver)

                # cooldown
                if (i + 1) % COOLDOWN_INTERVALO_CLIENTES == 0:
                    for s in tqdm(range(COOLDOWN_DURACAO_SEGUNDOS), desc="Cooldown"):
                        time.sleep(1)

if __name__ == "__main__":
    # ajuste aqui o arquivo de entrada e uma mensagem opcional
    processar_lote("clientes.xlsx", mensagem_padrao="")
