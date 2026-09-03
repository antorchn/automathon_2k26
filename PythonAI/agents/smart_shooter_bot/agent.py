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
    """Phase 3 : Se déplace intelligemment et tire (basé sur RushBot bridé)."""
    def __init__(self):
        super().__init__()
        self.wander_dir = Vector2Int(X=0, Y=0)
        self.wander_frames = 0
        self.noise_vec = Vector2Int(X=0, Y=0)
        self.noise_frames = 0

    def get_action(self, state: GameState) -> AIAction:
        if not state.SelfTank or not state.EnemyTank:
            return DummyBot().get_action(state)

        my_pos = state.SelfTank.Position
        enemy_pos = state.EnemyTank.Position
        
        dx = enemy_pos.X - my_pos.X
        dy = enemy_pos.Y - my_pos.Y
        dist = math.sqrt(dx*dx + dy*dy)
        
        # Déplacement aléatoire au début pour diversifier les parties
        if dist > 12000:
            if self.wander_frames <= 0:
                self.wander_dir = Vector2Int(X=random.randint(-1000, 1000), Y=random.randint(-1000, 1000))
                self.wander_frames = random.randint(30, 90)
            self.wander_frames -= 1
            return AIAction(MovingDirection=self.wander_dir, AimingDirection=Vector2Int(X=1000, Y=0))
        
        aimDir = normalize(Vector2Int(X=dx, Y=dy))
        
        # Bruit aléatoire fluide pour la génération de données
        if self.noise_frames <= 0:
            self.noise_vec = Vector2Int(X=random.randint(-300, 300), Y=random.randint(-300, 300))
            self.noise_frames = random.randint(10, 30)
        self.noise_frames -= 1
        
        movingDir = normalize(Vector2Int(X=aimDir.X + self.noise_vec.X, Y=aimDir.Y + self.noise_vec.Y))
        
        action = AIAction(MovingDirection=movingDir, AimingDirection=aimDir)
        action.MachineGun = state.SelfTank.MachineGunCooldownFramesLeft == 0
        return action

