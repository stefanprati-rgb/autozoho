# -*- coding: utf-8 -*-
import time
import re
import logging
from difflib import SequenceMatcher
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, ElementNotInteractableException

# Configurações de Delay
DELAY_DIGITACAO_CURTA = 0.05
DELAY_DIGITACAO_MEDIA = 0.08
DELAY_DIGITACAO_LONGA = 0.10

SELETORES = {
    "icone_pesquisa": 'button[data-id="globalSearchIcon"]',
    "barra_pesquisa": 'input[data-id="searchInput"]',
    "msg_sem_resultados": 'div.zd_v2-commonemptystate-title',
    "botao_whatsapp": 'span[data-title="Enviar mensagens via WhatsApp (canal de IM)"]',
    
    # ATUALIZADO: Seletor específico da lista PRINCIPAL (corpo da página)
    "linha_resultado": 'div.zd_v2-modulelistnew-innerListDiv', 
    
    # Seletor para clicar no nome (dentro da linha)
    "link_nome_cliente": 'a[data-title]',
    
    "tab_clientes": 'a[data-id="qtab_Contacts_Tab"]'
}

STOPWORDS_NOME = {"de","da","do","dos","e","ltda","me","epp","s/a","sa"}

def _sanear_termo(s):
    if not s: return ""
    return str(s).strip().lower()

def _tokens_nome(nome):
    return [t for t in re.split(r"\s+", str(nome).strip()) if len(t) >= 2]

def normalizar_nome(nome):
    if not nome: return ""
    return str(nome).lower().strip()

def _gerar_variacoes_inteligentes(dados_cliente):
    tipo = dados_cliente.get('tipo_busca', 'auto')
    valor = str(dados_cliente.get('busca', '')).strip()
    variacoes = []

    if tipo == 'email':
        logging.info(f"📧 Buscando por E-mail: {valor}")
        return [valor]

    elif tipo == 'telefone':
        nums = re.sub(r'\D', '', valor)
        logging.info(f"📞 Buscando por Telefone: {nums}")
        return [nums]

    elif tipo == 'doc':
        nums = re.sub(r'\D', '', valor)
        if len(nums) == 11:
            fmt = f"{nums[:3]}.{nums[3:6]}.{nums[6:9]}-{nums[9:]}"
            return [fmt]
        elif len(nums) == 14:
            fmt = f"{nums[:2]}.{nums[2:5]}.{nums[5:8]}/{nums[8:12]}-{nums[12:]}"
            return [fmt]
        return [valor]

    nome_limpo = normalizar_nome(valor)
    toks = _tokens_nome(nome_limpo)
    
    if not toks: return [valor]

    if len(toks) >= 2:
        variacoes.append(f"{toks[0]} {toks[1]}")
        variacoes.append(f"{toks[0]} {toks[-1]}")
    
    variacoes.append(valor)
    variacoes.append(toks[0])
    
    return list(dict.fromkeys(variacoes))[:6]

def _validar_resultado(elemento_linha, dados_cliente):
    """
    Validação Cruzada com Logs Detalhados.
    """
    try:
        # Pega o texto completo da linha para procurar email/telefone
        texto_linha = elemento_linha.text.lower()
        # Log para debug (ver o que o robô está lendo)
        logging.info(f"   👀 Analisando linha: {texto_linha[:60]}...") 
    except:
        return False

    pontos = 0
    criterios = 0
    
    # Valida E-mail
    if dados_cliente.get('email_excel'):
        criterios += 1
        email_alvo = _sanear_termo(dados_cliente['email_excel'])
        if email_alvo in texto_linha:
            logging.info(f"      ✅ E-mail '{email_alvo}' encontrado na linha.")
            pontos += 3

    # Valida Telefone
    if dados_cliente.get('telefone_excel'):
        criterios += 1
        tel_alvo = re.sub(r'\D', '', str(dados_cliente['telefone_excel']))
        if len(tel_alvo) >= 4 and tel_alvo[-4:] in texto_linha:
            logging.info(f"      ✅ Telefone final '...{tel_alvo[-4:]}' encontrado.")
            pontos += 3

    # Valida Nome
    if dados_cliente.get('nome_excel') and dados_cliente.get('tipo_busca') != 'nome':
        criterios += 1
        nome_alvo = _sanear_termo(dados_cliente['nome_excel']).split()[0]
        if nome_alvo in texto_linha:
            logging.info(f"      ✅ Nome '{nome_alvo}' encontrado.")
            pontos += 2

    if criterios == 0:
        return True # Sem dados para validar, aceita o resultado da busca
    
    return pontos > 0

def buscar_e_abrir_cliente(driver, dados_cliente):
    wait = WebDriverWait(driver, 15)
    short_wait = WebDriverWait(driver, 5)
    
    # 1. Garante Aba Clientes
    try:
        aba = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, SELETORES["tab_clientes"])))
        if "zd_v2-topmenu-menuItemActive" not in (aba.get_attribute("class") or ""):
            driver.execute_script("arguments[0].click();", aba)
            time.sleep(2)
    except: pass

    # 2. Abre Pesquisa (LÓGICA BLINDADA)
    campo = None
    try:
        # Tenta encontrar o campo diretamente primeiro (evita clicar na lupa se já aberto)
        possiveis_campos = driver.find_elements(By.CSS_SELECTOR, SELETORES["barra_pesquisa"])
        for c in possiveis_campos:
            if c.is_displayed() and c.is_enabled():
                campo = c
                campo.click() # Foca para garantir
                logging.debug("Campo de pesquisa já estava visível.")
                break
        
        # Se não achou ou não conseguiu clicar, clica na lupa
        if not campo:
            logging.debug("Campo não encontrado, clicando na lupa...")
            driver.find_element(By.CSS_SELECTOR, SELETORES["icone_pesquisa"]).click()
            campo = short_wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, SELETORES["barra_pesquisa"])))
            campo.click()

    except Exception as e:
        logging.error(f"Erro crítico ao acessar barra de pesquisa: {e}")
        # Tenta uma última recuperação forçada via JS
        try:
            js_campo = driver.find_element(By.CSS_SELECTOR, SELETORES["barra_pesquisa"])
            driver.execute_script("arguments[0].value = ''; arguments[0].focus();", js_campo)
            campo = js_campo
        except:
            return False

    variacoes = _gerar_variacoes_inteligentes(dados_cliente)
    
    for termo in variacoes:
        logging.info(f"🔎 Buscando por: '{termo}'")
        
        try:
            # Limpar e Digitar
            campo.send_keys(Keys.CONTROL, "a")
            campo.send_keys(Keys.DELETE)
            time.sleep(0.3)
            
            delay = DELAY_DIGITACAO_LONGA if len(termo) > 10 else DELAY_DIGITACAO_MEDIA
            for letra in termo:
                campo.send_keys(letra)
                time.sleep(delay)
            
            time.sleep(0.5)
            campo.send_keys(Keys.ENTER)
            
            # PAUSA MAIOR PARA CARREGAR A LISTA PRINCIPAL
            logging.debug("Aguardando carregamento da lista principal...")
            time.sleep(3.5) 
            
            # Tenta pegar a lista principal (do corpo da página)
            linhas = driver.find_elements(By.CSS_SELECTOR, SELETORES["linha_resultado"])
            
            if not linhas:
                # Verifica se tem mensagem de "sem resultados"
                try:
                    if driver.find_element(By.CSS_SELECTOR, SELETORES["msg_sem_resultados"]).is_displayed():
                        logging.warning("Zoho indicou 'Sem resultados'.")
                        continue
                except: pass
                logging.warning("Nenhuma linha de resultado encontrada após espera.")
                continue

            logging.info(f"   Encontradas {len(linhas)} linhas na tabela. Validando...")

            for linha in linhas:
                # Valida os dados
                if _validar_resultado(linha, dados_cliente):
                    try:
                        # Clica no link do NOME dentro dessa linha validada
                        link = linha.find_element(By.CSS_SELECTOR, SELETORES["link_nome_cliente"])
                        logging.info(f"   🖱️ Clicando em: {link.get_attribute('data-title')}")
                        
                        driver.execute_script("arguments[0].click();", link)
                        
                        # Sucesso se o botão do Whats aparecer
                        WebDriverWait(driver, 20).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, SELETORES["botao_whatsapp"]))
                        )
                        return True
                    except Exception as click_err:
                        logging.error(f"Erro ao clicar no resultado validado: {click_err}")
                        
        except Exception as e:
            logging.error(f"Erro durante tentativa de busca '{termo}': {e}")
            # Tenta recuperar referência do campo para próxima volta
            try: campo = driver.find_element(By.CSS_SELECTOR, SELETORES["barra_pesquisa"])
            except: pass

    return False