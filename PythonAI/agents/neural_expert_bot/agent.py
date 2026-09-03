import os
import sys
import numpy as np

# Ajouter le dossier parent au path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from bridge.datatypes import GameState, AIAction, Vector2Int
from .feature_extractor import extract_features

class ParticipantAgent:
    """
    Exemple d'Agent IA Neural Network entraîné avec StableBaselines3 (PPO).
    """
    def __init__(self):
        try:
            from stable_baselines3 import PPO
        except ImportError:
            print("Veuillez installer stable-baselines3 et torch pour utiliser cet agent.")
            sys.exit(1)
            
        model_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "training",
            "rl_model.zip"
        )
        
        # En fallback (si le modèle RL n'a pas encore été généré), on cherche le modèle BC
        if not os.path.exists(model_path):
            fallback_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "training", "bc_model.zip")
            if os.path.exists(fallback_path):
                model_path = fallback_path
            else:
                print(f"Erreur: Aucun modèle trouvé dans {model_path} ou {fallback_path}.")
                print("Veuillez lancer l'entraînement (training/rl_training.py) au préalable.")
                sys.exit(1)
                
        # On charge le modèle sans l'environnement
        self.model = PPO.load(model_path)
        
    def get_action(self, state: GameState) -> AIAction:
        # 1. Extraction des features
        obs = extract_features(state)
        
        # 2. Inférence (prediction déterministe)
        action_np, _states = self.model.predict(obs, deterministic=True)
        
        # 3. Conversion du vecteur numpy (8 dimensions) vers AIAction
        action = AIAction(
            MovingDirection=Vector2Int(X=int(action_np[0] * 1000), Y=int(action_np[1] * 1000)),
            AimingDirection=Vector2Int(X=int(action_np[2] * 1000), Y=int(action_np[3] * 1000)),
            MachineGun=bool(action_np[4] > 0.0),
            Missile=bool(action_np[5] > 0.0),
            Shield=bool(action_np[6] > 0.0),
            Dash=bool(action_np[7] > 0.0),
        )
        
        return action
