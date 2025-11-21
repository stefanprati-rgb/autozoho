# -*- coding: utf-8 -*-
import os
import sys
import re
import csv
import time
import argparse
import logging
from datetime import datetime
from tqdm import tqdm  # Barra de progresso

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    InvalidSessionIdException
)

# --- IMPORTAÇÕES MODULARES CORRIGIDAS ---
try:
    from config.constants import TEMPLATES_DISPONIVEIS, DEPARTAMENTOS_DISPONIVEIS, URL_ZOHO_DESK
    COOLDOWN_INTERVALO_CLIENTES = 20
    COOLDOWN_DURACAO_SEGUNDOS = 60
except ImportError:
    from config.constants import *

# Core (Lógica Principal)
from core.login import fazer_login
from core.search import buscar_e_abrir_cliente
from core.processing import processar_pagina_cliente

# CORREÇÃO: Importar a troca de departamento do sítio certo
from core.departments import trocar_departamento_zoho 

# Utils (Ferramentas)
from utils.files import carregar_lista_clientes
from utils.webdriver import iniciar_driver
from utils.screenshots import take_screenshot

# Logging
try:
    from utils.reports import setup_logging, dump_browser_logs
except ImportError:
    def setup_logging(level, file):
        logging.basicConfig(level=level, filename=file, format='%(asctime)s - %(levelname)s - %(message)s')
    def dump_browser_logs(driver): pass

# ==============================================================================
# FUNÇÃO PRINCIPAL
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="Automação de envio de mensagens via WhatsApp no Zoho Desk.")

    parser.add_argument("-a", "--arquivo", required=True, help="Caminho para o arquivo .xlsx ou .csv com a lista de clientes.")
    parser.add_argument("-l", "--loglevel", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="Nível de log.")
    parser.add_argument("--log", default="automacao.log", help="Arquivo de log.")
    parser.add_argument("--dry-run", action="store_true", help="Modo simulação (não envia mensagem).")
    parser.add_argument("--template", help="Número ou nome do template.")
    parser.add_argument("--departamento", help="Número ou nome do departamento.")
    parser.add_argument("--keep-open", action="store_true", default=True, help="Manter navegador aberto no final.")

    args = parser.parse_args()

    # 1. Configuração
    setup_logging(args.loglevel, args.log)
    inicio = datetime.now()
    logging.info(f"Iniciando automação em: {inicio}")

    if args.dry_run:
        logging.warning(">>> MODO DRY-RUN (SIMULAÇÃO) ATIVADO <<<")

    # 2. Definição de Template e Departamento
    global NOME_TEMPLATE, ANCORAS, NOME_DEPARTAMENTO
    
    if args.template and args.departamento:
        NOME_TEMPLATE, ANCORAS = resolver_template(args.template)
        NOME_DEPARTAMENTO = resolver_departamento(args.departamento)
    else:
        NOME_TEMPLATE, ANCORAS, NOME_DEPARTAMENTO = menu_principal()

    if not NOME_TEMPLATE or not NOME_DEPARTAMENTO:
        logging.error("Configuração incompleta. Encerrando.")
        return

    logging.info(f"Template: {NOME_TEMPLATE} | Departamento: {NOME_DEPARTAMENTO}")

    # 3. Carregar Clientes
    lista_clientes = carregar_lista_clientes(args.arquivo)
    if not lista_clientes:
        logging.error("Lista de clientes vazia ou arquivo não encontrado.")
        return
    logging.info(f"Carregados {len(lista_clientes)} clientes para processar.")

    # 4. Iniciar Navegador e Login
    driver = iniciar_driver()
    if not driver:
        return

    try:
        if not fazer_login(driver):
            logging.critical("Falha no login. Encerrando.")
            return

        # 5. Selecionar Departamento Inicial
        if not trocar_departamento_zoho(driver, NOME_DEPARTAMENTO):
            logging.critical("Falha ao selecionar departamento inicial.")
            return

        # 6. Loop de Processamento
        sucesso = []
        nao_encontrados = []
        erros = []

        pbar = tqdm(lista_clientes, desc="Processando", unit="cli")
        
        for i, cliente in enumerate(pbar):
            pbar.set_postfix_str(f"{cliente[:20]}...")
            
            if i > 0 and i % COOLDOWN_INTERVALO_CLIENTES == 0:
                logging.info(f"Pausa de {COOLDOWN_DURACAO_SEGUNDOS}s para resfriamento...")
                time.sleep(COOLDOWN_DURACAO_SEGUNDOS)

            # Garante que estamos na home
            if "desk.zoho.com/agent/" not in driver.current_url:
                driver.get(URL_ZOHO_DESK)
                time.sleep(2)

            try:
                # Busca
                encontrado = buscar_e_abrir_cliente(driver, cliente)
                if not encontrado:
                    nao_encontrados.append(cliente)
                    continue

                # Processa
                resultado = processar_pagina_cliente(
                    driver=driver,
                    nome_cliente=cliente,
                    departamento=NOME_DEPARTAMENTO,
                    template_nome=NOME_TEMPLATE,
                    ancoras=ANCORAS,
                    dry_run=args.dry_run
                )

                if resultado:
                    sucesso.append(cliente)
                else:
                    erros.append(cliente)

            except Exception as e:
                logging.error(f"Erro ao processar '{cliente}': {e}")
                take_screenshot(driver, f"erro_loop_{cliente}")
                erros.append(cliente)
                try: driver.get(URL_ZOHO_DESK) 
                except: pass

    except KeyboardInterrupt:
        logging.warning("Interrompido pelo usuário.")
    finally:
        imprimir_relatorio(inicio, sucesso, nao_encontrados, erros, args.arquivo)
        if args.keep_open:
            print("\nNavegador mantido aberto. Feche manualmente.")
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
    print("\n=== CONFIGURAÇÃO ===")
    print("Departamentos:")
    for k in sorted(DEPARTAMENTOS_DISPONIVEIS.keys(), key=int):
        print(f" {k}) {DEPARTAMENTOS_DISPONIVEIS[k]}")
    d = input("Escolha o Dept (Número): ").strip()
    dept = DEPARTAMENTOS_DISPONIVEIS.get(d)
    
    print("\nTemplates:")
    for k in sorted(TEMPLATES_DISPONIVEIS.keys(), key=int):
        print(f" {k}) {TEMPLATES_DISPONIVEIS[k]['nome']}")
    t = input("Escolha o Template (Número): ").strip()
    temp_data = TEMPLATES_DISPONIVEIS.get(t)
    
    if dept and temp_data:
        return temp_data["nome"], temp_data["ancoras"], dept
    return None, None, None

def imprimir_relatorio(inicio, sucesso, nao_enc, erros, arquivo):
    total = len(sucesso) + len(nao_enc) + len(erros)
    print("\n" + "="*40)
    print("RESUMO FINAL")
    print(f"Arquivo: {arquivo}")
    print(f"Total Processado: {total}")
    print(f"✅ Sucesso: {len(sucesso)}")
    print(f"🔍 Não Encontrados: {len(nao_enc)}")
    print(f"❌ Erros: {len(erros)}")
    
    nome_csv = f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    with open(nome_csv, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(["Status", "Cliente"])
        for c in sucesso: writer.writerow(["SUCESSO", c])
        for c in nao_enc: writer.writerow(["NAO_ENCONTRADO", c])
        for c in erros: writer.writerow(["ERRO", c])
    print(f"\nRelatório salvo em: {nome_csv}")
    print("="*40)

if __name__ == "__main__":
    main()