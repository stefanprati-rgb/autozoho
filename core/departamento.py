# core/departamento.py
from __future__ import annotations

from loguru import logger
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from core.driver import _screenshot_fallback


def trocar_departamento_zoho(driver, nome_departamento: str, timeout: int = 15) -> bool:
    """
    Troca o departamento atual no Zoho Desk pelo `nome_departamento`.

    Fluxo:
      - tenta focar a aba "E-mail" (libera o dropdown)
      - abre dropdown de departamento
      - seleciona por match exato ou parcial
      - opcional: volta pra aba "WhatsApp"

    Retorna True em sucesso.
    """
    wait = WebDriverWait(driver, timeout)
    try:
        # 1) ir para a aba "E-mail" (costuma exibir o dropdown de departamento)
        try:
            el = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[text()='E-mail']")))
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            try:
                el.click()
            except Exception:
                driver.execute_script("arguments[0].click();", el)
        except Exception:
            pass  # segue mesmo assim

        # 2) dropdown de departamento
        dd = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "span[data-id='qdeptcontainer_value']")))
        atual = dd.get_attribute("data-title") or dd.text.strip()
        if (atual or "").strip() == (nome_departamento or "").strip():
            return True

        try:
            dd.click()
        except Exception:
            driver.execute_script("arguments[0].click();", dd)

        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.zd_v2-listitem-multiLineValue"))
        )
        itens = [i for i in driver.find_elements(By.CSS_SELECTOR, "div.zd_v2-listitem-multiLineValue") if i.is_displayed()]
        alvo = None
        for i in itens:
            txt = (i.text or "").strip()
            if not txt:
                continue
            if txt == nome_departamento or nome_departamento.upper() in txt.upper():
                alvo = i
                break

        if not alvo:
            _screenshot_fallback("departamento_nao_encontrado", driver)
            return False

        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", alvo)
        try:
            alvo.click()
        except Exception:
            driver.execute_script("arguments[0].click();", alvo)

        # 3) voltar pra aba "WhatsApp" (quando existir)
        try:
            elw = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[text()='WhatsApp']")))
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elw)
            try:
                elw.click()
            except Exception:
                driver.execute_script("arguments[0].click();", elw)
        except Exception:
            pass

        return True

    except Exception as e:
        logger.error(f"Troca de departamento falhou: {e}")
        _screenshot_fallback("trocar_departamento_fail", driver)
        return False
