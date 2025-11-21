# -*- coding: utf-8 -*-
import os
import csv
import time
import openpyxl
import tkinter as tk
from tkinter import filedialog
import logging

def carregar_lista_clientes_completos(caminho_arquivo):
    """
    Carrega a lista de clientes como objetos completos (dicionários).
    Retorna lista de dicts: [{'busca': '...', 'nome': '...', 'email': '...', 'telefone': '...'}, ...]
    """
    if not caminho_arquivo:
        root = tk.Tk()
        root.withdraw()
        caminho_arquivo = filedialog.askopenfilename(
            title="Selecione a lista de clientes",
            filetypes=(("Arquivos Excel", "*.xlsx"), ("Arquivos CSV", "*.csv"), ("Texto", "*.txt"))
        )
        root.destroy()

    if not caminho_arquivo:
        logging.warning("Nenhum arquivo selecionado.")
        return []

    clientes = []
    try:
        if caminho_arquivo.lower().endswith('.xlsx'):
            wb = openpyxl.load_workbook(caminho_arquivo, data_only=True)
            sheet = wb.active
            
            # Identifica cabeçalhos
            headers = [str(c.value).strip().upper() if c.value else f"COL_{i}" for i, c in enumerate(sheet[1])]
            
            # Mapeia colunas importantes
            col_map = {}
            for idx, h in enumerate(headers):
                if any(x in h for x in ['CNPJ', 'CPF', 'DOCUMENTO']): col_map['doc'] = idx
                elif any(x in h for x in ['NOME', 'CLIENTE', 'RAZÃO', 'RAZAO']): col_map['nome'] = idx
                elif 'EMAIL' in h or 'E-MAIL' in h: col_map['email'] = idx
                elif 'TELEFONE' in h or 'CELULAR' in h: col_map['telefone'] = idx
                elif 'INSTALAÇÃO' in h or 'INSTALACAO' in h: col_map['instalacao'] = idx

            # Se não achou coluna de busca principal (doc), usa a primeira
            if 'doc' not in col_map and 'nome' not in col_map:
                col_map['busca'] = 0
            
            for row in sheet.iter_rows(min_row=2, values_only=True):
                if not any(row): continue # Pula linha vazia
                
                cliente = {}
                # Define o termo principal de busca (prioridade: Doc > Instalação > Nome)
                if 'doc' in col_map and row[col_map['doc']]:
                    cliente['busca'] = str(row[col_map['doc']]).strip()
                elif 'instalacao' in col_map and row[col_map['instalacao']]:
                    cliente['busca'] = str(row[col_map['instalacao']]).strip()
                elif 'nome' in col_map and row[col_map['nome']]:
                    cliente['busca'] = str(row[col_map['nome']]).strip()
                else:
                    cliente['busca'] = str(row[0]).strip()

                # Preenche dados auxiliares para validação
                if 'nome' in col_map: cliente['nome_excel'] = str(row[col_map['nome']]).strip()
                if 'email' in col_map: cliente['email_excel'] = str(row[col_map['email']]).strip()
                if 'telefone' in col_map: cliente['telefone_excel'] = str(row[col_map['telefone']]).strip()
                
                clientes.append(cliente)
                    
        elif caminho_arquivo.lower().endswith('.csv'):
            # Lógica similar para CSV (simplificada)
            with open(caminho_arquivo, newline='', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';') # Assume ; padrão Brasil
                for row in reader:
                    # Normaliza chaves para minúsculo
                    row_lower = {k.lower(): v for k, v in row.items() if k}
                    
                    # Encontra termo de busca
                    busca = None
                    for k in ['cnpj', 'cpf', 'documento', 'instalação', 'nome']:
                        if k in row_lower and row_lower[k]:
                            busca = row_lower[k].strip()
                            break
                    if not busca: busca = list(row.values())[0] # Pega primeira coluna
                    
                    cliente = {'busca': busca}
                    # Tenta extrair dados auxiliares
                    for k, v in row_lower.items():
                        if 'nome' in k: cliente['nome_excel'] = v
                        if 'email' in k: cliente['email_excel'] = v
                        if 'telefone' in k: cliente['telefone_excel'] = v
                    
                    clientes.append(cliente)

        # Remove duplicados pela chave de busca
        seen = set()
        unicos = []
        for c in clientes:
            if c['busca'] not in seen:
                unicos.append(c)
                seen.add(c['busca'])
                
        return unicos

    except Exception as e:
        logging.error(f"Erro ao ler arquivo: {e}")
        return []

# Alias para compatibilidade
carregar_lista_clientes = carregar_lista_clientes_completos