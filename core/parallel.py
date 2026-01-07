# -*- coding: utf-8 -*-
"""
Módulo de execução paralela do AutoZoho.
Gerencia múltiplos workers para envio de mensagens em paralelo.
"""

import os
import sys
import time
import logging
import csv
from datetime import datetime
from multiprocessing import Process, Queue, Manager, current_process
from typing import List, Dict, Any, Optional
from selenium.common.exceptions import WebDriverException

# Imports do projeto
from utils.webdriver import iniciar_driver
from utils.files import carregar_lista_clientes, dividir_lista_em_blocos
from utils.session import salvar_progresso
import utils.session as session
from core.login import fazer_login
from core.departments import trocar_departamento_zoho
from core.search import buscar_e_abrir_cliente
from core.processing import processar_pagina_cliente, fechar_modal_robusto
from core.messaging import fechar_ui_flutuante
from config.constants import URL_ZOHO_DESK

# Configurações de cooldown
COOLDOWN_INTERVALO_CLIENTES = 20
COOLDOWN_DURACAO_SEGUNDOS = 60

def calcular_workers_ideais(total_clientes: int, max_workers: int = 4) -> int:
    """
    Retorna número ideal de workers baseado no tamanho da lista.
    
    | Clientes | Workers |
    |----------|---------|
    | 1-20     | 1       |
    | 21-60    | 2       |
    | 61-120   | 3       |
    | 121+     | 4       |
    """
    if total_clientes <= 20:
        return 1
    elif total_clientes <= 60:
        return 2
    elif total_clientes <= 120:
        return 3
    else:
        return min(4, max_workers)


def worker_process(
    worker_id: int,
    bloco_clientes: List[Dict],
    config: Dict[str, Any],
    resultado_queue: Queue,
    login_sync_queue: Optional[Queue] = None
):
    """
    Processo worker que executa o envio para um bloco de clientes.
    
    Args:
        worker_id: Identificador do worker (1, 2, 3, 4)
        bloco_clientes: Lista de clientes para este worker processar
        config: Configurações (template, departamento, etc)
        resultado_queue: Fila para enviar resultados ao processo principal
        login_sync_queue: Fila para sincronizar logins sequenciais
    """
    # Setup de logging para este worker
    logging.basicConfig(
        level=logging.INFO,
        format=f'[Worker {worker_id}] %(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'automacao_worker_{worker_id}.log', encoding='utf-8'),
        ]
    )
    
    # Handler específico para o console com nível warning
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(logging.Formatter(f'[Worker {worker_id}] %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(console_handler)
    
    logger = logging.getLogger(f'Worker{worker_id}')
    logger.info(f"Iniciando com {len(bloco_clientes)} clientes")
    
    # Resultados locais
    resultados = {
        'worker_id': worker_id,
        'sucesso': [],
        'nao_encontrados': [],
        'erros': [],
        'total': len(bloco_clientes)
    }
    
    try:
        # Inicia driver com posicionamento baseado no worker_id
        driver = iniciar_driver(instance_id=worker_id)
        if not driver:
            logger.error("Falha ao iniciar driver")
            resultado_queue.put(resultados)
            return
        
        # Garante que o driver está funcionando navegando para uma URL inicial
        try:
            driver.get("about:blank")
            time.sleep(1)
        except Exception as e:
            logger.error(f"Driver não está respondendo: {e}")
            resultado_queue.put(resultados)
            return
        
        # Se temos sincronização de login, aguarda nossa vez
        if login_sync_queue and worker_id > 1:
            logger.info("Aguardando workers anteriores fazerem login...")
            while True:
                try:
                    ultimo_logado = login_sync_queue.get(timeout=300)  # 5 min timeout
                    if ultimo_logado >= worker_id - 1:
                        login_sync_queue.put(ultimo_logado)  # Devolve para outros workers
                        break
                except:
                    logger.warning("Timeout aguardando login anterior, tentando mesmo assim...")
                    break
        
        # Login
        logger.info("Iniciando login...")
        if not fazer_login(driver):
            logger.critical("Falha no login!")
            driver.quit()
            resultado_queue.put(resultados)
            return
        
        # Sinaliza que este worker logou
        if login_sync_queue:
            try:
                login_sync_queue.get_nowait()
            except:
                pass
            login_sync_queue.put(worker_id)
            logger.info(f"Login concluído, sinalizando worker {worker_id}")
        
        # Troca departamento
        dept_nome = config.get('departamento', 'Era Verde Energia')
        if not trocar_departamento_zoho(driver, dept_nome):
            logger.error("Falha ao trocar departamento")
            driver.quit()
            resultado_queue.put(resultados)
            return
        
        template_nome = config.get('template_nome')
        ancoras = config.get('ancoras', [])
        dry_run = config.get('dry_run', False)
        session_id = config.get('session_id')  # Para salvar progresso
        
        # Loop de processamento
        i = 0
        while i < len(bloco_clientes):
            cliente_dict = bloco_clientes[i]
            termo_busca = cliente_dict.get('busca', 'Desconhecido')
            
            # --- CHECK DE SESSÃO ---
            if session_id:
                status_anterior = session.obter_status_cliente(session_id, termo_busca)
                if status_anterior in ["SUCESSO", "NAO_ENCONTRADO"]:
                    logger.info(f"[{i+1}/{len(bloco_clientes)}] Pulando (já processado): {termo_busca} ({status_anterior})")
                    i += 1
                    continue
            
            logger.info(f"[{i+1}/{len(bloco_clientes)}] Processando: {termo_busca}")
            
            try:
                # Recuperação do driver se necessário
                if driver is None:
                    logger.warning("Driver nulo, tentando recuperar...")
                    raise WebDriverException("Driver nulo")

                # Limpeza de segurança (somente se driver estiver ok)
                try:
                    fechar_modal_robusto(driver, "limpeza", tentativas=2)
                    fechar_ui_flutuante(driver)
                    time.sleep(0.3)
                except Exception as e:
                    logger.warning(f"Erro na limpeza prévia (ignorado): {e}")
            
                # Cooldown
                if i > 0 and i % COOLDOWN_INTERVALO_CLIENTES == 0:
                    logger.info(f"Pausa de {COOLDOWN_DURACAO_SEGUNDOS}s...")
                    time.sleep(COOLDOWN_DURACAO_SEGUNDOS)
                
                # Garante home
                if "desk.zoho.com/agent/" not in driver.current_url:
                    driver.get(URL_ZOHO_DESK)
                    time.sleep(2)
                
                # Busca
                encontrado = buscar_e_abrir_cliente(driver, cliente_dict)
                
                if not encontrado:
                    resultados['nao_encontrados'].append(termo_busca)
                    if session_id:
                        salvar_progresso(session_id, termo_busca, "NAO_ENCONTRADO")
                    i += 1
                    continue
                
                # Processamento
                resultado = processar_pagina_cliente(
                    driver=driver,
                    nome_cliente=termo_busca,
                    departamento=dept_nome,
                    template_nome=template_nome,
                    ancoras=ancoras,
                    dry_run=dry_run
                )
                
                if resultado['sucesso']:
                    resultados['sucesso'].append(termo_busca)
                    if session_id:
                        salvar_progresso(session_id, termo_busca, "SUCESSO")
                else:
                    resultados['erros'].append({'cliente': termo_busca, 'erro': resultado['erro']})
                    if session_id:
                        salvar_progresso(session_id, termo_busca, "ERRO")
                
                # Sucesso! Avança para o próximo
                i += 1
                
            except (WebDriverException, ConnectionError, Exception) as e:
                # Verifica se é erro fatal de conexão/driver
                msg_erro = str(e).lower()
                eh_erro_conexao = "connection" in msg_erro or "refused" in msg_erro or "reset" in msg_erro or "closed" in msg_erro or "invalid session" in msg_erro
                
                if not eh_erro_conexao and not isinstance(e, (WebDriverException, ConnectionError)):
                    # Erro genérico de lógica, loga e avança
                    logger.error(f"Erro genérico no cliente {termo_busca}: {e}")
                    if session_id:
                        salvar_progresso(session_id, termo_busca, "ERRO_GENERICO")
                    
                    if isinstance(e, dict):
                         resultados['erros'].append({'cliente': termo_busca, 'erro': str(e)})
                    else:
                         resultados['erros'].append({'cliente': termo_busca, 'erro': str(e)})
                    i += 1
                    continue
                
                # Se for erro de conexão/driver, TENTA RECUPERAR
                logger.critical(f"ERRO DE CONEXÃO/DRIVER DETECTADO: {e}")
                logger.info("Tentando reiniciar o navegador e recuperar o worker...")
                
                try:
                    if driver:
                        driver.quit()
                except:
                    pass
                
                driver = None
                time.sleep(5) 
                
                # Tenta reinicializar até 3 vezes
                recuperado = False
                for tentativa_rec in range(3):
                    try:
                        logger.info(f"Tentativa de recuperação {tentativa_rec + 1}/3...")
                        driver = iniciar_driver(instance_id=worker_id)
                        if driver:
                            driver.get("about:blank")
                            time.sleep(1)
                            if fazer_login(driver):
                                if trocar_departamento_zoho(driver, dept_nome):
                                    recuperado = True
                                    logger.info("WORKER RECUPERADO COM SUCESSO!")
                                    break
                    except Exception as ex_rec:
                        logger.error(f"Falha na tentativa de recuperação {tentativa_rec + 1}: {ex_rec}")
                        if driver:
                            try: driver.quit() 
                            except: pass
                            driver = None
                        time.sleep(5)
                
                if not recuperado:
                    logger.critical("FALHA TOTAL NA RECUPERAÇÃO DO WORKER. Encerrando este worker.")
                    resultados['erros'].append({'cliente': termo_busca, 'erro': "FALHA_FATAL_WORKER"})
                    resultado_queue.put(resultados)
                    return
                
                logger.info(f"Retomando processamento do cliente: {termo_busca}")
        
        logger.info(f"Processamento concluído: {len(resultados['sucesso'])} sucesso, "
                   f"{len(resultados['nao_encontrados'])} não encontrados, "
                   f"{len(resultados['erros'])} erros")
        
    except Exception as e:
        logger.error(f"Erro fatal no worker: {e}")
    finally:
        # Envia resultados
        resultado_queue.put(resultados)
        logger.info("Resultados enviados ao processo principal")


def consolidar_resultados(resultado_queue: Queue, num_workers: int) -> Dict:
    """
    Coleta resultados de todos os workers e gera relatório unificado.
    """
    resultados = {
        'sucesso': [],
        'nao_encontrados': [],
        'erros': [],
        'por_worker': {},
        'total_processado': 0
    }
    
    workers_finalizados = 0
    timeout_por_worker = 7200  # 2 horas por worker
    
    while workers_finalizados < num_workers:
        try:
            resultado_worker = resultado_queue.get(timeout=timeout_por_worker)
            worker_id = resultado_worker.get('worker_id', 'unknown')
            
            resultados['por_worker'][worker_id] = resultado_worker
            resultados['sucesso'].extend(resultado_worker.get('sucesso', []))
            resultados['nao_encontrados'].extend(resultado_worker.get('nao_encontrados', []))
            resultados['erros'].extend(resultado_worker.get('erros', []))
            resultados['total_processado'] += resultado_worker.get('total', 0)
            
            workers_finalizados += 1
            logging.info(f"Worker {worker_id} finalizado ({workers_finalizados}/{num_workers})")
            
        except Exception as e:
            logging.error(f"Timeout ou erro aguardando worker: {e}")
            break
    
    return resultados


def salvar_relatorio_consolidado(resultados: Dict, arquivo_origem: str):
    """
    Salva relatório consolidado em CSV com detalhes por worker.
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    nome_csv = f"relatorio_paralelo_{timestamp}.csv"
    
    with open(nome_csv, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(["Status", "Cliente", "Worker"])
        
        for worker_id, dados in resultados['por_worker'].items():
            for c in dados.get('sucesso', []):
                writer.writerow(["SUCESSO", c, worker_id])
            for c in dados.get('nao_encontrados', []):
                writer.writerow(["NAO_ENCONTRADO", c, worker_id])
            for c in dados.get('erros', []):
                writer.writerow(["ERRO", c, worker_id])
    
    return nome_csv


def executar_paralelo(
    clientes: List[Dict],
    config: Dict[str, Any],
    num_workers: Optional[int] = None
) -> Dict:
    """
    Orquestra a execução paralela.
    
    Args:
        clientes: Lista completa de clientes
        config: Configurações (template, departamento, etc)
        num_workers: Número de workers (None = auto-scaling)
    
    Returns:
        Dicionário com resultados consolidados
    """
    total = len(clientes)
    
    # Auto-scaling se não especificado
    if num_workers is None:
        num_workers = calcular_workers_ideais(total)
    
    logging.info(f"Iniciando execução paralela: {total} clientes / {num_workers} workers")
    
    # Divide lista em blocos
    blocos = dividir_lista_em_blocos(clientes, num_workers)
    
    # Mostra distribuição
    for i, bloco in enumerate(blocos):
        logging.info(f"  Worker {i+1}: {len(bloco)} clientes")
    
    # Manager para comunicação entre processos
    with Manager() as manager:
        resultado_queue = manager.Queue()
        login_sync_queue = manager.Queue()
        login_sync_queue.put(0)  # Inicializa com 0 (nenhum worker logado)
        
        processos = []
        
        # Inicia workers
        for i, bloco in enumerate(blocos):
            p = Process(
                target=worker_process,
                args=(i + 1, bloco, config, resultado_queue, login_sync_queue)
            )
            processos.append(p)
            
            # Worker 1 inicia primeiro e faz login
            if i == 0:
                p.start()
                # Aguarda um pouco para o primeiro login começar
                time.sleep(3)
            else:
                # Outros workers iniciam com pequeno delay
                time.sleep(1)
                p.start()
        
        # Aguarda todos finalizarem
        for p in processos:
            p.join()
        
        # Consolida resultados
        resultados = consolidar_resultados(resultado_queue, num_workers)
    
    return resultados


def imprimir_resumo_paralelo(resultados: Dict, arquivo: str, inicio: datetime):
    """
    Imprime resumo final da execução paralela.
    """
    total = len(resultados['sucesso']) + len(resultados['nao_encontrados']) + len(resultados['erros'])
    duracao = datetime.now() - inicio
    
    print("\n" + "=" * 60)
    print("RESUMO FINAL - EXECUÇÃO PARALELA")
    print("=" * 60)
    print(f"Arquivo: {arquivo}")
    print(f"Duração: {duracao}")
    print(f"Workers utilizados: {len(resultados['por_worker'])}")
    print("-" * 60)
    print(f"Total Processado: {total}")
    print(f"✅ Sucesso: {len(resultados['sucesso'])}")
    print(f"🔍 Não Encontrados: {len(resultados['nao_encontrados'])}")
    print(f"❌ Erros: {len(resultados['erros'])}")
    print("-" * 60)
    print("Detalhes por Worker:")
    for worker_id, dados in sorted(resultados['por_worker'].items()):
        s = len(dados.get('sucesso', []))
        n = len(dados.get('nao_encontrados', []))
        e = len(dados.get('erros', []))
        print(f"  Worker {worker_id}: ✅{s} 🔍{n} ❌{e}")
    print("=" * 60)
