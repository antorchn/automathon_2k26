import math
import random
from bridge.datatypes import GameState, AIAction, Vector2Int

def length_squared(v: Vector2Int) -> int:
    return v.X * v.X + v.Y * v.Y

def length_float(v: Vector2Int) -> float:
    return math.sqrt(v.X * v.X + v.Y * v.Y)

def normalize(v: Vector2Int, magnitude: int = 1000) -> Vector2Int:
    length = math.sqrt(v.X * v.X + v.Y * v.Y)
    if length == 0:
        return Vector2Int(X=magnitude, Y=0)
    return Vector2Int(X=int(v.X * magnitude / length), Y=int(v.Y * magnitude / length))


class RandomBot:
    """Phase 1 : Se déplace aléatoirement pour forcer l'agent à viser une cible mouvante (pas de tir)."""
    def __init__(self):
        super().__init__()
        self.target_dir = Vector2Int(X=0, Y=0)
        self.frames_in_dir = 0
        
    def get_action(self, state: GameState) -> AIAction:
        import random
        if self.frames_in_dir <= 0:
            self.target_dir = Vector2Int(X=random.randint(-1000, 1000), Y=random.randint(-1000, 1000))
            self.frames_in_dir = random.randint(30, 90)
        self.frames_in_dir -= 1
        return AIAction(
            MovingDirection=self.target_dir, AimingDirection=Vector2Int(X=1000, Y=0),
            MachineGun=False, Missile=False, Shield=False, Dash=False
        )

class ParticipantAgent(RandomBot):
    """Phase 2 : Se déplace aléatoirement ET tire."""
    def get_action(self, state: GameState) -> AIAction:
        action = super().get_action(state)
        
        # Vise grossièrement l'ennemi
        if state.SelfTank and state.EnemyTank:
            dx = state.EnemyTank.Position.X - state.SelfTank.Position.X
            dy = state.EnemyTank.Position.Y - state.SelfTank.Position.Y
            action.AimingDirection = normalize(Vector2Int(X=dx, Y=dy))
        
        action.MachineGun = state.SelfTank and state.SelfTank.MachineGunCooldownFramesLeft == 0
        return action

