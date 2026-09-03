#!/usr/bin/env bash
# =============================================================================
# setup.sh — Automathon Linux / Databricks Setup
# Telecharge les binaires Unity depuis GitHub Releases.
#
# Usage:
#   bash PythonAI/setup.sh --headless   → Databricks / CI (binaire headless)
#   bash PythonAI/setup.sh --full       → PC Linux (headless + jeu graphique)
#   bash PythonAI/setup.sh              → defaut : --full
# =============================================================================
set -e

RELEASE_URL="https://github.com/antorchn/automathon_2k26/releases/latest/download"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"          # PythonAI/
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"         # racine du projet

MODE="${1:---full}"

echo "=== Automathon Setup (Linux) ==="
echo "Mode         : $MODE"
echo "Projet       : $PROJECT_ROOT"
echo "Release URL  : $RELEASE_URL"
echo ""

# ---------- Telechargement du binaire Unity ----------
if [ "$MODE" = "--headless" ]; then
    ASSET="automathon-headless-linux.tar.gz"
    echo "[1/3] Telechargement de $ASSET (binaire headless uniquement)..."
else
    ASSET="automathon-game-linux.tar.gz"
    echo "[1/3] Telechargement de $ASSET (headless + jeu graphique)..."
fi

TMP_FILE="/tmp/$ASSET"
curl -L --progress-bar "$RELEASE_URL/$ASSET" -o "$TMP_FILE"

# ---------- Extraction ----------
echo "[2/3] Extraction dans $PROJECT_ROOT..."
tar -xzf "$TMP_FILE" -C "$PROJECT_ROOT"

# ---------- Permissions ----------
echo "[3/3] Configuration des permissions..."
chmod +x "$PROJECT_ROOT/Headless/Headless" 2>/dev/null && \
    echo "  OK : Headless/Headless" || \
    echo "  AVERTISSEMENT : binaire Headless introuvable apres extraction."

if [ "$MODE" = "--full" ]; then
    chmod +x "$PROJECT_ROOT/AutomathonGame" 2>/dev/null && \
        echo "  OK : AutomathonGame" || \
        echo "  AVERTISSEMENT : AutomathonGame introuvable apres extraction."
fi

# ---------- Dependances Python ----------
echo ""
echo "Installation des dependances Python..."
pip install -r "$SCRIPT_DIR/requirements_participant.txt" --quiet

echo ""
echo "Setup termine !"
echo ""
if [ "$MODE" = "--full" ]; then
    echo "  Lancer le jeu       : $PROJECT_ROOT/AutomathonGame"
fi
echo "  Lancer un agent     : cd $SCRIPT_DIR && python agents/run_my_agent.py"
echo "  Lancer l'entrainement: cd $SCRIPT_DIR && python training/rl_training.py"
echo ""
echo "Variables d environnement disponibles :"
echo "  AUTOMATHON_PORT_BASE=5600        # Changer si conflit de ports (Databricks)"
echo "  AUTOMATHON_CHECKPOINT_DIR=/path  # Dossier des checkpoints (ex: /dbfs/...)"
echo "  AUTOMATHON_HEADLESS_PATH=/path   # Chemin custom vers le binaire Headless"
