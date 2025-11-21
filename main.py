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
from tqdm import tqdm  # Barra de progresso

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    InvalidSessionIdException
)

# --- IMPORTAÇÕES MODULARES ---
try:
    from config.constants import TEMPLATES_DISPONIVEIS, DEPARTAMENTOS_DISPONIVEIS, URL_ZOHO_DESK
    COOLDOWN_INTERVALO_CLIENTES = 20
    COOLDOWN_DURACAO_SEGUNDOS = 60
except ImportError:
    # Fallback caso constants.py não tenha tudo
    from config.constants import *

# Core (Lógica Principal)
from core.login import fazer_login
from core.search import buscar_e_abrir_cliente
from core.departments import trocar_departamento_zoho
from core.processing import processar_pagina_cliente

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
# SISTEMA DE MEMÓRIA (EVITAR DUPLICIDADE)
# ==============================================================================
ARQUIVO_MEMORIA = "clientes_processados_memoria.json"

def carregar_memoria():
    """Carrega a lista de clientes que já foram processados com sucesso."""
    if os.path.exists(ARQUIVO_MEMORIA):
        try:
            with open(ARQUIVO_MEMORIA, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except Exception as e:
            logging.warning(f"Erro ao carregar memória: {e}. Iniciando vazia.")
            return set()
    return set()

def salvar_memoria(processados_set):
    """Salva a lista atualizada de processados no disco."""
    try:
        with open(ARQUIVO_MEMORIA, 'w', encoding='utf-8') as f:
            json.dump(list(processados_set), f)
    except Exception as e:
        logging.error(f"Erro ao salvar memória: {e}")

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

    # 3. Carregar Clientes e Filtrar pela Memória
    logging.info("Carregando lista de clientes...")
    todos_clientes = carregar_lista_clientes(args.arquivo) # Agora retorna dicionários completos!
    
    if not todos_clientes:
        logging.error("Lista de clientes vazia ou arquivo não encontrado.")
        return

    # Carrega memória
    ja_processados = carregar_memoria()
    logging.info(f"Memória carregada: {len(ja_processados)} clientes já processados anteriormente.")
    
    # Filtra quem falta fazer
    clientes_para_processar = []
    for cliente in todos_clientes:
        chave_unica = cliente.get('busca', '') # Usa o termo de busca (email, cnpj, etc) como chave
        if chave_unica in ja_processados:
            logging.debug(f"⏭️ Pulando '{chave_unica}' (já processado).")
        else:
            clientes_para_processar.append(cliente)
            
    logging.info(f"Clientes restantes para processar: {len(clientes_para_processar)}")

    if not clientes_para_processar:
        print("\n✅ Todos os clientes do arquivo já foram processados! Nada a fazer.")
        return

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

        pbar = tqdm(clientes_para_processar, desc="Processando", unit="cli")
        
        for i, cliente_dict in enumerate(pbar):
            # O termo que usamos para buscar (nome, cpf, email)
            termo_busca = cliente_dict.get('busca', 'Desconhecido')
            pbar.set_postfix_str(f"{termo_busca[:20]}...")
            
            # Cooldown (Pausa para evitar bloqueio)
            if i > 0 and i % COOLDOWN_INTERVALO_CLIENTES == 0:
                logging.info(f"Pausa de {COOLDOWN_DURACAO_SEGUNDOS}s para resfriamento...")
                time.sleep(COOLDOWN_DURACAO_SEGUNDOS)

            # Garante que estamos na home
            if "desk.zoho.com/agent/" not in driver.current_url:
                driver.get(URL_ZOHO_DESK)
                time.sleep(2)

            try:
                # Busca Inteligente (Passa o dicionário completo para validação cruzada)
                encontrado = buscar_e_abrir_cliente(driver, cliente_dict)
                
                if not encontrado:
                    nao_encontrados.append(termo_busca)
                    continue

                # Processa (Envia Mensagem)
                # Passamos apenas o termo_busca como string para o processamento (logs/screenshots)
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
                    # --- SALVA O SUCESSO IMEDIATAMENTE ---
                    ja_processados.add(termo_busca)
                    salvar_memoria(ja_processados)
                else:
                    erros.append(termo_busca)

            except Exception as e:
                logging.error(f"Erro ao processar '{termo_busca}': {e}")
                take_screenshot(driver, f"erro_loop_{termo_busca}")
                erros.append(termo_busca)
                # Tenta recuperar indo para home
                try: driver.get(URL_ZOHO_DESK) 
                except: pass

    except KeyboardInterrupt:
        logging.warning("Interrompido pelo usuário.")
    finally:
        # 7. Relatório Final
        imprimir_relatorio(inicio, sucesso, nao_encontrados, erros, args.arquivo)
        
        if args.keep_open:
            print("\nNavegador mantido aberto. Feche manualmente.")
        else:
            driver.quit()

# ==============================================================================
# FUNÇÕES AUXILIARES DO MENU
# ==============================================================================
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
    
    # Dept
    print("Departamentos:")
    for k in sorted(DEPARTAMENTOS_DISPONIVEIS.keys(), key=int):
        print(f" {k}) {DEPARTAMENTOS_DISPONIVEIS[k]}")
    d = input("Escolha o Dept (Número): ").strip()
    dept = DEPARTAMENTOS_DISPONIVEIS.get(d)
    
    # Template
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
    
    # Salva CSV simples
    nome_csv = f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    with open(nome_csv, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(["Status", "Cliente"])
        for c in sucesso: writer.writerow(["SUCESSO", c])
        for c in nao_enc: writer.writerow(["NAO_ENCONTRADO", c])
        for c in erros: writer.writerow(["ERRO", c])
    print(f"\nRelatório salvo em: {nome_csv}")
    print(f"Memória de processados salva em: {ARQUIVO_MEMORIA}")
    print("="*40)

if __name__ == "__main__":
    main()