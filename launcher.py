# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import time

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    print("=" * 60)
    print("   AUTOZOHO - SISTEMA DE ENVIO AUTOMÁTICO DE MENSAGENS")
    print("=" * 60)
    print("\n")

def get_file_path():
    while True:
        print("📁  Passo 1: ARQUIVO DE CLIENTES")
        print("    Arraste o arquivo CSV ou Excel para esta janela e aperte ENTER.")
        file_path = input("    > ").strip()
        
        # Remove quotes if present (common when dragging files in Windows)
        if file_path.startswith('"') and file_path.endswith('"'):
            file_path = file_path[1:-1]
        
        if not file_path:
            print("\n❌  Por favor, forneça um arquivo válido.\n")
            continue
            
        if os.path.isfile(file_path):
            return file_path
        else:
            print(f"\n❌  O arquivo não foi encontrado: {file_path}")
            print("    Tente novamente.\n")

def select_mode():
    while True:
        print("\n⚙️   Passo 2: MODO DE OPERAÇÃO")
        print("    [1] Modo Padrão (Recomendado - Auto detecção)")
        print("    [2] Modo Avançado (Configurar Workers / Simulação)")
        
        choice = input("    >Escolha (1/2): ").strip()
        
        if choice == '1':
            return 'default'
        elif choice == '2':
            return 'advanced'
        else:
            print("\n❌  Opção inválida. Digite 1 ou 2.")

def get_advanced_options():
    options = []
    
    print("\n🔬  CONFIGURAÇÕES AVANÇADAS")
    
    # Workers
    print("\n    [Workers] Quantas janelas simultâneas? (1-4)")
    print("    Deixe em branco para Automático.")
    workers = input("    > ").strip()
    if workers and workers in ['1', '2', '3', '4']:
        options.append(f"--workers={workers}")
    
    # Dry run
    print("\n    [Simulação] Ativar modo DRY-RUN (Não envia mensagens)? (s/N)")
    dry = input("    > ").strip().lower()
    if dry == 's':
        options.append("--dry-run")
        
    # Resume
    print("\n    [Retomada] Forçar retomada de sessão anterior? (s/N)")
    resume = input("    > ").strip().lower()
    if resume == 's':
        options.append("--resume")
        
    return options

def main():
    clear_screen()
    print_header()
    
    try:
        # 1. Get File
        file_path = get_file_path()
        print(f"\n✅  Arquivo selecionado: {os.path.basename(file_path)}")
        
        # 2. Select Mode
        mode = select_mode()
        
        if mode == 'advanced':
            # Modo avançado: usa main_parallel.py com workers
            cmd_args = [sys.executable, "main_parallel.py", f"--arquivo={file_path}"]
            extra_args = get_advanced_options()
            cmd_args.extend(extra_args)
        else:
            # Modo padrão: usa main.py (single worker)
            cmd_args = [sys.executable, "main.py", f"--arquivo={file_path}"]
            
        # 3. Confirmation
        print("\n" + "-" * 60)
        print("🚀  PRONTO PARA INICIAR")
        print("-" * 60)
        print(f"    Comando: {' '.join(cmd_args)}")
        print("\n    Pressione ENTER para começar (ou Ctrl+C para sair)...")
        input()
        
        # 4. Execute
        print("\n🔄  Iniciando sistema...\n")
        subprocess.run(cmd_args)
        
    except KeyboardInterrupt:
        print("\n\n👋  Operação cancelada pelo usuário.")
    except Exception as e:
        print(f"\n❌  Erro inesperado: {e}")
        input("\nPressione ENTER para sair...")

if __name__ == "__main__":
    main()
