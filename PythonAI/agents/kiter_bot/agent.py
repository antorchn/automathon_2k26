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
    """Maintient une distance cible et tourne autour de l'ennemi."""
    def __init__(self, target_distance: int = 4000):
        super().__init__()
        self.target_distance = target_distance
        self.wander_dir = Vector2Int(X=0, Y=0)
        self.wander_frames = 0
        self.noise_vec = Vector2Int(X=0, Y=0)
        self.noise_frames = 0

    def get_action(self, state: GameState) -> AIAction:
        if not state.SelfTank or not state.EnemyTank:
            return DummyBot().get_action(state)

        dx = state.EnemyTank.Position.X - state.SelfTank.Position.X
        dy = state.EnemyTank.Position.Y - state.SelfTank.Position.Y
        dist = math.sqrt(dx*dx + dy*dy)
        
        # Déplacement aléatoire au début pour diversifier les parties
        if dist > 12000:
            if self.wander_frames <= 0:
                self.wander_dir = Vector2Int(X=random.randint(-1000, 1000), Y=random.randint(-1000, 1000))
                self.wander_frames = random.randint(30, 90)
            self.wander_frames -= 1
            return AIAction(MovingDirection=self.wander_dir, AimingDirection=Vector2Int(X=1000, Y=0))
        
        aimDir = normalize(Vector2Int(X=dx, Y=dy))
        
        # Mouvement: si trop loin -> avance; si trop près -> recule; si bonne distance -> tourne (perpendiculaire)
        if dist > self.target_distance + 500:
            base_x, base_y = aimDir.X, aimDir.Y
        elif dist < self.target_distance - 500:
            base_x, base_y = -aimDir.X, -aimDir.Y
        else:
            # Tourner autour
            perp = normalize(Vector2Int(X=-dy, Y=dx))
            base_x, base_y = perp.X, perp.Y
            
        # Bruit aléatoire fluide
        if self.noise_frames <= 0:
            self.noise_vec = Vector2Int(X=random.randint(-300, 300), Y=random.randint(-300, 300))
            self.noise_frames = random.randint(10, 30)
        self.noise_frames -= 1
        movingDir = normalize(Vector2Int(X=base_x + self.noise_vec.X, Y=base_y + self.noise_vec.Y))

        action = AIAction(MovingDirection=movingDir, AimingDirection=aimDir)
        action.MachineGun = state.SelfTank.MachineGunCooldownFramesLeft == 0
        
        # Utiliser Missile seulement si on vise bien et qu'on est à bonne distance
        if state.SelfTank.MissileCooldownFramesLeft == 0 and dist < 6000:
            action.Missile = True
            
        return action

