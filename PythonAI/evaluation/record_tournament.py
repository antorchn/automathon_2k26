import os
import sys
import json
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.record_highlights import record_match
import importlib

def load_agent_class(folder_name):
    module = importlib.import_module(f"agents.{folder_name}.agent")
    return module.ParticipantAgent

def record_tournament_finals():
    results_path = os.path.join(os.path.dirname(__file__), "tournament_results.json")
    
    if not os.path.exists(results_path):
        print(f"Erreur : Le fichier {results_path} n'existe pas. Veuillez d'abord exécuter run_tournament.py.")
        return
        
    with open(results_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    print("="*50)
    print(" ENREGISTREMENT AUTOMATIQUE DES FINALES DU TOURNOI ")
    print("="*50)
    
    # Extraire les 3 matchs (les deux demi-finales et la finale)
    demis = data["bracket"]["demis"]
    finale = data["bracket"]["finale"]
    
    matches_to_record = [
        ("Demi-Finale 1", demis[0]),
        ("Demi-Finale 2", demis[1]),
        ("Grande Finale", finale[0])
    ]
    
    for match_title, match_data in matches_to_record:
        print(f"\n" + "*"*40)
        print(f"Lancement de : {match_title}")
        p1_info = data['participants'][match_data['p1']]
        p2_info = data['participants'][match_data['p2']]
        
        p1_name = p1_info['name'] if isinstance(p1_info, dict) else p1_info
        p2_name = p2_info['name'] if isinstance(p2_info, dict) else p2_info
        
        print(f"Affiche : {p1_name} VS {p2_name}")
        print("*"*40 + "\n")
        
        target_winner_pid = match_data['winner']
        target_winner_idx = 1 if match_data['p1'] == target_winner_pid else 2
        
        while True:
            if isinstance(p1_info, dict) and isinstance(p2_info, dict):
                agent1 = load_agent_class(p1_info['folder'])()
                agent2 = load_agent_class(p2_info['folder'])()
            else:
                print("Erreur : Le format du JSON est obsolète (il manque les dossiers). Veuillez relancer run_tournament.py.")
                return
            
            # Enregistrement avec la logique de record_highlights
            video_path, live_winner_idx = record_match(agent1, agent2)
            
            if live_winner_idx == target_winner_idx:
                print(f"\n✅ Succès ! Le gagnant de la vidéo (J{live_winner_idx}) correspond au vainqueur du tournoi ({target_winner_pid}).")
                break
            else:
                print(f"\n❌ Incohérence ! Vainqueur attendu = J{target_winner_idx} ({target_winner_pid}), Vainqueur vidéo = J{live_winner_idx}.")
                print("Suppression de la vidéo et relance du même match...")
                if video_path and os.path.exists(video_path):
                    try:
                        os.remove(video_path)
                    except Exception as e:
                        print(f"Impossible de supprimer la vidéo : {e}")
                
                print("Attente de 5 secondes avant de relancer...")
                time.sleep(5)
                
        print(f"\n{match_title} terminée.")
        print("Attente de 5 secondes avant le match suivant (libération des ports)...")
        time.sleep(5)
        
    print("\n" + "="*50)
    print(" TOUS LES ENREGISTREMENTS SONT TERMINÉS ! ")
    print("="*50)

if __name__ == "__main__":
    record_tournament_finals()
