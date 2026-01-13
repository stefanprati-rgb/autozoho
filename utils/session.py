# -*- coding: utf-8 -*-
"""
Módulo de Gerenciamento de Sessões - AutoZoho

Permite retomar execuções interrompidas, identificando campanhas únicas
através de hash do arquivo + template + departamento.
"""
import os
import json
import hashlib
import logging
from datetime import datetime
from pathlib import Path

# Diretório onde as sessões são armazenadas
SESSIONS_DIR = Path(__file__).parent.parent / "sessions"


def gerar_hash_arquivo(caminho_arquivo: str) -> str:
    """
    Gera um hash MD5 do conteúdo do arquivo.
    Usado para detectar se o arquivo foi modificado.
    """
    hash_md5 = hashlib.md5()
    try:
        with open(caminho_arquivo, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logging.error(f"Erro ao calcular hash do arquivo: {e}")
        return ""


def gerar_session_id(hash_arquivo: str, template: str, departamento: str) -> str:
    """
    Gera um ID único para a sessão baseado em:
    - Hash do conteúdo do arquivo
    - Nome do template
    - Nome do departamento
    
    Isso garante que:
    - Mesmo arquivo + mesmo template + mesmo dept = mesma sessão (retomável)
    - Arquivo modificado = nova sessão automática
    - Template diferente = nova sessão
    """
    combo = f"{hash_arquivo}:{template}:{departamento}"
    return hashlib.md5(combo.encode()).hexdigest()[:12]


def get_session_path(session_id: str) -> Path:
    """Retorna o caminho do arquivo de sessão."""
    return SESSIONS_DIR / f"session_{session_id}.json"


def sessao_existe(session_id: str) -> bool:
    """Verifica se uma sessão existe."""
    return get_session_path(session_id).exists()


def carregar_sessao(session_id: str) -> dict:
    """
    Carrega uma sessão existente do disco.
    
    Returns:
        dict com dados da sessão ou None se não existir
    """
    session_path = get_session_path(session_id)
    
    if not session_path.exists():
        return None
    
    try:
        with open(session_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Erro ao carregar sessão {session_id}: {e}")
        return None


def criar_sessao(session_id: str, arquivo: str, hash_arquivo: str, 
                 template: str, departamento: str, total_clientes: int) -> dict:
    """
    Cria uma nova sessão e salva no disco.
    """
    # Garante que o diretório existe
    SESSIONS_DIR.mkdir(exist_ok=True)
    
    sessao = {
        "session_id": session_id,
        "arquivo": os.path.basename(arquivo),
        "arquivo_path": arquivo,
        "hash": hash_arquivo,
        "template": template,
        "departamento": departamento,
        "iniciado_em": datetime.now().isoformat(),
        "atualizado_em": datetime.now().isoformat(),
        "total_clientes": total_clientes,
        "processados": {}
    }
    
    _salvar_sessao(session_id, sessao)
    logging.info(f"Nova sessão criada: {session_id}")
    
    return sessao


def salvar_progresso(session_id: str, cliente: str, status: str) -> bool:
    """
    Salva o progresso de um cliente na sessão.
    
    Args:
        session_id: ID da sessão
        cliente: Termo de busca do cliente
        status: SUCESSO, NAO_ENCONTRADO, ERRO
    
    Returns:
        True se salvou com sucesso
    """
    sessao = carregar_sessao(session_id)
    
    if not sessao:
        logging.error(f"Sessão {session_id} não encontrada para salvar progresso")
        return False
    
    sessao["processados"][cliente] = {
        "status": status,
        "timestamp": datetime.now().isoformat()
    }
    sessao["atualizado_em"] = datetime.now().isoformat()
    
    return _salvar_sessao(session_id, sessao)


def cliente_ja_processado(session_id: str, cliente: str) -> bool:
    """
    Verifica se um cliente já foi processado na sessão.
    """
    sessao = carregar_sessao(session_id)
    
    if not sessao:
        return False
    
    return cliente in sessao.get("processados", {})


def obter_status_cliente(session_id: str, cliente: str) -> str:
    """
    Retorna o status de processamento de um cliente.
    """
    sessao = carregar_sessao(session_id)
    
    if not sessao:
        return None
    
    proc = sessao.get("processados", {}).get(cliente)
    return proc.get("status") if proc else None


def contar_processados(session_id: str) -> dict:
    """
    Retorna contagem de clientes por status.
    """
    sessao = carregar_sessao(session_id)
    
    if not sessao:
        return {"SUCESSO": 0, "NAO_ENCONTRADO": 0, "ERRO": 0}
    
    contagem = {"SUCESSO": 0, "NAO_ENCONTRADO": 0, "ERRO": 0}
    
    for cliente, dados in sessao.get("processados", {}).items():
        status = dados.get("status", "ERRO")
        if status in contagem:
            contagem[status] += 1
    
    return contagem


def apagar_sessao(session_id: str) -> bool:
    """
    Remove uma sessão do disco.
    """
    session_path = get_session_path(session_id)
    
    try:
        if session_path.exists():
            session_path.unlink()
            logging.info(f"Sessão {session_id} removida")
        return True
    except Exception as e:
        logging.error(f"Erro ao remover sessão {session_id}: {e}")
        return False


def listar_sessoes_ativas() -> list:
    """
    Lista todas as sessões no diretório.
    """
    if not SESSIONS_DIR.exists():
        return []
    
    sessoes = []
    for f in SESSIONS_DIR.glob("session_*.json"):
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                data = json.load(fp)
                contagem = contar_processados(data["session_id"])
                sessoes.append({
                    "id": data["session_id"],
                    "arquivo": data.get("arquivo", "?"),
                    "template": data.get("template", "?"),
                    "departamento": data.get("departamento", "?"),
                    "iniciado_em": data.get("iniciado_em", "?"),
                    "total": data.get("total_clientes", 0),
                    "processados": sum(contagem.values()),
                    "sucesso": contagem["SUCESSO"]
                })
        except Exception as e:
            logging.warning(f"Erro ao ler sessão {f.name}: {e}")
    
    return sessoes


def _salvar_sessao(session_id: str, sessao: dict) -> bool:
    """
    Função interna para salvar sessão no disco.
    """
    session_path = get_session_path(session_id)
    
    try:
        SESSIONS_DIR.mkdir(exist_ok=True)
        with open(session_path, 'w', encoding='utf-8') as f:
            json.dump(sessao, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logging.error(f"Erro ao salvar sessão {session_id}: {e}")
        return False


def resumo_sessao(session_id: str) -> str:
    """
    Retorna um resumo formatado da sessão para exibição.
    """
    sessao = carregar_sessao(session_id)
    
    if not sessao:
        return "Sessão não encontrada"
    
    contagem = contar_processados(session_id)
    total = sessao.get("total_clientes", 0)
    processados = sum(contagem.values())
    restantes = total - processados
    
    return (
        f"\n{'='*50}\n"
        f"📋 SESSÃO ANTERIOR ENCONTRADA\n"
        f"{'='*50}\n"
        f"Arquivo: {sessao.get('arquivo', '?')}\n"
        f"Template: {sessao.get('template', '?')}\n"
        f"Departamento: {sessao.get('departamento', '?')}\n"
        f"Iniciado em: {sessao.get('iniciado_em', '?')[:19]}\n"
        f"\n📊 Progresso:\n"
        f"  Total: {total}\n"
        f"  ✅ Sucesso: {contagem['SUCESSO']}\n"
        f"  🔍 Não Encontrados: {contagem['NAO_ENCONTRADO']}\n"
        f"  ❌ Erros: {contagem['ERRO']}\n"
        f"  ⏳ Restantes: {restantes}\n"
        f"{'='*50}"
    )
