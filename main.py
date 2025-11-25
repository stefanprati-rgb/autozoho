# -*- coding: utf-8 -*-
import os
import sys
import re
import csv
import time
import json
import argparse
import logging
from datetime import datetime
from tqdm import tqdm

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    TimeoutException,
    InvalidSessionIdException
)

# --- TENTATIVA DE IMPORTAR COLORAMA (PARA CORES) ---
try:
    import colorama
    from colorama import Fore, Style
    colorama.init(autoreset=True)
    USE_COLORS = True
except ImportError:
    USE_COLORS = False

# --- IMPORTAÇÕES MODULARES ---
try:
    from config.constants import TEMPLATES_DISPONIVEIS, DEPARTAMENTOS_DISPONIVEIS, URL_ZOHO_DESK
    COOLDOWN_INTERVALO_CLIENTES = 20
    COOLDOWN_DURACAO_SEGUNDOS = 60
    DELAY_DIGITACAO_CURTA = 0.005
    DELAY_DIGITACAO_MEDIA = 0.010
    DELAY_DIGITACAO_LONGA = 0.015
except ImportError:
    from config.constants import *
    DELAY_DIGITACAO_CURTA = 0.005
    DELAY_DIGITACAO_MEDIA = 0.010
    DELAY_DIGITACAO_LONGA = 0.015

from core.login import fazer_login
from core.search import buscar_e_abrir_cliente
from core.departments import trocar_departamento_zoho
from core.processing import processar_pagina_cliente
from utils.files import carregar_lista_clientes
from utils.webdriver import iniciar_driver
from utils.screenshots import take_screenshot

# --- CONFIGURAÇÃO DE LOGGING VISUAL ---
class ColoredFormatter(logging.Formatter):
    def format(self, record):
        if not USE_COLORS:
            return super().format(record)
        
        # Definição de cores e ícones
        if record.levelno == logging.INFO:
            prefix = f"{Fore.GREEN}ℹ️ {Style.RESET_ALL}"
            msg = f"{Fore.LIGHTWHITE_EX}{record.msg}{Style.RESET_ALL}"
        elif record.levelno == logging.WARNING:
            prefix = f"{Fore.YELLOW}⚠️ {Style.RESET_ALL}"
            msg = f"{Fore.YELLOW}{record.msg}{Style.RESET_ALL}"
        elif record.levelno == logging.ERROR:
            prefix = f"{Fore.RED}❌ {Style.RESET_ALL}"
            msg = f"{Fore.RED}{record.msg}{Style.RESET_ALL}"
        elif record.levelno == logging.CRITICAL:
            prefix = f"{Fore.RED}{Style.BRIGHT}🔥 {Style.RESET_ALL}"
            msg = f"{Fore.RED}{Style.BRIGHT}{record.msg}{Style.RESET_ALL}"
        elif record.levelno == logging.DEBUG:
            prefix = f"{Fore.CYAN}🐛 {Style.RESET_ALL}"
            msg = f"{Fore.CYAN}{record.msg}{Style.RESET_ALL}"
        else:
            prefix = ""
            msg = record.msg
            
        return f"{prefix} {msg}"

def setup_logging_visual(loglevel, logfile):
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, loglevel.upper()))
    root_logger.handlers = [] # Limpa handlers antigos

    # 1. Console Handler (Limpo e Colorido)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(ColoredFormatter())
    # Define nível do console um pouco mais alto para esconder ruído se necessário
    console_level = getattr(logging, loglevel.upper())
    console_handler.setLevel(console_level)
    root_logger.addHandler(console_handler)

    # 2. File Handler (Detalhado com datas para auditoria)
    if logfile:
        file_handler = logging.FileHandler(logfile, encoding='utf-8')
        file_fmt = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(file_fmt)
        root_logger.addHandler(file_handler)
        
    # Silencia logs chatos de bibliotecas externas
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("WDM").setLevel(logging.WARNING)

def dump_browser_logs(driver): pass # Placeholder

# ==============================================================================
# SISTEMA DE MEMÓRIA
# ==============================================================================
ARQUIVO_MEMORIA = "clientes_processados_memoria.json"

def carregar_memoria():
    if os.path.exists(ARQUIVO_MEMORIA):
        try:
            with open(ARQUIVO_MEMORIA, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except: return set()
    return set()

def salvar_memoria(processados_set):
    try:
        with open(ARQUIVO_MEMORIA, 'w', encoding='utf-8') as f:
            json.dump(list(processados_set), f)
    except: pass

# ==============================================================================
# FUNÇÃO PRINCIPAL
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="Automação Zoho Desk")
    parser.add_argument("-a", "--arquivo", required=True, help="Arquivo de clientes")
    parser.add_argument("-l", "--loglevel", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="Nível de log")
    parser.add_argument("--log", default="automacao.log", help="Arquivo de log")
    parser.add_argument("--dry-run", action="store_true", help="Modo simulação")
    parser.add_argument("--template", help="Nome do template")
    parser.add_argument("--departamento", help="Nome do departamento")
    parser.add_argument("--keep-open", action="store_true", default=True, help="Manter navegador aberto")

    args = parser.parse_args()

    setup_logging_visual(args.loglevel, args.log)
    
    print("\n" + "="*60)
    print(f"🚀 INICIANDO AUTOMAÇÃO ZOHO DESK")
    print(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("="*60 + "\n")

    if args.dry_run:
        logging.warning("MODO DRY-RUN ATIVADO (Nenhuma mensagem será enviada)")

    global NOME_TEMPLATE, ANCORAS, NOME_DEPARTAMENTO
    
    if args.template and args.departamento:
        NOME_TEMPLATE, ANCORAS = resolver_template(args.template)
        NOME_DEPARTAMENTO = resolver_departamento(args.departamento)
    else:
        NOME_TEMPLATE, ANCORAS, NOME_DEPARTAMENTO = menu_principal()

    if not NOME_TEMPLATE or not NOME_DEPARTAMENTO:
        logging.error("Configuração incompleta. Encerrando.")
        return

    logging.info(f"Configuração: {NOME_DEPARTAMENTO}  >>  {NOME_TEMPLATE}")

    todos_clientes = carregar_lista_clientes(args.arquivo)
    if not todos_clientes:
        logging.error("Lista de clientes vazia.")
        return

    ja_processados = carregar_memoria()
    clientes_para_processar = [c for c in todos_clientes if c.get('busca', '') not in ja_processados]
    
    logging.info(f"Total: {len(todos_clientes)} | Já feitos: {len(ja_processados)} | A fazer: {len(clientes_para_processar)}")

    if not clientes_para_processar:
        logging.info("Todos os clientes já foram processados! 🎉")
        return

    driver = iniciar_driver()
    if not driver: return

    try:
        if not fazer_login(driver):
            logging.critical("Login falhou.")
            return

        if not trocar_departamento_zoho(driver, NOME_DEPARTAMENTO):
            logging.critical("Falha ao selecionar departamento inicial.")
            return

        sucesso = []
        nao_encontrados = []
        erros = []

        # Barra de progresso mais limpa
        pbar = tqdm(clientes_para_processar, desc="Progresso", unit="cli", ncols=80, bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}")
        
        for i, cliente_dict in enumerate(pbar):
            # Limpa logs anteriores da tela do tqdm
            
            termo_busca = cliente_dict.get('busca', 'Desconhecido')
            pbar.set_description(f"Processando: {termo_busca[:20]:<20}")
            
            # Limpeza de tela (modais perdidos)
            try:
                ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            except: pass

            # Cooldown
            if i > 0 and i % COOLDOWN_INTERVALO_CLIENTES == 0:
                logging.info(f"❄️ Pausa de {COOLDOWN_DURACAO_SEGUNDOS}s para resfriamento...")
                time.sleep(COOLDOWN_DURACAO_SEGUNDOS)

            if "desk.zoho.com/agent/" not in driver.current_url:
                driver.get(URL_ZOHO_DESK)
                time.sleep(2)

            try:
                encontrado = buscar_e_abrir_cliente(driver, cliente_dict)
                
                if not encontrado:
                    nao_encontrados.append(termo_busca)
                    continue

                resultado = processar_pagina_cliente(
                    driver=driver,
                    nome_cliente=termo_busca, 
                    departamento=NOME_DEPARTAMENTO,
                    template_nome=NOME_TEMPLATE,
                    ancoras=ANCORAS,
                    dry_run=args.dry_run
                )

                if resultado:
                    sucesso.append(termo_busca)
                    ja_processados.add(termo_busca)
                    salvar_memoria(ja_processados)
                else:
                    erros.append(termo_busca)

            except Exception as e:
                logging.error(f"Erro processando '{termo_busca}': {e}")
                take_screenshot(driver, f"erro_loop_{termo_busca}")
                erros.append(termo_busca)
                try: driver.get(URL_ZOHO_DESK) 
                except: pass

    except KeyboardInterrupt:
        print("\n🛑 Interrompido pelo usuário.")
    finally:
        imprimir_relatorio_limpo(sucesso, nao_encontrados, erros, args.arquivo)
        
        if args.keep_open:
            print("\n🌐 Navegador aberto. Pode fechar quando quiser.")
        else:
            driver.quit()

def resolver_template(entrada):
    if entrada in TEMPLATES_DISPONIVEIS:
        return TEMPLATES_DISPONIVEIS[entrada]["nome"], TEMPLATES_DISPONIVEIS[entrada]["ancoras"]
    for k, v in TEMPLATES_DISPONIVEIS.items():
        if v["nome"].lower() == entrada.lower():
            return v["nome"], v["ancoras"]
    return None, None

def resolver_departamento(entrada):
    if entrada in DEPARTAMENTOS_DISPONIVEIS:
        return DEPARTAMENTOS_DISPONIVEIS[entrada]
    for k, v in DEPARTAMENTOS_DISPONIVEIS.items():
        if v.lower() == entrada.lower():
            return v
    return None

def menu_principal():
    print("\n--- CONFIGURAÇÃO ---")
    print("Departamentos:")
    for k in sorted(DEPARTAMENTOS_DISPONIVEIS.keys(), key=int):
        print(f" {k}) {DEPARTAMENTOS_DISPONIVEIS[k]}")
    d = input("Escolha o Dept: ").strip()
    dept = DEPARTAMENTOS_DISPONIVEIS.get(d)
    
    print("\nTemplates:")
    for k in sorted(TEMPLATES_DISPONIVEIS.keys(), key=int):
        print(f" {k}) {TEMPLATES_DISPONIVEIS[k]['nome']}")
    t = input("Escolha o Template: ").strip()
    temp_data = TEMPLATES_DISPONIVEIS.get(t)
    
    if dept and temp_data:
        return temp_data["nome"], temp_data["ancoras"], dept
    return None, None, None

def imprimir_relatorio_limpo(sucesso, nao_enc, erros, arquivo):
    print("\n" + "="*60)
    print(f"📊 RELATÓRIO FINAL")
    print("="*60)
    print(f"Arquivo: {os.path.basename(arquivo)}")
    print(f"✅ Sucesso:        {len(sucesso)}")
    print(f"🔍 Não Encontrados: {len(nao_enc)}")
    print(f"❌ Erros:           {len(erros)}")
    print("-" * 60)
    
    nome_csv = f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    with open(nome_csv, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(["Status", "Cliente"])
        for c in sucesso: writer.writerow(["SUCESSO", c])
        for c in nao_enc: writer.writerow(["NAO_ENCONTRADO", c])
        for c in erros: writer.writerow(["ERRO", c])
    
    print(f"📄 Detalhes salvos em: {nome_csv}")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()