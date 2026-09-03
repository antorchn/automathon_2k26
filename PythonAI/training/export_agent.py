import os
import sys
import zipfile
import shutil
import datetime
import argparse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TRAINING_DIR  = os.path.dirname(os.path.abspath(__file__))
PYTHON_AI_DIR = os.path.dirname(TRAINING_DIR)

def find_model(model_path: str = None) -> str:
    """Trouve le meilleur modele disponible."""
    if model_path and os.path.exists(model_path):
        return model_path
    candidates = [
        os.path.join(TRAINING_DIR, "rl_model.zip"),
        os.path.join(TRAINING_DIR, "rl_model_interrupted.zip"),
        os.path.join(TRAINING_DIR, "bc_model.zip"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None

def find_agent_files(agent_folder: str) -> list[tuple[str, str]]:
    """Retourne les fichiers de l agent a embarquer dans le zip."""
    agent_dir = os.path.join(PYTHON_AI_DIR, "agents", agent_folder)
    if not os.path.isdir(agent_dir):
        raise FileNotFoundError(f"Dossier agent introuvable : {agent_dir}")
    files = []
    for fname in os.listdir(agent_dir):
        if fname.endswith(".py") and not fname.startswith("__"):
            src = os.path.join(agent_dir, fname)
            arc = f"agents/{agent_folder}/{fname}"
            files.append((src, arc))
    return files

def download_in_environment(zip_path: str):
    """Declenche le telechargement si execution dans Colab ou Databricks."""
    # --- Google Colab ---
    try:
        from google.colab import files
        print(f"  Colab detecte. Telechargement en cours...")
        files.download(zip_path)
        return
    except ImportError:
        pass

    # --- Databricks ---
    try:
        import IPython
        ip = IPython.get_ipython()
        if ip is not None:
            # Copier vers DBFS si disponible
            dbfs_dir = os.environ.get("AUTOMATHON_CHECKPOINT_DIR", "/dbfs/FileStore/automathon/exports")
            os.makedirs(dbfs_dir, exist_ok=True)
            dest = os.path.join(dbfs_dir, os.path.basename(zip_path))
            shutil.copy2(zip_path, dest)
            dbfs_url = dest.replace("/dbfs", "/files")
            print(f"  Databricks detecte. Fichier copie dans DBFS :")
            print(f"  {dest}")
            print(f"  Lien de telechargement : {dbfs_url}")
            return
    except Exception:
        pass

    print(f"  Fichier disponible localement : {zip_path}")

def main():
    parser = argparse.ArgumentParser(description="Exporte un agent entraine en archive portable.")
    parser.add_argument(
        "agent_folder",
        nargs="?",
        default="neural_expert_bot",
        help="Nom du dossier agent dans agents/ (defaut: neural_expert_bot)"
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Chemin vers le fichier modele .zip (defaut: recherche automatique)"
    )
    args = parser.parse_args()

    print("=== Automathon — Export Agent ===")
    print(f"Agent        : {args.agent_folder}")

    # 1. Trouver le modele
    model_path = find_model(args.model)
    if not model_path:
        print("ERREUR : Aucun modele entraine trouve dans training/")
        print("  Lancez d abord : python training/rl_training.py")
        sys.exit(1)
    print(f"Modele       : {os.path.basename(model_path)}")

    # 2. Trouver les fichiers de l agent
    try:
        agent_files = find_agent_files(args.agent_folder)
    except FileNotFoundError as e:
        print(f"ERREUR : {e}")
        sys.exit(1)

    # 3. Construire l archive
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name  = f"mon_agent_{timestamp}.zip"
    zip_path  = os.path.join(TRAINING_DIR, zip_name)

    instructions_src = os.path.join(TRAINING_DIR, "IMPORT_INSTRUCTIONS.md")

    print(f"Creation de  : {zip_name}")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Modele entraine
        zf.write(model_path, "training/rl_model.zip")
        # Code de l agent
        for src, arc in agent_files:
            zf.write(src, arc)
        # Instructions
        if os.path.exists(instructions_src):
            zf.write(instructions_src, "IMPORT_INSTRUCTIONS.md")

    size_kb = os.path.getsize(zip_path) / 1024
    print(f"Taille       : {size_kb:.1f} Ko")
    print("")

    # 4. Telechargement automatique si environnement cloud
    download_in_environment(zip_path)

    print("")
    print("Pour tester votre agent sur votre PC :")
    print("  1. Placez training/rl_model.zip dans PythonAI/training/rl_model.zip")
    print("  2. cd PythonAI && python agents/run_my_agent.py")
    print("  3. Lancez AutomathonGame.exe / AutomathonGame")

if __name__ == "__main__":
    main()
