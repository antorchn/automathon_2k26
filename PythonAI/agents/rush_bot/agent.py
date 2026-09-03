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


class DummyBot:
    """Bot inactif mais qui tire tout droit."""
    def get_action(self, state: GameState) -> AIAction:
        return AIAction(
            MovingDirection=Vector2Int(X=0, Y=0),
            AimingDirection=Vector2Int(X=1000, Y=0),
            MachineGun=True,
            Missile=False,
            Shield=False,
            Dash=False
        )

class ParticipantAgent:
    """Fonce sur l'ennemi agressivement (similaire à example_ai.py)."""
    def get_action(self, state: GameState) -> AIAction:
        if not state.SelfTank or not state.EnemyTank:
            return DummyBot().get_action(state)

        aimDir = Vector2Int(
            X=state.EnemyTank.Position.X - state.SelfTank.Position.X,
            Y=state.EnemyTank.Position.Y - state.SelfTank.Position.Y
        )
        forward = length_squared(aimDir) > 2000 * 2000
        aimDir_norm = normalize(aimDir)
        
        movingDir = aimDir_norm if forward else Vector2Int(X=-aimDir_norm.X, Y=-aimDir_norm.Y)
        
        action = AIAction(MovingDirection=movingDir, AimingDirection=aimDir_norm)
        action.MachineGun = state.SelfTank.MachineGunCooldownFramesLeft == 0
        action.Missile = state.SelfTank.MissileCooldownFramesLeft == 0
        action.Shield = state.SelfTank.ShieldCooldownFramesLeft == 0
        action.Dash = state.SelfTank.DashCooldownFramesLeft == 0
        
        return action

