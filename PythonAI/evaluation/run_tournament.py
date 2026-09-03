import os
import sys
import subprocess
import time
import json
import itertools

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.env.automathon_env import AutomathonEnv
from training.utils import get_unity_headless_path, make_popen_kwargs
import importlib

def get_available_agents():
    agents_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agents")
    available = []
    for item in sorted(os.listdir(agents_dir)):
        item_path = os.path.join(agents_dir, item)
        if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, "agent.py")):
            available.append(item)
    return available

def load_agent_class(folder_name):
    module = importlib.import_module(f"agents.{folder_name}.agent")
    return module.ParticipantAgent
from evaluation.run_matchup import play_matchup

class Participant:
    def __init__(self, pid: str, name: str, folder_name: str, bot):
        self.id = pid
        self.name = name
        self.folder_name = folder_name
        self.bot = bot
        
        # Statistiques de poule
        self.points = 0
        self.wins = 0
        self.losses = 0
        self.draws = 0
        self.games_won = 0
        self.games_lost = 0
        
    @property
    def diff(self):
        return self.games_won - self.games_lost

def play_bracket_round(env, matchups, round_name, tournament_data_ref, num_games):
    print(f"\n=========================================")
    print(f"        {round_name.upper()}        ")
    print(f"=========================================")
    
    round_results = []
    winners = []
    
    for i, (p1, p2) in enumerate(matchups):
        print(f"\n--- {round_name} {i+1} : {p1.name} VS {p2.name} ---")
        winner_bot, s1, s2, draws = play_matchup(env, p1.bot, p2.bot, num_games, verbose=False)
        
        # On détermine qui a gagné le BO
        if s1 > s2:
            winner = p1
        elif s2 > s1:
            winner = p2
        else:
            # En cas d'égalité stricte en BO, avantage p1 arbitraire (très rare sur des nombres impairs comme 51)
            winner = p1
            
        print(f"Gagnant: {winner.name} ({s1} à {s2}, {draws} égalités)")
        
        round_results.append({
            "match_id": f"{round_name}_{i+1}",
            "p1": p1.id,
            "p2": p2.id,
            "s1": s1,
            "s2": s2,
            "draws": draws,
            "winner": winner.id
        })
        winners.append(winner)
        
    tournament_data_ref[round_name] = round_results
    return winners


def run_tournament(num_games_per_matchup: int = 51):
    port = "5555"
    unity_exe_path = get_unity_headless_path()

    print(f"Lancement de Unity en Headless Mode : {unity_exe_path} sur le port {port}")
    process = subprocess.Popen([unity_exe_path, f"tcp://127.0.0.1:{port}"], **make_popen_kwargs())
    
    time.sleep(5) # Laisser le temps à Unity de démarrer
    env = AutomathonEnv(tcp_port="5555")
    
    # 1. Sélectionner les 16 participants depuis les dossiers
    bots_pool_folders = get_available_agents()
    if not bots_pool_folders:
        print("Erreur: Aucun agent trouvé dans le dossier 'agents'.")
        return
        
    participants = []
    for i in range(16):
        folder_name = bots_pool_folders[i % len(bots_pool_folders)]
        bot_class = load_agent_class(folder_name)
        p = Participant(f"P{i+1}", f"{folder_name} {i//len(bots_pool_folders) + 1}", folder_name, bot_class())
        participants.append(p)
        
    print("\nDEBUT DU GRAND TOURNOI AUTOMATHON")
    print(f"Format : 16 Joueurs, Phases de Poules puis Arbre d'élimination.")
    print(f"Matchs : Meilleur de {num_games_per_matchup} parties.")
    
    # Initialisation des données JSON
    tournament_data = {
        "participants": {p.id: {"name": p.name, "folder": p.folder_name} for p in participants},
        "group_stage": {},
        "bracket": {}
    }
    
    try:
        # --- PHASE 1 : POULES (GROUP STAGE) ---
        groups = {
            "A": participants[0:4],
            "B": participants[4:8],
            "C": participants[8:12],
            "D": participants[12:16]
        }
        
        print("\n" + "="*50)
        print("                PHASE DE POULES")
        print("="*50)
        
        for group_name, group_participants in groups.items():
            print(f"\n--- POULE {group_name} ---")
            group_matches = []
            
            # Round Robin : toutes les combinaisons possibles (6 matchs par poule)
            for p1, p2 in itertools.combinations(group_participants, 2):
                print(f"Match Poule {group_name}: {p1.name} vs {p2.name}")
                _, s1, s2, draws = play_matchup(env, p1.bot, p2.bot, num_games_per_matchup, verbose=False)
                
                # Mise à jour des statistiques de poule
                p1.games_won += s1
                p1.games_lost += s2
                p2.games_won += s2
                p2.games_lost += s1
                p1.draws += draws
                p2.draws += draws
                
                if s1 > s2:
                    p1.points += 3
                    p1.wins += 1
                    p2.losses += 1
                    match_winner = p1.id
                elif s2 > s1:
                    p2.points += 3
                    p2.wins += 1
                    p1.losses += 1
                    match_winner = p2.id
                else:
                    p1.points += 1
                    p2.points += 1
                    match_winner = "DRAW"
                    
                group_matches.append({
                    "p1": p1.id,
                    "p2": p2.id,
                    "s1": s1,
                    "s2": s2,
                    "draws": draws,
                    "winner": match_winner
                })
                
            # Classer la poule : points, puis différence de manches
            group_participants.sort(key=lambda p: (p.points, p.diff), reverse=True)
            print(f"Classement Poule {group_name}:")
            for rank, p in enumerate(group_participants):
                print(f"  {rank+1}. {p.name} ({p.points} pts, Diff: {p.diff})")
            
            tournament_data["group_stage"][group_name] = {
                "matches": group_matches,
                "standings": [p.id for p in group_participants]
            }
            
        # --- PHASE 2 : ARBRE D'ÉLIMINATION (BRACKET) ---
        print("\n" + "="*50)
        print("             ARBRE D'ÉLIMINATION")
        print("="*50)
        
        # Huitièmes (Seeding croisé)
        r16_matchups = [
            (groups["A"][0], groups["D"][3]), # M1
            (groups["B"][1], groups["C"][2]), # M2
            (groups["C"][0], groups["B"][3]), # M3
            (groups["D"][1], groups["A"][2]), # M4
            (groups["B"][0], groups["C"][3]), # M5
            (groups["A"][1], groups["D"][2]), # M6
            (groups["D"][0], groups["A"][3]), # M7
            (groups["C"][1], groups["B"][2]), # M8
        ]
        
        r16_winners = play_bracket_round(env, r16_matchups, "huitiemes", tournament_data["bracket"], num_games_per_matchup)
        
        # Quarts de Finale
        qf_matchups = [
            (r16_winners[0], r16_winners[1]),
            (r16_winners[2], r16_winners[3]),
            (r16_winners[4], r16_winners[5]),
            (r16_winners[6], r16_winners[7])
        ]
        qf_winners = play_bracket_round(env, qf_matchups, "quarts", tournament_data["bracket"], num_games_per_matchup)
        
        # Demi-Finales
        sf_matchups = [
            (qf_winners[0], qf_winners[1]),
            (qf_winners[2], qf_winners[3])
        ]
        sf_winners = play_bracket_round(env, sf_matchups, "demis", tournament_data["bracket"], num_games_per_matchup)
        
        # Finale
        f_matchups = [
            (sf_winners[0], sf_winners[1])
        ]
        f_winner = play_bracket_round(env, f_matchups, "finale", tournament_data["bracket"], num_games_per_matchup)
        
        print("\n" + "="*50)
        print(f"LE GRAND CHAMPION EST : {f_winner[0].name} !")
        print("="*50 + "\n")
        
        # Sauvegarde JSON dans 'evaluation'
        output_path = os.path.join(os.path.dirname(__file__), "tournament_results.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(tournament_data, f, indent=4, ensure_ascii=False)
        print(f"Résultats du tournoi sauvegardés dans : {output_path}")
        
    finally:
        print("Fermeture de l'environnement Unity...")
        env.game.end_training()
        process.kill()

if __name__ == "__main__":
    run_tournament(51)
