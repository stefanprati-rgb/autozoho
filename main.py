# Arquivo: main.py
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
from selenium.webdriver import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    TimeoutException,
    InvalidSessionIdException
)

# --- IMPORTAÇÕES MODULARES ---
try:
    from config.constants import TEMPLATES_DISPONIVEIS, DEPARTAMENTOS_DISPONIVEIS, URL_ZOHO_DESK
    COOLDOWN_INTERVALO_CLIENTES = 20
    COOLDOWN_DURACAO_SEGUNDOS = 60
    
    # --- CONFIGURAÇÃO DE VELOCIDADE ---
    DELAY_DIGITACAO_CURTA = 0.005
    DELAY_DIGITACAO_MEDIA = 0.010
    DELAY_DIGITACAO_LONGA = 0.015
    
except ImportError:
    from config.constants import *
    DELAY_DIGITACAO_CURTA = 0.005
    DELAY_DIGITACAO_MEDIA = 0.010
    DELAY_DIGITACAO_LONGA = 0.015

# Core (Lógica Principal)
from core.login import fazer_login
from core.search import buscar_e_abrir_cliente
from core.departments import trocar_departamento_zoho
from core.processing import processar_pagina_cliente, fechar_modal_robusto
from core.messaging import fechar_ui_flutuante

# Utils (Ferramentas)
from utils.files import carregar_lista_clientes
from utils.webdriver import iniciar_driver
from utils.screenshots import take_screenshot
from utils.session import (
    gerar_hash_arquivo, gerar_session_id,
    sessao_existe, carregar_sessao, criar_sessao,
    salvar_progresso, cliente_ja_processado,
    apagar_sessao, resumo_sessao, contar_processados
)

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
    parser.add_argument("--log", default=os.path.join("logging", "automacao.log"), help="Arquivo de log.")
    parser.add_argument("--dry-run", action="store_true", help="Modo simulação (não envia mensagem).")
    parser.add_argument("--template", help="Número ou nome do template.")
    parser.add_argument("--departamento", help="Número ou nome do departamento.")
    parser.add_argument("--keep-open", action="store_true", default=True, help="Manter navegador aberto no final.")
    parser.add_argument("--resume", action="store_true", help="Retomar sessão anterior automaticamente.")
    parser.add_argument("--force", action="store_true", help="Forçar nova sessão, ignorando progresso anterior.")

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
    logging.info("Carregando lista de clientes...")
    todos_clientes = carregar_lista_clientes(args.arquivo)
    
    if not todos_clientes:
        logging.error("Lista de clientes vazia ou arquivo não encontrado.")
        return

    # === SISTEMA DE SESSÕES (PERSISTENTE) ===
    # Calcula hash do arquivo para identificar mudanças no conteúdo
    hash_arquivo = gerar_hash_arquivo(args.arquivo)
    session_id = gerar_session_id(hash_arquivo, NOME_TEMPLATE, NOME_DEPARTAMENTO)
    
    logging.info(f"Session ID: {session_id}")
    logging.info(f"Total carregado do arquivo: {len(todos_clientes)}")
    
    # Verifica se existe sessão anterior com mesma combinação
    retomar_sessao = False
    
    if sessao_existe(session_id):
        if args.force:
            # Flag --force: apaga sessão e recomeça
            print("\n⚠️  Flag --force detectada. Apagando sessão anterior...")
            apagar_sessao(session_id)
            logging.info("Sessão anterior apagada por --force")
        elif args.resume:
            # Flag --resume: retoma automaticamente
            retomar_sessao = True
            print(resumo_sessao(session_id))
            print("\n▶️  Flag --resume detectada. Retomando automaticamente...")
            logging.info("Retomando sessão por --resume")
        else:
            # Sem flags: pergunta ao usuário
            print(resumo_sessao(session_id))
            resposta = input("\n❓ Deseja RETOMAR esta sessão? (S=Retomar / N=Recomeçar): ").strip().upper()
            
            if resposta == 'S':
                retomar_sessao = True
                logging.info("Usuário optou por RETOMAR sessão")
            else:
                apagar_sessao(session_id)
                logging.info("Usuário optou por RECOMEÇAR - sessão apagada")
    
    # Cria nova sessão se não existe ou se for recomeçar
    if not sessao_existe(session_id):
        criar_sessao(session_id, args.arquivo, hash_arquivo, 
                     NOME_TEMPLATE, NOME_DEPARTAMENTO, len(todos_clientes))
    
    # Controle de duplicatas dentro da sessão atual (memória)
    vistos_na_sessao = set()

    # 4. Iniciar Navegador e Login
    
    # Inicializa listas de relatório antes de qualquer possível falha
    sucesso = []
    nao_encontrados = []
    erros = []
    duplicados_ignorados = []
    
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
        pbar = tqdm(todos_clientes, desc="Processando", unit="cli")
        
        for i, cliente_dict in enumerate(pbar):
            
            # === LIMPEZA DE SEGURANÇA ENTRE CLIENTES ===
            try:
                # Tenta fechar modal do WhatsApp se estiver aberto (erro anterior)
                fechar_modal_robusto(driver, "limpeza_entre_clientes", tentativas=2)
                # Fecha qualquer overlay adicional (ESC)
                fechar_ui_flutuante(driver)
                time.sleep(0.3)
            except Exception as e_limpar:
                logging.debug(f"Limpeza de segurança: {e_limpar}")
            # ============================

            termo_busca = cliente_dict.get('busca', 'Desconhecido')
            tipo_busca = cliente_dict.get('tipo_busca', 'auto')
            logging.info(f"Processando Cliente: '{termo_busca}' (Método: {tipo_busca.upper()})")
            
            # --- VERIFICAÇÃO DE DUPLICIDADE NA SESSÃO ---
            if termo_busca in vistos_na_sessao:
                pbar.set_postfix_str(f"⏭️ Duplicado: {termo_busca[:15]}")
                duplicados_ignorados.append(termo_busca)
                continue
            
            # --- VERIFICAÇÃO DE CLIENTE JÁ PROCESSADO (SESSÃO PERSISTENTE) ---
            if retomar_sessao and cliente_ja_processado(session_id, termo_busca):
                pbar.set_postfix_str(f"✅ Já processado: {termo_busca[:15]}")
                logging.debug(f"Pulando cliente já processado: {termo_busca}")
                continue
            
            # Marca como visto AGORA
            vistos_na_sessao.add(termo_busca)
            
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
                # Busca Inteligente
                encontrado = buscar_e_abrir_cliente(driver, cliente_dict)
                
                if not encontrado:
                    nao_encontrados.append(termo_busca)
                    salvar_progresso(session_id, termo_busca, "NAO_ENCONTRADO")
                    continue

                # Processa (Envia Mensagem)
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
                    salvar_progresso(session_id, termo_busca, "SUCESSO")
                else:
                    erros.append(termo_busca)
                    salvar_progresso(session_id, termo_busca, "ERRO")

            except Exception as e:
                logging.error(f"Erro ao processar '{termo_busca}': {e}")
                take_screenshot(driver, f"erro_loop_{termo_busca}")
                erros.append(termo_busca)
                salvar_progresso(session_id, termo_busca, "ERRO")
                # Tenta recuperar indo para home
                try: driver.get(URL_ZOHO_DESK) 
                except: pass

    except KeyboardInterrupt:
        logging.warning("Interrompido pelo usuário.")
    finally:
        # 7. Relatório Final
        imprimir_relatorio(inicio, sucesso, nao_encontrados, erros, duplicados_ignorados, args.arquivo)
        
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

def imprimir_relatorio(inicio, sucesso, nao_enc, erros, duplicados, arquivo):
    total = len(sucesso) + len(nao_enc) + len(erros) + len(duplicados)
    print("\n" + "="*40)
    print("RESUMO FINAL DA SESSÃO")
    print(f"Arquivo: {arquivo}")
    print(f"Total Processado: {total}")
    print(f"✅ Sucesso: {len(sucesso)}")
    print(f"🔍 Não Encontrados: {len(nao_enc)}")
    print(f"⏭️ Duplicados (Pulados): {len(duplicados)}")
    print(f"❌ Erros: {len(erros)}")
    
    # Salva CSV simples
    os.makedirs("reports", exist_ok=True)
    nome_csv = os.path.join("reports", f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M')}.csv")
    with open(nome_csv, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(["Status", "Cliente"])
        for c in sucesso: writer.writerow(["SUCESSO", c])
        for c in nao_enc: writer.writerow(["NAO_ENCONTRADO", c])
        for c in erros: writer.writerow(["ERRO", c])
        for c in duplicados: writer.writerow(["DUPLICADO_SESSAO", c])
    print(f"\nRelatório salvo em: {nome_csv}")
    print("="*40)

if __name__ == "__main__":
    main()