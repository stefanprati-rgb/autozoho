"""
Módulo de configurações centralizadas.

Responsabilidades:
- Carregar constantes de arquivo YAML (.yaml)
- Validar tipos via Pydantic
- Permitir sobrescrita por variáveis de ambiente
- Suportar re-carregamento controlado (útil para testes)
"""

import yaml
from pathlib import Path
from typing import Dict, List
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


# ---------- Modelos de Dados ----------
class TemplateConfig(BaseModel):
    nome: str
    ancoras: List[str]


class RetryConfig(BaseModel):
    tentativas: int = 3
    backoff_base: float = 0.5
    max_backoff: float = 10.0


class TimeoutsConfig(BaseModel):
    login: int = 900
    troca_dept: int = 15
    busca_cliente: int = 15
    envio: int = 600


class FuzzyConfig(BaseModel):
    threshold: float = 0.85
    primeiro_ultimo: float = 0.85


class ZohoConfig(BaseModel):
    url: str
    departamentos: Dict[str, str]
    templates: Dict[str, TemplateConfig]


class Config(BaseModel):
    zoho: ZohoConfig
    timeouts: TimeoutsConfig = TimeoutsConfig()
    fuzzy: FuzzyConfig = FuzzyConfig()
    retry: RetryConfig = RetryConfig()


# ---------- Configurações via Ambiente ----------
class Settings(BaseSettings):
    zoho_email: str
    zoho_senha: str
    keep_browser_open: bool = True
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )


# ---------- Controle de Inicialização ----------
CONFIG: Config | None = None
SETTINGS: Settings | None = None


def init():
    """Inicializa ou reinicializa as configurações (útil para testes)."""
    global CONFIG, SETTINGS
    CONFIG = load_config()
    SETTINGS = Settings()


def load_config() -> Config:
    yaml_path = Path(__file__).parent / "config.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"Arquivo de configuração não encontrado: {yaml_path}")
    with yaml_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Config.parse_obj(data)