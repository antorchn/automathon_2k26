import os
import sys
import subprocess
import time
import numpy as np
import importlib
from tqdm import tqdm
import concurrent.futures

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.env.automathon_env import AutomathonEnv
from bridge.datatypes import AIAction
from agents.neural_expert_bot.feature_extractor import extract_features
from training.utils import get_unity_headless_path, make_popen_kwargs, get_port_base

def action_to_numpy(action: AIAction) -> np.ndarray:
    """Convertit l'AIAction en vecteur continu 8D."""
    return np.array([
        action.MovingDirection.X / 1000.0,
        action.MovingDirection.Y / 1000.0,
        action.AimingDirection.X / 1000.0,
        action.AimingDirection.Y / 1000.0,
        1.0 if action.MachineGun else -1.0,
        1.0 if action.Missile else -1.0,
        1.0 if action.Shield else -1.0,
        1.0 if action.Dash else -1.0
    ], dtype=np.float32)

def load_agent_class(folder_name):
    module = importlib.import_module(f"agents.{folder_name}.agent")
    return module.ParticipantAgent

def collect_for_opponent(args):
    opp_name, port, num_games = args

    unity_exe_path = get_unity_headless_path()

    print(f"[{opp_name}] Lancement de Unity sur le port {port}...")
    process = subprocess.Popen(
        [unity_exe_path, f"tcp://127.0.0.1:{port}"],
        **make_popen_kwargs()
    )
    time.sleep(5)
    
    env = AutomathonEnv(tcp_port=str(port), extractor_fn=extract_features)
    
    expert_agent = load_agent_class("expert_master_bot")()
    opp_agent = load_agent_class(opp_name)()
    env.set_opponent(opp_agent)
    
    obs_list = []
    act_list = []
    
    try:
        print(f"[{opp_name}] Début des {num_games} matchs...")
        # tqdm avec position pour un affichage propre en multi-processing
        for _ in range(num_games):
            obs, _ = env.reset()
            done = False
            
            while not done:
                action = expert_agent.get_action(env._last_state)
                action_np = action_to_numpy(action)
                
                obs_list.append(obs)
                act_list.append(action_np)
                
                obs, reward, terminated, truncated, info = env.step(action)
                done = terminated or truncated
                
    finally:
        print(f"[{opp_name}] Terminée. Fermeture de Unity...")
        try:
            env.game.end_training()
        except:
            pass
        try:
            process.kill()
        except:
            pass
            
    return np.array(obs_list, dtype=np.float32), np.array(act_list, dtype=np.float32)

def main():
    num_games_per_opponent = 50
    # Offset de +100 par rapport à RL training pour éviter les conflits de ports
    start_port = get_port_base() + 100
    
    opponents = [
        "dummy_bot", "random_bot", "random_shooter_bot", 
        "smart_shooter_bot", "kiter_bot", "smart_shield_bot", 
        "smart_dash_bot", "rush_bot", "target_bot"
    ]
    
    args_list = []
    for i, opp in enumerate(opponents):
        args_list.append((opp, start_port + i, num_games_per_opponent))
        
    all_obs = []
    all_acts = []
    
    print(f"Lancement de la collecte en parallèle (9 instances de Unity)...")
    
    # On utilise max_workers=9 puisqu'on a 9 adversaires (parfait pour un CPU 18 coeurs)
    with concurrent.futures.ProcessPoolExecutor(max_workers=9) as executor:
        results = executor.map(collect_for_opponent, args_list)
        
        for obs_array, act_array in results:
            all_obs.append(obs_array)
            all_acts.append(act_array)
            
    # Concaténation des résultats
    final_obs = np.concatenate(all_obs, axis=0)
    final_acts = np.concatenate(all_acts, axis=0)
    
    save_path = os.path.join(os.path.dirname(__file__), "expert_dataset.npz")
    np.savez_compressed(save_path, obs=final_obs, acts=final_acts)
    print(f"\n✅ Dataset sauvegardé dans {save_path}")
    print(f"Total des frames collectées : {len(final_obs)}")

if __name__ == "__main__":
    main()
