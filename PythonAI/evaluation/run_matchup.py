import os
import sys
import subprocess
import time

# Ajouter le dossier parent au sys.path pour pouvoir importer `core` et `my_agent`
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.env.automathon_env import AutomathonEnv
from training.utils import get_unity_headless_path, make_popen_kwargs
import importlib

def load_agent_class(folder_name):
    module = importlib.import_module(f"agents.{folder_name}.agent")
    return module.ParticipantAgent

def play_matchup(env: AutomathonEnv, agent1, agent2, num_games: int = 301, verbose: bool = True, name1: str = None, name2: str = None):
    env.set_opponent(agent2)
    wins_agent1 = 0
    wins_agent2 = 0
    draws = 0
    
    name1 = name1 or agent1.__class__.__name__
    name2 = name2 or agent2.__class__.__name__
    
    if verbose:
        print(f"\n--- Matchup: {name1} vs {name2} ({num_games} matchs) ---")
    
    for match_idx in range(1, num_games + 1):
        obs, _ = env.reset()
        done = False
        
        while not done:
            action = agent1.get_action(env._last_state)
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            
        # Vérifier le gagnant
        if info.get("oob_agent1") and info.get("oob_agent2"):
            draws += 1
            winner = "Égalité"
        elif info.get("oob_agent1"):
            wins_agent2 += 1
            winner = name2
        elif info.get("oob_agent2"):
            wins_agent1 += 1
            winner = name1
        else:
            last_state = env._last_state
            if last_state:
                hp1 = last_state.SelfTank.Health if last_state.SelfTank else 0
                hp2 = last_state.EnemyTank.Health if last_state.EnemyTank else 0
                
                if hp1 <= 0 and hp2 > 0:
                    wins_agent2 += 1
                    winner = name2
                elif hp2 <= 0 and hp1 > 0:
                    wins_agent1 += 1
                    winner = name1
                else:
                    draws += 1
                    winner = "Égalité"
                    
        if verbose:
            print(f"Match {match_idx}/{num_games} terminé. Vainqueur : {winner}")
            
    if wins_agent1 > wins_agent2:
        overall_winner = agent1
    elif wins_agent2 > wins_agent1:
        overall_winner = agent2
    else:
        overall_winner = agent1 # Avantage arbitraire au joueur 1
        
    if verbose:
        print(f"\nRÉSULTAT {name1} vs {name2} :")
        print(f"{name1} : {wins_agent1} victoires")
        print(f"{name2} : {wins_agent2} victoires")
        print(f"Égalités : {draws}")
        print(f"VAINQUEUR DU MATCHUP : {name1 if wins_agent1 >= wins_agent2 else name2}")
        
    return overall_winner, wins_agent1, wins_agent2, draws


def run_matchup(num_games: int = 301):
    port = "5555"
    unity_exe_path = get_unity_headless_path()

    print(f"Lancement de Unity en Headless Mode : {unity_exe_path} sur le port {port}")
    process = subprocess.Popen([unity_exe_path, f"tcp://127.0.0.1:{port}"], **make_popen_kwargs())
    
    time.sleep(5)
    env = AutomathonEnv(tcp_port="5555")
    
    # Choisir deux bots à affronter (exemples)
    # Assurez-vous que ces dossiers existent bien dans agents/
    agent1_folder = "expert_master_bot"
    agent2_folder = "smart_dash_bot"
    
    agent1 = load_agent_class(agent1_folder)()
    agent2 = load_agent_class(agent2_folder)()
    
    try:
        play_matchup(env, agent1, agent2, num_games, verbose=True, name1=agent1_folder, name2=agent2_folder)
    finally:
        print("Fermeture de l'environnement Unity...")
        env.game.end_training()
        process.kill()

if __name__ == "__main__":
    run_matchup(21)
