"""
core/driver.py
Inicialização e ciclo de vida do WebDriver (Edge/Chromium).

- Opções seguras e performáticas
- Reutilização de sessão (user-data-dir) ou cookies
- Retry automático (tenacity) na criação do driver
- Screenshots e logs em caso de falha
- Detach opcional
"""

from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.options import ArgOptions
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService

# ---------------------------------------------------------------------------
# Config com fallback: evita quebrar import-time caso CONFIG/SETTINGS mudem
# ---------------------------------------------------------------------------
try:
    from config import CONFIG, SETTINGS  # seus objetos (yaml/.env)
except Exception:
    class _Cfg:
        class Retry:
            tentativas = 3
            backoff_base = 1
            max_backoff = 8
        class Driver:
            base_url = "https://example.com"
        retry = Retry()
        driver = Driver()
    class _Set:
        keep_browser_open = False
        headless = False
        edge_user_data_dir: Optional[str] = None  # se presente, não precisa cookies
        download_dir: str = str(Path.cwd() / "downloads")
        selenium_remote_url: Optional[str] = None
    CONFIG, SETTINGS = _Cfg(), _Set()  # fallback leve

# ---------------------------------------------------------------------------
# Constantes / paths
# ---------------------------------------------------------------------------
COOKIES_FILE = Path(__file__).resolve().parent.parent / "cookies.pkl"
EDGE_DRIVER_PATH: Optional[str] = None  # None -> Selenium Manager
DEFAULT_PAGELOAD_TIMEOUT = 45
DEFAULT_SCRIPT_TIMEOUT = 45
DEFAULT_IMPLICIT_WAIT = 0

# ---------------------------------------------------------------------------
# Opções do Edge (Chromium)
# ---------------------------------------------------------------------------
def _get_edge_options(headless: Optional[bool]) -> EdgeOptions:
    opts = EdgeOptions()

    # Headless
    _headless = SETTINGS.headless if headless is None else headless
    if _headless:
        # "new" é mais estável nas versões modernas
        try:
            opts.add_argument("--headless=new")
        except Exception:
            opts.add_argument("--headless")

    # Performance/estabilidade em CI
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-notifications")
    opts.add_argument("--disable-background-timer-throttling")
    opts.add_argument("--disable-backgrounding-occluded-windows")
    opts.add_argument("--disable-renderer-backgrounding")

    # Downloads silenciosos
    download_dir = Path(SETTINGS.download_dir).resolve()
    download_dir.mkdir(parents=True, exist_ok=True)
    prefs = {
        "download.default_directory": str(download_dir),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    opts.add_experimental_option("prefs", prefs)

    # Detach (manter navegador aberto ao final)
    if getattr(SETTINGS, "keep_browser_open", False):
        opts.add_experimental_option("detach", True)

    # Reuso de perfil completo (preferível a cookies)
    if getattr(SETTINGS, "edge_user_data_dir", None):
        opts.add_argument(f'--user-data-dir={SETTINGS.edge_user_data_dir}')

    # Logs de navegador e performance
    caps = DesiredCapabilities.EDGE.copy()
    caps["goog:loggingPrefs"] = {"browser": "ALL", "performance": "ALL"}
    opts.set_capability("goog:loggingPrefs", {"browser": "ALL", "performance": "ALL"})
    for k, v in caps.items():
        try:
            opts.set_capability(k, v)
        except Exception:
            pass

    return opts

# ---------------------------------------------------------------------------
# Cookies helpers
# ---------------------------------------------------------------------------
def _salvar_cookies(driver) -> None:
    if getattr(SETTINGS, "edge_user_data_dir", None):
        logger.debug("User-data-dir ativo: ignorando salvamento de cookies.")
        return
    try:
        cookies = driver.get_cookies()
        with open(COOKIES_FILE, "wb") as f:
            pickle.dump(cookies, f)
        logger.debug(f"Cookies salvos em {COOKIES_FILE}.")
    except Exception as e:
        logger.warning(f"Não foi possível salvar cookies: {e!r}")

def _restaurar_cookies(driver, base_url: str) -> None:
    """
    Para adicionar cookies, o driver PRECISA estar num domínio compatível.
    Estratégia:
      - abre base_url
      - injeta cookies conhecidos
      - atualiza a página
    """
    if getattr(SETTINGS, "edge_user_data_dir", None):
        logger.debug("User-data-dir ativo: ignorando restauração de cookies.")
        return
    if not COOKIES_FILE.exists():
        logger.debug("Nenhum cookies.pkl encontrado.")
        return

    try:
        driver.get(base_url)
        with open(COOKIES_FILE, "rb") as f:
            cookies = pickle.load(f)
        ok, skipped = 0, 0
        for ck in cookies:
            try:
                # Selenium exige chaves válidas e domain consistente
                ck = {k: v for k, v in ck.items() if k in {
                    "name", "value", "domain", "path", "expiry", "secure", "httpOnly", "sameSite"
                }}
                driver.add_cookie(ck)
                ok += 1
            except Exception:
                skipped += 1
        driver.refresh()
        logger.info(f"Cookies restaurados ({ok} aplicados, {skipped} ignorados).")
    except Exception as e:
        logger.warning(f"Falha ao restaurar cookies: {e!r}")

# ---------------------------------------------------------------------------
# Inicialização com retry
# ---------------------------------------------------------------------------
@retry(
    stop=stop_after_attempt(getattr(CONFIG.retry, "tentativas", 3)),
    wait=wait_exponential(
        multiplier=getattr(CONFIG.retry, "backoff_base", 1),
        max=getattr(CONFIG.retry, "max_backoff", 8)
    ),
    reraise=True,
    before_sleep=lambda rs: logger.warning(
        f"Tentativa {rs.attempt_number} falhou ao iniciar o driver. Retentando..."
    ),
)
def iniciar_driver(headless: Optional[bool] = None):
    """
    Cria e retorna um WebDriver Edge (local ou remoto) com opções seguras.
    - Respeita SETTINGS.selenium_remote_url (se definido)
    - Define timeouts padrão
    """
    logger.info("Inicializando Microsoft Edge WebDriver...")
    options = _get_edge_options(headless)

    try:
        remote_url = getattr(SETTINGS, "selenium_remote_url", None)
        if remote_url:
            driver = webdriver.Remote(command_executor=remote_url, options=options)
        else:
            service = EdgeService(executable_path=EDGE_DRIVER_PATH) if EDGE_DRIVER_PATH else None
            driver = webdriver.Edge(service=service, options=options)

        driver.set_page_load_timeout(DEFAULT_PAGELOAD_TIMEOUT)
        driver.set_script_timeout(DEFAULT_SCRIPT_TIMEOUT)
        driver.implicitly_wait(DEFAULT_IMPLICIT_WAIT)

        # maximize opcional (nem todo ambiente suporta)
        try:
            driver.maximize_window()
        except Exception as e:
            logger.debug(f"Não foi possível maximizar a janela: {e!r}")

        caps = driver.capabilities or {}
        logger.info(f"Edge iniciado. Versões: browser={caps.get('browserVersion')}, "
                    f"selenium={caps.get('se:options', {}).get('se:cdpVersion')}")
        return driver

    except WebDriverException as e:
        logger.error(f"Erro ao iniciar Edge: {e}")
        _screenshot_fallback("erro_iniciar_driver")
        raise

def iniciar_driver_com_sessao(headless: Optional[bool] = None, base_url: Optional[str] = None):
    """
    Inicia driver e tenta restaurar sessão:
    - Se user-data-dir estiver configurado, não mexe em cookies.
    - Caso contrário, restaura cookies e garante estar no base_url.
    """
    drv = iniciar_driver(headless=headless)
    _base = base_url or getattr(CONFIG.driver, "base_url", "about:blank")

    if getattr(SETTINGS, "edge_user_data_dir", None):
        # perfil persistente já garante sessão
        try:
            if _base and _base != "about:blank":
                drv.get(_base)
        except Exception as e:
            logger.warning(f"Falha ao abrir base_url: {e!r}")
        return drv

    # Cookies
    _restaurar_cookies(drv, _base)
    return drv

# ---------------------------------------------------------------------------
# Context manager para ciclo de vida com salvamento de cookies e screenshot
# ---------------------------------------------------------------------------
class DriverManager:
    """
    Uso:
        with DriverManager(headless=False, base_url=CONFIG.driver.base_url) as driver:
            driver.get("https://...")

    Em caso de exceção dentro do bloco, salva screenshot automaticamente.
    Ao sair, salva cookies (se aplicável) e encerra o driver, a não ser que keep_browser_open=True.
    """
    def __init__(self, headless: Optional[bool] = None, base_url: Optional[str] = None):
        self.headless = headless
        self.base_url = base_url or getattr(CONFIG.driver, "base_url", "about:blank")
        self.driver = None

    def __enter__(self):
        self.driver = iniciar_driver_com_sessao(self.headless, self.base_url)
        return self.driver

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc:
                _screenshot_fallback("erro_runtime_driver", self.driver)
            _salvar_cookies(self.driver)
        finally:
            if not getattr(SETTINGS, "keep_browser_open", False):
                try:
                    self.driver.quit()
                except Exception:
                    pass
        # Propaga exceção (não suprime)
        return False

# ---------------------------------------------------------------------------
# Screenshot fallback (sem dependências cruzadas)
# ---------------------------------------------------------------------------
def _screenshot_fallback(base_name: str, driver=None) -> Optional[Path]:
    try:
        out_dir = Path.cwd() / "screenshots"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{base_name}.png"
        if driver:
            driver.get_screenshot_as_file(str(path))
        else:
            # sem driver: cria um marcador vazio
            path.write_bytes(b"")
        logger.debug(f"Screenshot salvo em {path}")
        return path
    except Exception as e:
        logger.warning(f"Falha ao salvar screenshot de fallback: {e!r}")
        return None
