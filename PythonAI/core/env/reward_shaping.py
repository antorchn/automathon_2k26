import math
from bridge.datatypes import GameState, AIAction

def calculate_reward(current_state: GameState, next_state: GameState, action: AIAction = None, current_step: int = 0) -> float:
    """
    Calcule la récompense (Reward Shaping) entre deux étapes.
    """
    reward = -0.1 # Pénalité de temps par défaut (-0.1 par frame)

    if current_state.SelfTank and next_state.SelfTank and current_state.EnemyTank and next_state.EnemyTank:
        # Dégâts infligés à l'ennemi (positif)
        damage_dealt = current_state.EnemyTank.Health - next_state.EnemyTank.Health
        if damage_dealt > 0:
            reward += damage_dealt * 1.0
            
        # Multiplicateur de douleur abaissé à 0.1
        # Objectif : Désensibiliser l'agent à sa propre santé pour le forcer à privilégier l'attaque.
        # S'il a trop peur de prendre des dégâts, il fuira le combat.
        pain_factor = 0.1

        # Dégâts subis (négatif) - Sensibilité régulée par le pain_factor
        damage_taken = current_state.SelfTank.Health - next_state.SelfTank.Health
        if damage_taken > 0:
            reward -= damage_taken * 1.0 * pain_factor
            
        # (La récompense de visée a été supprimée. L'agent sait déjà viser grâce au Behavioral Cloning)

    # Victoire / Défaite absolue
    if next_state.Done:
        if not next_state.SelfTank or next_state.SelfTank.Health <= 0:
            reward -= 1000.0
        elif not next_state.EnemyTank or next_state.EnemyTank.Health <= 0:
            reward += 1000.0
        else:
            reward -= 1000.0 # PUNITION DU MATCH NUL (Timeout) : Forcer l'engagement !
            
    # Vérification Hors-Limite (Sortie de carte)
    if next_state.SelfTank:
        pos = next_state.SelfTank.Position
        if abs(pos.X) > 15000 or abs(pos.Y) > 10000:
            reward -= 1000.0 # Pénalité de mort immédiate par fuite
            


    return float(reward)
