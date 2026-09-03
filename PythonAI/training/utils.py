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


def get_unity_headless_cwd() -> str:
    """
    Retourne le working directory depuis lequel lancer le binaire Unity.
    Unity cherche ses fichiers data (*_Data/) relativement au CWD.
    Sur Linux (Colab/Databricks), il faut que le CWD soit le dossier
    contenant le binaire, pas PythonAI/.
    """
    headless_path = get_unity_headless_path()
    return os.path.dirname(headless_path)


def get_unity_popen_args(port: int) -> tuple[list, dict]:
    """
    Retourne (cmd_args, popen_kwargs) adaptes a l OS pour lancer le jeu headless.
    
    NOTE: Le binaire Headless est une application C# .NET autonome (pas un build Unity standard).
    Il n'a pas besoin de -batchmode ni de -nographics, et ne possede pas de dossier _Data/.
    """
    headless_path = get_unity_headless_path()
    cmd = [headless_path, f"tcp://127.0.0.1:{port}"]
    kwargs = {}

    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    else:
        # CWD = racine du projet (l'application C# peut chercher des chemins relatifs)
        kwargs["cwd"] = get_project_root()
        
        # FIX pour le crash SIGSEGV (PAL_SEHException) sur Colab/Docker
        # Les applications .NET autonomes crashent souvent sur des Linux minimalistes
        # a cause de la globalisation (ICU) ou du Garbage Collector (cgroups).
        env = os.environ.copy()
        env["DOTNET_SYSTEM_GLOBALIZATION_INVARIANT"] = "1"
        env["DOTNET_gcServer"] = "0"
        kwargs["env"] = env

    return cmd, kwargs


def make_popen_kwargs() -> dict:
    """
    Retourne les kwargs supplementaires pour subprocess.Popen selon l OS.
    Windows : masque la fenetre console du processus Unity.
    Linux   : pas de kwargs supplementaires.
    DEPRECATED : utiliser get_unity_popen_args() pour les lancements Unity.
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


def get_num_envs() -> int:
    """
    Retourne le nombre d instances Unity a lancer en parallele.
    Configurable via AUTOMATHON_NUM_ENVS.
    Defaut : min(os.cpu_count(), 16) pour ne pas surcharger les VMs Colab.
    """
    default = min(os.cpu_count() or 2, 16)
    return int(os.environ.get("AUTOMATHON_NUM_ENVS", str(default)))


def get_startup_wait() -> int:
    """
    Nombre de secondes a attendre apres le lancement de Unity.
    Sur Colab/Databricks les VMs sont plus lentes, 15s est plus sur.
    Configurable via AUTOMATHON_STARTUP_WAIT. Defaut : 15.
    """
    return int(os.environ.get("AUTOMATHON_STARTUP_WAIT", "15"))


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
