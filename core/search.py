# -*- coding: utf-8 -*-
import time
import re
import logging
from difflib import SequenceMatcher
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, ElementNotInteractableException
from utils.reports import salvar_snapshot_erro

DELAY_DIGITACAO_CURTA = 0.05
DELAY_DIGITACAO_MEDIA = 0.08
DELAY_DIGITACAO_LONGA = 0.12 # Aumentado

SELETORES = {
    "icone_pesquisa": 'button[data-id="globalSearchIcon"]',
    "barra_pesquisa": 'input[data-id="searchInput"]',
    "msg_sem_resultados": 'div.zd_v2-commonemptystate-title',
    "botao_whatsapp": 'span[data-title="Enviar mensagens via WhatsApp (canal de IM)"]',
    "linha_resultado": 'div.zd_v2-modulelistnew-innerListDiv', 
    "link_nome_cliente": 'a[data-title]',
    "tab_clientes": 'a[data-id="qtab_Contacts_Tab"]'
}

STOPWORDS_NOME = {"de","da","do","dos","e","ltda","me","epp","s/a","sa"}

def _sanear_termo(s): return str(s).strip().lower() if s else ""
def _tokens_nome(nome): return [t for t in re.split(r"\s+", str(nome).strip()) if len(t) >= 2]
def normalizar_nome(nome): return str(nome).lower().strip() if nome else ""

def _gerar_variacoes_inteligentes(dados_cliente):
    tipo = dados_cliente.get('tipo_busca', 'auto')
    valor = str(dados_cliente.get('busca', '')).strip()
    if tipo == 'email': return [valor]
    elif tipo == 'telefone': return [re.sub(r'\D', '', valor)]
    elif tipo == 'doc':
        nums = re.sub(r'\D', '', valor)
        if len(nums) == 11: return [f"{nums[:3]}.{nums[3:6]}.{nums[6:9]}-{nums[9:]}"]
        elif len(nums) == 14: return [f"{nums[:2]}.{nums[2:5]}.{nums[5:8]}/{nums[8:12]}-{nums[12:]}"]
        return [valor]
    
    nome_limpo = normalizar_nome(valor)
    toks = _tokens_nome(nome_limpo)
    if not toks: return [valor]
    variacoes = []
    if len(toks) >= 2:
        variacoes.append(f"{toks[0]} {toks[1]}")
        variacoes.append(f"{toks[0]} {toks[-1]}")
    variacoes.append(valor)
    variacoes.append(toks[0])
    return list(dict.fromkeys(variacoes))[:6]

def _validar_resultado(elemento_linha, dados_cliente):
    try: texto_linha = elemento_linha.text.lower()
    except: return False 
    pontos = 0; criterios = 0
    if dados_cliente.get('email_excel'):
        criterios += 1
        if _sanear_termo(dados_cliente['email_excel']) in texto_linha: pontos += 3
    if dados_cliente.get('telefone_excel'):
        criterios += 1
        tel_alvo = re.sub(r'\D', '', str(dados_cliente['telefone_excel']))
        if len(tel_alvo) >= 4 and tel_alvo[-4:] in texto_linha: pontos += 3
    if dados_cliente.get('nome_excel') and dados_cliente.get('tipo_busca') != 'nome':
        criterios += 1
        nome_alvo = _sanear_termo(dados_cliente['nome_excel']).split()[0]
        if nome_alvo in texto_linha: pontos += 2
    return True if criterios == 0 else pontos > 0

def _clicar_robusto(driver, elemento):
    try:
        elemento.click()
        return True
    except:
        driver.execute_script("arguments[0].click();", elemento)
        return True

def buscar_e_abrir_cliente(driver, dados_cliente):
    wait = WebDriverWait(driver, 15)
    short_wait = WebDriverWait(driver, 5)
    
    # 1. Garante Aba Clientes
    try:
        aba = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, SELETORES["tab_clientes"])))
        if "zd_v2-topmenu-menuItemActive" not in (aba.get_attribute("class") or ""):
            _clicar_robusto(driver, aba)
            time.sleep(3) # Pausa aumentada para carga
    except: pass

    # 2. Abre Pesquisa
    campo = None
    try:
        # Tenta ver se já está aberta
        possiveis = driver.find_elements(By.CSS_SELECTOR, SELETORES["barra_pesquisa"])
        for c in possiveis:
            if c.is_displayed():
                campo = c
                break
        
        if not campo:
            time.sleep(1) # Pausa antes de clicar na lupa
            btn_lupa = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, SELETORES["icone_pesquisa"])))
            _clicar_robusto(driver, btn_lupa)
            campo = short_wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, SELETORES["barra_pesquisa"])))
        
        campo.click()
        time.sleep(0.5)

    except Exception as e:
        logging.error(f"Erro ao abrir pesquisa: {e}")
        salvar_snapshot_erro(driver, "erro_barra_pesquisa")
        return False

    variacoes = _gerar_variacoes_inteligentes(dados_cliente)
    
    for termo in variacoes:
        logging.info(f"🔎 Buscando: '{termo}'")
        try:
            campo.send_keys(Keys.CONTROL, "a")
            campo.send_keys(Keys.DELETE)
            time.sleep(0.5) # Pausa após limpar
            
            for letra in termo:
                campo.send_keys(letra)
                time.sleep(DELAY_DIGITACAO_LONGA) # Digitação mais lenta
            
            time.sleep(1) # Pausa antes do Enter
            campo.send_keys(Keys.ENTER)
            
            # Pausa longa para resultados (evita o erro do React)
            time.sleep(4) 
            
            # Verifica se encontrou resultados
            if driver.find_elements(By.CSS_SELECTOR, SELETORES["msg_sem_resultados"]):
                if driver.find_element(By.CSS_SELECTOR, SELETORES["msg_sem_resultados"]).is_displayed():
                    continue

            linhas = driver.find_elements(By.CSS_SELECTOR, SELETORES["linha_resultado"])
            for linha in linhas:
                if _validar_resultado(linha, dados_cliente):
                    try:
                        link = linha.find_element(By.CSS_SELECTOR, SELETORES["link_nome_cliente"])
                        logging.info(f"   🖱️ Clicando: {link.get_attribute('data-title')}")
                        
                        if _clicar_robusto(driver, link):
                            WebDriverWait(driver, 20).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, SELETORES["botao_whatsapp"]))
                            )
                            time.sleep(2) # Pausa para estabilizar a página do cliente
                            return True
                    except Exception as e:
                        logging.error(f"Erro clique: {e}")
                        salvar_snapshot_erro(driver, "erro_clique")

        except Exception as e:
            logging.error(f"Erro busca '{termo}': {e}")
            try: campo = driver.find_element(By.CSS_SELECTOR, SELETORES["barra_pesquisa"])
            except: pass

    return False