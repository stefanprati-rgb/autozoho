# Arquivo: main_parallel.py
# -*- coding: utf-8 -*-
"""
AutoZoho - Modo Paralelo
Envia mensagens WhatsApp usando múltiplas janelas do Edge em paralelo.
"""

import os
import sys
import argparse
import logging
from datetime import datetime

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Imports do projeto
from utils.files import carregar_lista_clientes
from utils.session import (
    gerar_hash_arquivo, gerar_session_id,
    sessao_existe, carregar_sessao, criar_sessao,
    salvar_progresso, cliente_ja_processado,
    apagar_sessao, resumo_sessao, contar_processados
)
from core.parallel import (
    calcular_workers_ideais,
    executar_paralelo,
    salvar_relatorio_consolidado,
    imprimir_resumo_paralelo
)

try:
    from config.constants import TEMPLATES_DISPONIVEIS, DEPARTAMENTOS_DISPONIVEIS
except ImportError:
    TEMPLATES_DISPONIVEIS = {}
    DEPARTAMENTOS_DISPONIVEIS = {}


def resolver_template(entrada):
    """Resolve template por número ou nome."""
    if entrada in TEMPLATES_DISPONIVEIS:
        return TEMPLATES_DISPONIVEIS[entrada]["nome"], TEMPLATES_DISPONIVEIS[entrada]["ancoras"]
    for k, v in TEMPLATES_DISPONIVEIS.items():
        if v["nome"].lower() == entrada.lower():
            return v["nome"], v["ancoras"]
    return None, None


def resolver_departamento(entrada):
    """Resolve departamento por número ou nome."""
    if entrada in DEPARTAMENTOS_DISPONIVEIS:
        return DEPARTAMENTOS_DISPONIVEIS[entrada]
    for k, v in DEPARTAMENTOS_DISPONIVEIS.items():
        if v.lower() == entrada.lower():
            return v
    return None


def menu_principal():
    """Menu interativo para seleção de template e departamento."""
    print("\n" + "=" * 50)
    print("AUTOZOHO - MODO PARALELO")
    print("=" * 50)
    
    # Departamento
    print("\nDepartamentos disponíveis:")
    for k in sorted(DEPARTAMENTOS_DISPONIVEIS.keys(), key=int):
        print(f"  {k}) {DEPARTAMENTOS_DISPONIVEIS[k]}")
    d = input("\nEscolha o Departamento (Número): ").strip()
    dept = DEPARTAMENTOS_DISPONIVEIS.get(d)
    
    if not dept:
        print("❌ Departamento inválido!")
        return None, None, None
    
    # Template
    print("\nTemplates disponíveis:")
    for k in sorted(TEMPLATES_DISPONIVEIS.keys(), key=int):
        print(f"  {k}) {TEMPLATES_DISPONIVEIS[k]['nome']}")
    t = input("\nEscolha o Template (Número): ").strip()
    temp_data = TEMPLATES_DISPONIVEIS.get(t)
    
    if not temp_data:
        print("❌ Template inválido!")
        return None, None, None
    
    return temp_data["nome"], temp_data["ancoras"], dept


def main():
    parser = argparse.ArgumentParser(
        description="AutoZoho - Envio paralelo de mensagens WhatsApp via Zoho Desk."
    )
    
    parser.add_argument(
        "-a", "--arquivo",
        required=True,
        help="Caminho para o arquivo .xlsx ou .csv com a lista de clientes."
    )
    parser.add_argument(
        "--workers",
        type=int,
        choices=[1, 2, 3, 4],
        default=None,
        help="Número de workers paralelos (1-4). Padrão: auto-scaling baseado na lista."
    )
    parser.add_argument(
        "--template",
        help="Número ou nome do template."
    )
    parser.add_argument(
        "--departamento",
        help="Número ou nome do departamento."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Modo simulação (não envia mensagem)."
    )
    parser.add_argument(
        "-l", "--loglevel",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Nível de log."
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Retomar sessão anterior automaticamente."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Forçar nova sessão, ignorando progresso anterior."
    )
    
    args = parser.parse_args()
    
    # Cria pasta de logs se não existir
    os.makedirs('logging', exist_ok=True)
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.loglevel),
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join('logging', 'automacao_paralelo.log'), encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    inicio = datetime.now()
    logging.info(f"Iniciando AutoZoho Paralelo em: {inicio}")
    
    if args.dry_run:
        logging.warning(">>> MODO DRY-RUN (SIMULAÇÃO) ATIVADO <<<")
    
    # Resolver template e departamento
    if args.template and args.departamento:
        template_nome, ancoras = resolver_template(args.template)
        departamento = resolver_departamento(args.departamento)
    else:
        template_nome, ancoras, departamento = menu_principal()
    
    if not template_nome or not departamento:
        logging.error("Configuração incompleta. Encerrando.")
        return
    
    logging.info(f"Template: {template_nome} | Departamento: {departamento}")
    
    # Carregar clientes
    logging.info("Carregando lista de clientes...")
    clientes = carregar_lista_clientes(args.arquivo)
    
    if not clientes:
        logging.error("Lista de clientes vazia ou arquivo não encontrado.")
        return
    
    total_original = len(clientes)
    logging.info(f"Total de clientes carregados: {total_original}")
    
    # === SISTEMA DE SESSÕES (PERSISTENTE) ===
    hash_arquivo = gerar_hash_arquivo(args.arquivo)
    session_id = gerar_session_id(hash_arquivo, template_nome, departamento)
    
    logging.info(f"Session ID: {session_id}")
    
    retomar_sessao = False
    
    if sessao_existe(session_id):
        if args.force:
            print("\n⚠️  Flag --force detectada. Apagando sessão anterior...")
            apagar_sessao(session_id)
            logging.info("Sessão anterior apagada por --force")
        elif args.resume:
            retomar_sessao = True
            print(resumo_sessao(session_id))
            print("\n▶️  Flag --resume detectada. Retomando automaticamente...")
            logging.info("Retomando sessão por --resume")
        else:
            print(resumo_sessao(session_id))
            resposta = input("\n❓ Deseja RETOMAR esta sessão? (S=Retomar / N=Recomeçar): ").strip().upper()
            
            if resposta == 'S':
                retomar_sessao = True
                logging.info("Usuário optou por RETOMAR sessão")
            else:
                apagar_sessao(session_id)
                logging.info("Usuário optou por RECOMEÇAR - sessão apagada")
    
    # Cria nova sessão se não existe
    if not sessao_existe(session_id):
        criar_sessao(session_id, args.arquivo, hash_arquivo, 
                     template_nome, departamento, total_original)
    
    # Filtrar clientes já processados se estiver retomando
    if retomar_sessao:
        clientes_pendentes = [
            c for c in clientes 
            if not cliente_ja_processado(session_id, c.get('busca', ''))
        ]
        filtrados = total_original - len(clientes_pendentes)
        if filtrados > 0:
            print(f"\n✅ Pulando {filtrados} clientes já processados...")
            logging.info(f"Filtrados {filtrados} clientes já processados")
        clientes = clientes_pendentes
    
    total = len(clientes)
    
    if total == 0:
        print("\n✅ Todos os clientes já foram processados!")
        logging.info("Nenhum cliente pendente para processar")
        return
    
    # Determinar número de workers
    if args.workers:
        num_workers = args.workers
        logging.info(f"Usando {num_workers} workers (especificado pelo usuário)")
    else:
        num_workers = calcular_workers_ideais(total)
        logging.info(f"Auto-scaling: {total} clientes → {num_workers} worker(s)")
    
    # Mostrar configuração
    print("\n" + "=" * 60)
    print("CONFIGURAÇÃO DA EXECUÇÃO PARALELA")
    print("=" * 60)
    print(f"  Arquivo.........: {args.arquivo}")
    print(f"  Total Clientes..: {total}")
    print(f"  Workers.........: {num_workers}")
    print(f"  Departamento....: {departamento}")
    print(f"  Template........: {template_nome}")
    print(f"  Dry-Run.........: {'SIM' if args.dry_run else 'NÃO'}")
    print("=" * 60)
    
    # Confirmar execução
    if not args.dry_run:
        resp = input("\n⚠️  Confirma início da execução? (s/N): ").strip().lower()
        if resp != 's':
            print("Execução cancelada.")
            return
    
    # Configuração para os workers
    config = {
        'template_nome': template_nome,
        'ancoras': ancoras,
        'departamento': departamento,
        'dry_run': args.dry_run,
        'session_id': session_id  # Para salvar progresso
    }
    
    # Executar em paralelo
    try:
        resultados = executar_paralelo(clientes, config, num_workers)
        
        # Salvar relatório
        csv_path = salvar_relatorio_consolidado(resultados, args.arquivo)
        logging.info(f"Relatório salvo: {csv_path}")
        
        # Imprimir resumo
        imprimir_resumo_paralelo(resultados, args.arquivo, inicio)
        
    except KeyboardInterrupt:
        logging.warning("Execução interrompida pelo usuário.")
    except Exception as e:
        logging.error(f"Erro fatal: {e}")
        raise


if __name__ == "__main__":
    main()
