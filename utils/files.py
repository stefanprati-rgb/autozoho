# -*- coding: utf-8 -*-
import os
import csv
import time
import openpyxl
import tkinter as tk
from tkinter import filedialog

def carregar_lista_clientes(caminho_arquivo):
    """Carrega a lista de clientes de um arquivo Excel, CSV ou TXT."""
    if not caminho_arquivo:
        # Se não passou arquivo, abre janela para escolher
        root = tk.Tk()
        root.withdraw()
        caminho_arquivo = filedialog.askopenfilename(
            title="Selecione a lista de clientes",
            filetypes=(("Arquivos Excel", "*.xlsx"), ("Arquivos CSV", "*.csv"), ("Texto", "*.txt"))
        )
        root.destroy()

    if not caminho_arquivo:
        print("Nenhum arquivo selecionado.")
        return []

    clientes = []
    try:
        if caminho_arquivo.lower().endswith('.xlsx'):
            wb = openpyxl.load_workbook(caminho_arquivo)
            sheet = wb.active
            
            # Tenta identificar coluna de CNPJ/CPF ou usa a primeira
            col_idx = 0
            headers = [c.value for c in sheet[1]]
            for i, h in enumerate(headers):
                if h and str(h).upper() in ['CNPJ', 'CPF', 'DOCUMENTO']:
                    col_idx = i
                    break
            
            for row in sheet.iter_rows(min_row=2, values_only=True):
                if row[col_idx]:
                    clientes.append(str(row[col_idx]).strip())
                    
        elif caminho_arquivo.lower().endswith('.csv'):
            with open(caminho_arquivo, newline='', encoding='utf-8-sig') as f:
                # Tenta detectar delimitador
                sample = f.read(1024)
                f.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample)
                except:
                    dialect = 'excel'
                
                reader = csv.reader(f, dialect)
                for row in reader:
                    if row:
                        clientes.append(row[0].strip())
                        
        else: # TXT
            with open(caminho_arquivo, 'r', encoding='utf-8') as f:
                clientes = [line.strip() for line in f if line.strip()]

        # Remove duplicados mantendo a ordem
        return list(dict.fromkeys(clientes))

    except Exception as e:
        print(f"Erro ao ler arquivo: {e}")
        return []