# -*- coding: utf-8 -*-
"""
Módulo de busca de clientes (core/search.py).
Versão Atualizada: Navega para aba 'Clientes' antes de buscar.
"""

import time
import re
import logging
from difflib import SequenceMatcher

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException
)

# --- CONSTANTES ---
DELAY_DIGITACAO_CURTA = 0.02
DELAY_DIGITACAO_MEDIA = 0.03
DELAY_DIGITACAO_LONGA = 0.04

STOPWORDS_NOME = {
    "de","da","do","das","dos","e","d","jr","jr.","junior","júnior","filho","neto","sobrinho",
    "me","epp","s/a","sa","s.a","s.a.","ltda","ltda.","holding","group","grupogera"
}

SOBRENOMES_COMUNS_IGNORAR = {
    "silva", "santos", "souza", "oliveira", "pereira", "lima", "ferreira",
    "costa", "rodrigues", "almeida", "nascimento", "gomes", "martins",
    "araujo", "melo", "barbosa", "cardoso", "teixeira", "dias", "vieira",
    "batista"
}

SELETORES = {
    "icone_pesquisa": 'button[data-id="globalSearchIcon"]',
    "barra_pesquisa": 'input[data-id="searchInput"]',
    "msg_sem_resultados": 'div.zd_v2-commonemptystate-title',
    "botao_whatsapp": 'span[data-title="Enviar mensagens via WhatsApp (canal de IM)"]',
    "linha_resultado": 'div.zd_v2-listlayout-innerContainer',
    # NOVO SELETOR: Aba Clientes
    "tab_clientes": 'a[data-id="qtab_Contacts_Tab"]'
}

# --- FUNÇÕES AUXILIARES ---

def normalizar_nome(nome, remover_invalidos=False):
    """Normaliza strings para comparação."""
    if not nome: return ""
    nome = str(nome)
    if remover_invalidos:
        nome = nome.replace('\ufffd', ' ').replace('?', ' ')
    
    import unicodedata
    nfkd = unicodedata.normalize('NFKD', nome)
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return re.sub(r'[^a-zA-Z0-9\s]', ' ', sem_acento).lower().strip()

def _formatar_documento(valor):
    """Formata CPF ou CNPJ para o padrão brasileiro."""
    limpo = re.sub(r'\D', '', str(valor))
    if len(limpo) == 11: # CPF
        return f"{limpo[:3]}.{limpo[3:6]}.{limpo[6:9]}-{limpo[9:]}"
    elif len(limpo) == 14: # CNPJ
        return f"{limpo[:2]}.{limpo[2:5]}.{limpo[5:8]}/{limpo[8:12]}-{limpo[12:]}"
    return valor

def _sanear_termo_busca(s: str) -> str:
    if not s: return ""
    s = s.replace('\ufffd', ' ')
    toks = re.split(r"\s+", s.strip())
    toks_limpos = [t for t in toks if len(t) >= 3 and t.lower() not in STOPWORDS_NOME]
    resultado = " ".join(toks_limpos)
    if len(resultado) < 3: return ""
    return resultado

def _tokens_nome(nome: str):
    return [t for t in re.split(r"\s+", nome.strip()) if len(t) >= 2]

def _gerar_variacoes_inteligentes(nome_original: str):
    variacoes = []
    nome_original = str(nome_original).strip()
    
    # 1. E-mail
    if "@" in nome_original and "." in nome_original and " " not in nome_original:
        logging.info(f"📧 Detectado E-mail. Usando busca exata: '{nome_original}'")
        return [nome_original]

    # 2. Documento (CPF/CNPJ)
    apenas_numeros = re.sub(r'\D', '', nome_original)
    if apenas_numeros and (len(apenas_numeros) == 11 or len(apenas_numeros) == 14):
        doc_formatado = _formatar_documento(apenas_numeros)
        logging.info(f"🔢 Detectado Documento. Formatado: '{doc_formatado}'")
        return [doc_formatado]

    # 3. Nome
    nome_limpo = normalizar_nome(nome_original, remover_invalidos=True)
    toks = _tokens_nome(nome_limpo)

    if not toks:
        return [nome_original] if len(nome_original) >= 3 else []

    if len(toks) >= 2:
        variacoes.append(f"{toks[0]} {toks[1]}")
        variacoes.append(f"{toks[0]} {toks[-1]}")

    ultimo = toks[-1]
    if len(ultimo) >= 3 and ultimo not in SOBRENOMES_COMUNS_IGNORAR:
        variacoes.append(ultimo)

    if len(toks) >= 3:
        variacoes.append(" ".join(toks))

    if len(toks[0]) >= 3:
        variacoes.append(toks[0])

    sanitizado = _sanear_termo_busca(nome_limpo)
    if sanitizado:
        variacoes.append(sanitizado)

    return list(dict.fromkeys(variacoes))[:10]

def _clicar_seguro(driver, seletor, timeout=5):
    try:
        el = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.CSS_SELECTOR, seletor)))
        el.click()
        return True
    except:
        return False

def _garantir_aba_clientes(driver):
    """
    Verifica se a aba 'Clientes' está ativa e clica nela se não estiver.
    Isso atende ao requisito de navegar para Clientes antes de buscar.
    """
    try:
        # Verifica se a aba Clientes existe
        aba = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, SELETORES["tab_clientes"])))
        
        # Verifica se já está ativa (classe zd_v2-topmenu-menuItemActive)
        classes = aba.get_attribute("class") or ""
        if "zd_v2-topmenu-menuItemActive" in classes:
            logging.debug("Aba 'Clientes' já está ativa.")
            return True
        
        logging.info("Navegando para a aba 'Clientes'...")
        try:
            aba.click()
        except:
            driver.execute_script("arguments[0].click();", aba)
            
        time.sleep(2) # Pausa para carregamento da lista
        return True
    except Exception as e:
        logging.warning(f"Não foi possível ativar a aba Clientes: {e}")
        return False

# --- FUNÇÃO PRINCIPAL DE BUSCA ---

def buscar_e_abrir_cliente(driver, nome_cliente):
    wait = WebDriverWait(driver, 15)
    short_wait = WebDriverWait(driver, 5)
    
    # 1. GARANTIR QUE ESTAMOS NA ABA CLIENTES (NOVA ETAPA)
    _garantir_aba_clientes(driver)
    
    # 2. Gerar variações de busca
    variacoes = _gerar_variacoes_inteligentes(nome_cliente)
    if not variacoes:
        logging.warning(f"Nenhuma variação válida para busca de: {nome_cliente}")
        return False
    
    logging.info(f"🔍 Iniciando busca por: '{variacoes[0]}' ({len(variacoes)} tentativas)")

    # 3. Abrir barra de pesquisa
    try:
        _clicar_seguro(driver, SELETORES["icone_pesquisa"], timeout=3)
        barra_pesquisa = short_wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, SELETORES["barra_pesquisa"])))
    except TimeoutException:
        logging.error("Não foi possível abrir a barra de pesquisa.")
        return False

    # 4. Loop de tentativas
    for tentativa, termo in enumerate(variacoes, 1):
        is_email = "@" in termo
        is_doc = not is_email and any(c.isdigit() for c in termo)
        termo_busca = termo if (is_email or is_doc) else _sanear_termo_busca(termo)
        
        if len(termo_busca) < 3: continue

        logging.info(f"Tentativa {tentativa}: Buscando por '{termo_busca}'")

        try:
            # Limpar e Digitar
            barra_pesquisa.click()
            barra_pesquisa.send_keys(Keys.CONTROL, "a")
            barra_pesquisa.send_keys(Keys.DELETE)
            time.sleep(0.2)

            # Delay adaptativo
            if len(termo_busca) <= 5: delay = DELAY_DIGITACAO_CURTA
            elif len(termo_busca) <= 10: delay = DELAY_DIGITACAO_MEDIA
            else: delay = DELAY_DIGITACAO_LONGA
            
            for letra in termo_busca:
                barra_pesquisa.send_keys(letra)
                time.sleep(delay)
            
            time.sleep(0.5)
            barra_pesquisa.send_keys(Keys.ENTER)
            
            # Aguardar Resultados
            try:
                WebDriverWait(driver, 10).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-title]")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, SELETORES["msg_sem_resultados"]))
                    )
                )
            except TimeoutException:
                logging.warning("Timeout esperando resultados.")
                continue

            # Validar Resultados
            if driver.find_elements(By.CSS_SELECTOR, SELETORES["msg_sem_resultados"]):
                if driver.find_element(By.CSS_SELECTOR, SELETORES["msg_sem_resultados"]).is_displayed():
                    continue 

            # Verificar lista de resultados
            if is_email:
                linhas = driver.find_elements(By.CSS_SELECTOR, SELETORES["linha_resultado"])
                for linha in linhas:
                    if termo_busca.lower() in linha.text.lower():
                        logging.info(f"✅ E-mail encontrado: '{termo_busca}'")
                        try:
                            link = linha.find_element(By.CSS_SELECTOR, "a[data-title]")
                            driver.execute_script("arguments[0].click();", link)
                            WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.CSS_SELECTOR, SELETORES["botao_whatsapp"])))
                            return True
                        except: pass
            else:
                resultados = driver.find_elements(By.CSS_SELECTOR, "a[data-title]")
                for res in resultados:
                    try:
                        titulo = res.get_attribute("data-title") or res.text
                        if not titulo: continue
                        
                        if is_doc:
                            numeros_titulo = re.sub(r'\D', '', titulo)
                            numeros_busca = re.sub(r'\D', '', termo_busca)
                            match = (numeros_titulo == numeros_busca) and len(numeros_busca) > 0
                        else:
                            titulo_norm = normalizar_nome(titulo)
                            busca_norm = normalizar_nome(termo_busca)
                            match = (busca_norm in titulo_norm) or (SequenceMatcher(None, busca_norm, titulo_norm).ratio() > 0.85)

                        if match:
                            logging.info(f"✅ ENCONTRADO: '{titulo}'")
                            try:
                                driver.execute_script("arguments[0].click();", res)
                            except:
                                res.click()
                            WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.CSS_SELECTOR, SELETORES["botao_whatsapp"])))
                            return True
                            
                    except StaleElementReferenceException:
                        continue
                    
        except Exception as e:
            logging.error(f"Erro na busca: {e}")
            try:
                barra_pesquisa = driver.find_element(By.CSS_SELECTOR, SELETORES["barra_pesquisa"])
            except: pass

    logging.warning(f"❌ Cliente '{nome_cliente}' não encontrado.")
    return False