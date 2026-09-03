import os
import sys
import subprocess
import time
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.vec_env import SubprocVecEnv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.env.automathon_env import AutomathonEnv
from agents.neural_expert_bot.feature_extractor import extract_features
from training.utils import get_unity_headless_path, make_popen_kwargs, get_port_base, get_checkpoint_dir


class DynamicOpponentCallback(BaseCallback):
    """
    Change l'adversaire de l'environnement périodiquement (Curriculum Learning).
    """
    def __init__(self, switch_freq: int = 10000, verbose=0):
        super().__init__(verbose)
        self.switch_freq = switch_freq
        self.opponents = ["rush_bot", "smart_dash_bot", "expert_master_bot"]
        self.current_idx = 0

    def _on_step(self) -> bool:
        if self.n_calls % self.switch_freq == 0:
            self.current_idx = (self.current_idx + 1) % len(self.opponents)
            new_opp_name = self.opponents[self.current_idx]
            self.training_env.env_method("set_opponent_by_name", new_opp_name)
            if self.verbose > 0:
                print(f"\n[Callback] Changement d'adversaire pour tous les envs : {new_opp_name}")
        return True


def make_env(port: int, unity_exe_path: str):
    """
    Fonction constructeur pour SubprocVecEnv.
    Lance une instance Unity Headless unique sur un port unique.
    Compatible Windows et Linux.
    """
    def _init():
        print(f"Lancement de Unity sur le port {port}...")
        process = subprocess.Popen(
            [unity_exe_path, f"tcp://127.0.0.1:{port}"],
            **make_popen_kwargs()
        )
        time.sleep(5)

        env = AutomathonEnv(tcp_port=str(port), extractor_fn=extract_features)

        # Monkey patch du close() pour tuer le processus Unity quand le VecEnv se ferme
        original_close = env.close
        def new_close():
            for fn in [original_close, env.game.end_training, process.kill]:
                try:
                    fn()
                except Exception:
                    pass
        env.close = new_close

        return env
    return _init


def main():
    from stable_baselines3.common.callbacks import CheckpointCallback

    num_envs = 16
    start_port = get_port_base()
    unity_exe_path = get_unity_headless_path()

    print(f"Binaire Unity    : {unity_exe_path}")
    print(f"Ports            : {start_port} → {start_port + num_envs - 1}")
    print(f"Création de {num_envs} environnements en parallèle...")

    env = SubprocVecEnv([make_env(start_port + i, unity_exe_path) for i in range(num_envs)])

    bc_model_path = os.path.join(os.path.dirname(__file__), "bc_model.zip")
    tensorboard_log = os.path.join(os.path.dirname(__file__), "tensorboard")

    if os.path.exists(bc_model_path):
        print("Chargement du modèle pré-entraîné (Behavioral Cloning)...")
        model = PPO.load(bc_model_path, env=env, tensorboard_log=tensorboard_log)
    else:
        print("Attention : bc_model.zip introuvable. Démarrage from scratch.")
        model = PPO("MlpPolicy", env, verbose=1, tensorboard_log=tensorboard_log)

    # Checkpoint périodique — critique sur Databricks pour protéger contre les interruptions.
    # Configurable via AUTOMATHON_CHECKPOINT_DIR (ex: /dbfs/FileStore/automathon/mon_equipe)
    checkpoint_dir = get_checkpoint_dir()
    os.makedirs(checkpoint_dir, exist_ok=True)
    print(f"Checkpoints      : {checkpoint_dir}")

    checkpoint_callback = CheckpointCallback(
        save_freq=max(50_000 // num_envs, 1),
        save_path=checkpoint_dir,
        name_prefix="rl_model_checkpoint",
        verbose=1
    )
    curriculum_callback = DynamicOpponentCallback(switch_freq=20000, verbose=1)

    try:
        print(f"\nDébut du Reinforcement Learning sur {num_envs} cœurs...")
        model.learn(total_timesteps=2_000_000, callback=[curriculum_callback, checkpoint_callback])

        save_path = os.path.join(os.path.dirname(__file__), "rl_model.zip")
        model.save(save_path)
        print(f"Entraînement terminé. Modèle sauvegardé : {save_path}")
    except KeyboardInterrupt:
        print("\nEntraînement interrompu. Sauvegarde de sécurité...")
        save_path = os.path.join(os.path.dirname(__file__), "rl_model_interrupted.zip")
        model.save(save_path)
    finally:
        print("Fermeture de tous les environnements Unity...")
        env.close()


if __name__ == "__main__":
    main()
