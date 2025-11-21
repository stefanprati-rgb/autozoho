# -*- coding: utf-8 -*-
import os
import csv
import openpyxl
import tkinter as tk
from tkinter import filedialog
import logging

def carregar_lista_clientes(caminho_arquivo):
    """
    Lê o arquivo e define a prioridade de busca: Email > Telefone > Nome.
    Retorna lista de dicionários completos.
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
        # Função auxiliar para identificar colunas
        def mapear_colunas(headers):
            m = {}
            for i, h in enumerate(headers):
                h = str(h).upper().strip()
                if 'EMAIL' in h or 'E-MAIL' in h: m['email'] = i
                elif any(x in h for x in ['TELEFONE', 'CELULAR', 'WHATSAPP']): m['telefone'] = i
                elif any(x in h for x in ['NOME', 'CLIENTE', 'RAZÃO', 'RAZAO']): m['nome'] = i
                elif any(x in h for x in ['CNPJ', 'CPF', 'DOCUMENTO']): m['doc'] = i
            return m

        if caminho_arquivo.lower().endswith('.xlsx'):
            wb = openpyxl.load_workbook(caminho_arquivo, data_only=True)
            sheet = wb.active
            
            # Lê cabeçalhos
            headers = [c.value for c in sheet[1]]
            col_map = mapear_colunas(headers)
            
            for row in sheet.iter_rows(min_row=2, values_only=True):
                if not any(row): continue
                
                cli = {}
                
                # Extrai dados brutos (se a coluna existir)
                val_email = str(row[col_map['email']]).strip() if 'email' in col_map and row[col_map['email']] else None
                val_tel = str(row[col_map['telefone']]).strip() if 'telefone' in col_map and row[col_map['telefone']] else None
                val_nome = str(row[col_map['nome']]).strip() if 'nome' in col_map and row[col_map['nome']] else None
                val_doc = str(row[col_map['doc']]).strip() if 'doc' in col_map and row[col_map['doc']] else None
                
                # --- LÓGICA DE PRIORIDADE (Email > Telefone > Nome) ---
                if val_email and '@' in val_email:
                    cli['busca'] = val_email
                    cli['tipo_busca'] = 'email'
                elif val_tel and len(val_tel) >= 8:
                    cli['busca'] = val_tel
                    cli['tipo_busca'] = 'telefone'
                elif val_nome and len(val_nome) > 2:
                    cli['busca'] = val_nome
                    cli['tipo_busca'] = 'nome'
                elif val_doc: # Fallback último caso
                    cli['busca'] = val_doc
                    cli['tipo_busca'] = 'doc'
                else:
                    # Se não achou nada específico, usa a primeira coluna
                    cli['busca'] = str(row[0]).strip()
                    cli['tipo_busca'] = 'auto'

                # Guarda dados auxiliares para validação
                if val_email: cli['email_excel'] = val_email
                if val_tel: cli['telefone_excel'] = val_tel
                if val_nome: cli['nome_excel'] = val_nome
                
                clientes.append(cli)

        elif caminho_arquivo.lower().endswith('.csv'):
            with open(caminho_arquivo, newline='', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';')
                for row in reader:
                    # Normaliza chaves do CSV
                    r = {k.upper(): v for k, v in row.items() if k}
                    
                    val_email = next((v for k,v in r.items() if 'EMAIL' in k), None)
                    val_tel = next((v for k,v in r.items() if 'TEL' in k or 'CEL' in k), None)
                    val_nome = next((v for k,v in r.items() if 'NOME' in k or 'RAZ' in k), None)
                    
                    cli = {}
                    if val_email and '@' in val_email:
                        cli['busca'] = val_email
                        cli['tipo_busca'] = 'email'
                    elif val_tel:
                        cli['busca'] = val_tel
                        cli['tipo_busca'] = 'telefone'
                    elif val_nome:
                        cli['busca'] = val_nome
                        cli['tipo_busca'] = 'nome'
                    else:
                        cli['busca'] = list(row.values())[0]
                        cli['tipo_busca'] = 'auto'
                        
                    if val_email: cli['email_excel'] = val_email
                    if val_tel: cli['telefone_excel'] = val_tel
                    if val_nome: cli['nome_excel'] = val_nome
                    
                    clientes.append(cli)

        # Remove duplicados
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