"""
core/actions.py
Ações Selenium resilientes e padronizadas.

- Localização por seletor (CSS/XPath) com waits
- Clique seguro (retry + scroll + foco)
- Digitação confiável (clear opcional, paste, slow type)
- Esperas utilitárias (visível, clicável, sumir, texto)
- Scrolling helpers
- Screenshots/logs automáticos em falha
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional, Iterable, Literal, Tuple

from loguru import logger
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
    ElementNotInteractableException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver, WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

try:
    from config import CONFIG
except Exception:
    class _Timeouts:  # fallbacks seguros
        search_wait = 15
        after_click = 20
        short = 5
        long = 45
    class _Cfg:
        timeouts = _Timeouts()
    CONFIG = _Cfg()

# import tardio para evitar circularidade com core.driver no import-time
def _screenshot_safe(name: str, driver: Optional[WebDriver]):
    try:
        from core.driver import _screenshot_fallback
        return _screenshot_fallback(name, driver)
    except Exception:
        return None


# ------------------------ Tipos e helpers ------------------------
LocatorType = Literal["css", "xpath"]

def _by(locator_type: LocatorType) -> By:
    return By.CSS_SELECTOR if locator_type == "css" else By.XPATH

def _wait(driver: WebDriver, seconds: Optional[int] = None) -> WebDriverWait:
    t = seconds or getattr(getattr(CONFIG, "timeouts", object()), "search_wait", 15)
    return WebDriverWait(driver, t)

def _sleep_smart(seg: float):
    if seg > 0:
        time.sleep(seg)


# ------------------------ Finds com wait ------------------------
def find_one(
    driver: WebDriver,
    selector: str,
    locator_type: LocatorType = "css",
    timeout: Optional[int] = None,
    must_be_visible: bool = True,
) -> WebElement:
    """
    Retorna um único elemento com espera.
    - must_be_visible=True => espera 'visibility_of_element_located'
    """
    by = _by(locator_type)
    wait = _wait(driver, timeout)
    cond = EC.visibility_of_element_located if must_be_visible else EC.presence_of_element_located
    try:
        el = wait.until(cond((by, selector)))
        return el
    except TimeoutException as e:
        _screenshot_safe("find_one_timeout", driver)
        raise e


def find_all(
    driver: WebDriver,
    selector: str,
    locator_type: LocatorType = "css",
    timeout: Optional[int] = None,
    require_non_empty: bool = True,
    must_be_visible: bool = False,
) -> Iterable[WebElement]:
    """
    Retorna lista de elementos; opcionalmente exige lista não-vazia.
    """
    by = _by(locator_type)
    wait = _wait(driver, timeout)
    cond = EC.visibility_of_all_elements_located if must_be_visible else EC.presence_of_all_elements_located
    try:
        els = wait.until(cond((by, selector)))
        if require_non_empty and not els:
            raise TimeoutException(f"Lista vazia para seletor: {selector}")
        return els
    except TimeoutException as e:
        _screenshot_safe("find_all_timeout", driver)
        raise e


# ------------------------ Scroll/foco ------------------------
def scroll_into_view(driver: WebDriver, el: WebElement, align: str = "center"):
    try:
        driver.execute_script(f"arguments[0].scrollIntoView({{behavior:'instant', block:'{align}'}});", el)
    except Exception:
        # fallback
        driver.execute_script("arguments[0].scrollIntoView(true);", el)

def focus_element(driver: WebDriver, el: WebElement):
    try:
        driver.execute_script("arguments[0].focus();", el)
    except Exception:
        pass


# ------------------------ Clique resiliente ------------------------
def click_safe(
    driver: WebDriver,
    selector: str,
    locator_type: LocatorType = "css",
    timeout: Optional[int] = None,
    retries: int = 3,
    after_click_wait: Optional[int] = None,
) -> WebElement:
    """
    Clique robusto:
      - wait visível + clicável
      - scroll + foco
      - retry para Stale/Intercepted/NotInteractable
    Retorna o elemento clicado.
    """
    wait = _wait(driver, timeout)
    by = _by(locator_type)
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            el = wait.until(EC.visibility_of_element_located((by, selector)))
            wait.until(EC.element_to_be_clickable((by, selector)))
            scroll_into_view(driver, el, align="center")
            focus_element(driver, el)
            try:
                el.click()
            except (ElementClickInterceptedException, ElementNotInteractableException):
                # usa JS como fallback
                driver.execute_script("arguments[0].click();", el)
            if after_click_wait:
                _wait(driver, after_click_wait).until(lambda d: True)  # pequena barreira
            return el
        except (StaleElementReferenceException,
                ElementClickInterceptedException,
                ElementNotInteractableException,
                TimeoutException) as e:
            last_exc = e
            logger.debug(f"[click_safe] tentativa {attempt}/{retries} falhou: {e.__class__.__name__}")
            _sleep_smart(0.3 * attempt)
    _screenshot_safe("click_safe_fail", driver)
    if last_exc:
        raise last_exc
    raise RuntimeError("click_safe: falha desconhecida")


# ------------------------ Digitação confiável ------------------------
def type_text(
    driver: WebDriver,
    selector: str,
    text: str,
    locator_type: LocatorType = "css",
    timeout: Optional[int] = None,
    clear: bool = True,
    slow_type_sec_per_char: float = 0.0,
    paste: bool = False,
) -> WebElement:
    """
    Digita texto no elemento:
      - wait visível
      - clear opcional
      - slow typing (simula humano) OU paste via JS (mais resiliente)
    """
    el = find_one(driver, selector, locator_type, timeout, must_be_visible=True)
    scroll_into_view(driver, el)
    focus_element(driver, el)

    if clear:
        try:
            el.clear()
        except Exception:
            # fallback via JS
            try:
                driver.execute_script("arguments[0].value='';", el)
            except Exception:
                pass

    if paste:
        try:
            driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input',{bubbles:true}))", el, text)
            return el
        except Exception:
            # cai para slow/normal
            pass

    if slow_type_sec_per_char > 0:
        for ch in text:
            el.send_keys(ch)
            _sleep_smart(slow_type_sec_per_char)
    else:
        el.send_keys(text)
    return el


# ------------------------ Esperas utilitárias ------------------------
def wait_visible(
    driver: WebDriver,
    selector: str,
    locator_type: LocatorType = "css",
    timeout: Optional[int] = None,
) -> WebElement:
    return find_one(driver, selector, locator_type, timeout, must_be_visible=True)

def wait_clickable(
    driver: WebDriver,
    selector: str,
    locator_type: LocatorType = "css",
    timeout: Optional[int] = None,
) -> WebElement:
    by = _by(locator_type)
    return _wait(driver, timeout).until(EC.element_to_be_clickable((by, selector)))

def wait_disappear(
    driver: WebDriver,
    selector: str,
    locator_type: LocatorType = "css",
    timeout: Optional[int] = None,
) -> bool:
    by = _by(locator_type)
    try:
        _wait(driver, timeout).until(EC.invisibility_of_element_located((by, selector)))
        return True
    except TimeoutException:
        _screenshot_safe("wait_disappear_timeout", driver)
        return False

def wait_text_present(
    driver: WebDriver,
    selector: str,
    text: str,
    locator_type: LocatorType = "css",
    timeout: Optional[int] = None,
) -> bool:
    by = _by(locator_type)
    try:
        _wait(driver, timeout).until(EC.text_to_be_present_in_element((by, selector), text))
        return True
    except TimeoutException:
        _screenshot_safe("wait_text_timeout", driver)
        return False


# ------------------------ Ações combinadas comuns ------------------------
def click_and_wait(
    driver: WebDriver,
    click_selector: str,
    wait_selector: str,
    locator_type_click: LocatorType = "css",
    locator_type_wait: LocatorType = "css",
    click_timeout: Optional[int] = None,
    wait_timeout: Optional[int] = None,
) -> Tuple[WebElement, WebElement]:
    """
    Clica em um seletor e espera outro aparecer (padrão de navegação).
    """
    el_clicked = click_safe(
        driver,
        click_selector,
        locator_type=locator_type_click,
        timeout=click_timeout,
        after_click_wait=getattr(CONFIG.timeouts, "after_click", 20),
    )
    el_waited = find_one(
        driver,
        wait_selector,
        locator_type=locator_type_wait,
        timeout=wait_timeout,
        must_be_visible=True,
    )
    return el_clicked, el_waited
