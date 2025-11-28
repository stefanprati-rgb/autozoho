# Script de Backup - AutoZoho
# Cria backups timestamped de arquivos importantes antes de modificações

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = "backups/backup_$timestamp"

Write-Host "Criando backups em: $backupDir" -ForegroundColor Cyan

# Criar diretório de backup
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

# Arquivos para backup
$arquivos = @(
    "core/processing.py",
    "core/messaging.py",
    "main.py",
    "utils/telefone.py",
    "config/constants.py"
)

$sucessos = 0
$total = $arquivos.Count

foreach ($arquivo in $arquivos) {
    $origem = $arquivo
    
    if (Test-Path $origem) {
        $destino = Join-Path $backupDir $arquivo
        $destinoDir = Split-Path $destino -Parent
        
        # Criar diretório de destino se não existir
        if (!(Test-Path $destinoDir)) {
            New-Item -ItemType Directory -Path $destinoDir -Force | Out-Null
        }
        
        # Copiar arquivo
        Copy-Item $origem $destino -Force
        Write-Host "Backup criado: $arquivo" -ForegroundColor Green
        $sucessos++
    }
    else {
        Write-Host "Arquivo nao encontrado: $arquivo" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Backup concluido: $sucessos/$total arquivos" -ForegroundColor Cyan
Write-Host "Localizacao: $backupDir" -ForegroundColor Cyan
