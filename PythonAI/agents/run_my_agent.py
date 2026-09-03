import os
import sys
import importlib

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bridge.play import Play

def get_available_agents():
    agents_dir = os.path.dirname(os.path.abspath(__file__))
    available = []
    
    for item in sorted(os.listdir(agents_dir)):
        item_path = os.path.join(agents_dir, item)
        if os.path.isdir(item_path):
            agent_file = os.path.join(item_path, "agent.py")
            if os.path.exists(agent_file):
                available.append(item)
    return available

def main():
    available_agents = get_available_agents()
    
    print("=== Lanceur d'Agent Automathon ===")
    if not available_agents:
        print("Aucun agent trouvé dans le dossier 'agents/'.")
        return
        
    print("Sélectionnez l'agent à lancer :")
    for i, agent_name in enumerate(available_agents):
        print(f"{i} - {agent_name}")
        
    choice = input(f"Votre choix [0-{len(available_agents)-1}] (Défaut: 0) : ").strip()
    if not choice or not choice.isdigit() or int(choice) >= len(available_agents):
        choice = "0"
        
    selected_agent_folder = available_agents[int(choice)]
    print(f"\nChargement de l'agent : {selected_agent_folder}...")
    
    module_name = f"agents.{selected_agent_folder}.agent"
    module = importlib.import_module(module_name)
    
    if not hasattr(module, "ParticipantAgent"):
        print(f"Erreur : La classe ParticipantAgent est introuvable dans {module_name}.")
        return
        
    agent = module.ParticipantAgent()

    port_input = input("Entrez le port TCP à utiliser (Défaut: 5555) : ").strip()
    port = port_input if port_input else "5555"

    print(f"Démarrage du serveur sur le port {port}. Lancez l'exécutable Unity pour jouer !")
    
    play = Play(agent.get_action, tcp_port=port)
    
    try:
        while True:
            play.respond()
    except KeyboardInterrupt:
        print("\nServeur arrêté par l'utilisateur.")

if __name__ == "__main__":
    main()
