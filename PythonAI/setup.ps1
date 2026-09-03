# =============================================================================
# setup.ps1 - Automathon Windows Setup
# Telecharge les binaires Unity depuis GitHub Releases.
#
# Usage : ./PythonAI/setup.ps1
#   ou depuis PythonAI/ : ./setup.ps1
# =============================================================================

$ErrorActionPreference = "Stop"

$ReleaseUrl  = "https://github.com/antorchn/automathon_2k26/releases/latest/download"
$Asset       = "automathon-game-windows.zip"
$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path   # PythonAI/
$ProjectRoot = Split-Path -Parent $ScriptDir                      # racine du projet
$TmpPath     = "$env:TEMP\$Asset"

Write-Host "=== Automathon Setup (Windows) ===" -ForegroundColor Cyan
Write-Host "Projet       : $ProjectRoot"
Write-Host "Release URL  : $ReleaseUrl"
Write-Host ""

# ---------- Telechargement ----------
Write-Host "[1/3] Telechargement de $Asset..." -ForegroundColor Yellow
Invoke-WebRequest -Uri "$ReleaseUrl/$Asset" -OutFile $TmpPath -UseBasicParsing

# ---------- Extraction ----------
Write-Host "[2/3] Extraction dans $ProjectRoot..." -ForegroundColor Yellow
Expand-Archive -Path $TmpPath -DestinationPath $ProjectRoot -Force

# ---------- Verification ----------
Write-Host "[3/3] Verification..." -ForegroundColor Yellow
$headlessPath = Join-Path $ProjectRoot "Headless\Headless.exe"
$gamePath     = Join-Path $ProjectRoot "AutomathonGame.exe"

if (Test-Path $headlessPath) {
    Write-Host "  OK : Headless\Headless.exe" -ForegroundColor Green
} else {
    Write-Warning "  Headless\Headless.exe introuvable apres extraction."
}
if (Test-Path $gamePath) {
    Write-Host "  OK : AutomathonGame.exe" -ForegroundColor Green
} else {
    Write-Warning "  AutomathonGame.exe introuvable apres extraction."
}

# ---------- Dependances Python ----------
Write-Host ""
Write-Host "Installation des dependances Python..."
pip install -r "$ScriptDir\requirements_participant.txt" --quiet

Write-Host ""
Write-Host "Setup termine !" -ForegroundColor Green
Write-Host ""
Write-Host "  Lancer le jeu        : Double-cliquer sur AutomathonGame.exe"
Write-Host "  Lancer un agent      : cd PythonAI; python agents\run_my_agent.py"
Write-Host "  Lancer entrainement  : cd PythonAI; python training\rl_training.py"
Write-Host ""
Write-Host "Variables d environnement disponibles :"
Write-Host "  set AUTOMATHON_PORT_BASE=5600        # Changer si conflit de ports"
Write-Host "  set AUTOMATHON_CHECKPOINT_DIR=C:\..  # Dossier des checkpoints"
