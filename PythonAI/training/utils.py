import os
import sys
import stat
import subprocess

# -----------------------------------------------------------------------------
# Utilitaires cross-platform partages entre rl_training.py et
# collect_demonstrations.py.
# -----------------------------------------------------------------------------

GITHUB_RELEASES_URL = "https://github.com/antorchn/automathon_2k26/releases/latest/download"


def get_project_root() -> str:
    """Retourne la racine du projet (dossier parent de PythonAI/)."""
    # utils.py est dans PythonAI/training/ -> remonter 2 niveaux
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_unity_headless_path() -> str:
    """
    Detecte l OS et retourne le chemin absolu vers le binaire Headless Unity.

    Priorite :
      1. Variable d environnement AUTOMATHON_HEADLESS_PATH (pour Databricks / DBFS)
      2. Chemin standard relatif a la racine du projet

    Raises FileNotFoundError si le binaire est introuvable.
    """
    env_path = os.environ.get("AUTOMATHON_HEADLESS_PATH")
    if env_path:
        path = env_path
    else:
        project_root = get_project_root()
        if sys.platform == "win32":
            path = os.path.join(project_root, "Headless", "Headless.exe")
        else:
            path = os.path.join(project_root, "Headless", "Headless")

    if not os.path.exists(path):
        if sys.platform == "win32":
            hint = "Lancez PythonAI/setup.ps1 pour telecharger les binaires."
        else:
            hint = "Lancez 'bash PythonAI/setup.sh --headless' pour telecharger le binaire."
        raise FileNotFoundError(
            f"Binaire Unity Headless introuvable : {path}\n{hint}\n"
            f"Ou definissez AUTOMATHON_HEADLESS_PATH pour pointer vers votre binaire."
        )

    # S assurer que le bit d execution est positionne sur Linux/macOS
    if sys.platform != "win32":
        current_mode = os.stat(path).st_mode
        os.chmod(path, current_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    return path


def make_popen_kwargs() -> dict:
    """
    Retourne les kwargs supplementaires pour subprocess.Popen selon l OS.
    Windows : masque la fenetre console du processus Unity.
    Linux   : pas de kwargs supplementaires.
    """
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


def get_port_base() -> int:
    """
    Retourne le port de base pour les instances Unity headless.
    Configurable via AUTOMATHON_PORT_BASE pour eviter les collisions
    entre participants sur un cluster Databricks partage.
    Defaut : 5600.
    """
    return int(os.environ.get("AUTOMATHON_PORT_BASE", "5600"))


def get_checkpoint_dir() -> str:
    """
    Retourne le repertoire de sauvegarde des checkpoints.
    Configurable via AUTOMATHON_CHECKPOINT_DIR.
    Sur Databricks : /dbfs/FileStore/automathon/checkpoints/<equipe>
    Defaut : PythonAI/training/checkpoints/
    """
    default = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "checkpoints"
    )
    return os.environ.get("AUTOMATHON_CHECKPOINT_DIR", default)
