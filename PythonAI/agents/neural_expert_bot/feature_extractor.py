import numpy as np
from bridge.datatypes import GameState, TankState, Vector2Int

def get_cooldown_norm(cooldown: int, max_frames: int = 60) -> float:
    return min(float(cooldown) / max_frames, 1.0)

def dot_product(v1: Vector2Int, v2: Vector2Int) -> float:
    return v1.X * v2.X + v1.Y * v2.Y

def extract_features(state: GameState) -> np.ndarray:
    """
    Extrait un vecteur d'état NumPy de 82 dimensions, normalisé dans [-1, 1].
    Gère les entités manquantes proprement avec un flag 'Exists'.
    Filtre les balles qui s'éloignent.
    """
    NORM_DIST_X = 15000.0
    NORM_DIST_Y = 15000.0
    NORM_VEL = 2000.0 
    
    features = []
    
    # --- 1. SelfTank (9 features) ---
    if state.SelfTank:
        self_tank = state.SelfTank
        features.append(np.clip(self_tank.Position.X / NORM_DIST_X, -1.0, 1.0)) # 1. Pos X
        features.append(np.clip(self_tank.Position.Y / NORM_DIST_Y, -1.0, 1.0)) # 2. Pos Y
        features.append(np.clip(self_tank.Velocity.X / NORM_VEL, -1.0, 1.0)) # 3. Vel X
        features.append(np.clip(self_tank.Velocity.Y / NORM_VEL, -1.0, 1.0)) # 4. Vel Y
        features.append(self_tank.Health / 1000.0) # 5. HP
        features.append(get_cooldown_norm(self_tank.MachineGunCooldownFramesLeft)) # 6. CD MG
        features.append(get_cooldown_norm(self_tank.MissileCooldownFramesLeft)) # 7. CD Missile
        features.append(get_cooldown_norm(self_tank.ShieldCooldownFramesLeft)) # 8. CD Shield
        features.append(get_cooldown_norm(self_tank.DashCooldownFramesLeft)) # 9. CD Dash
        
        self_pos = self_tank.Position
    else:
        features.extend([0.0] * 9)
        self_pos = Vector2Int(X=0, Y=0)

    def dist_sq(pos1: Vector2Int, pos2: Vector2Int):
        return (pos1.X - pos2.X)**2 + (pos1.Y - pos2.Y)**2

    # --- 2. EnemyTank (6 features) ---
    if state.EnemyTank:
        enemy_tank = state.EnemyTank
        features.append(1.0) # 1. Exists
        features.append(np.clip((enemy_tank.Position.X - self_pos.X) / NORM_DIST_X, -1.0, 1.0)) # 2. Rel Pos X
        features.append(np.clip((enemy_tank.Position.Y - self_pos.Y) / NORM_DIST_Y, -1.0, 1.0)) # 3. Rel Pos Y
        features.append(np.clip(enemy_tank.Velocity.X / NORM_VEL, -1.0, 1.0)) # 4. Vel X
        features.append(np.clip(enemy_tank.Velocity.Y / NORM_VEL, -1.0, 1.0)) # 5. Vel Y
        features.append(enemy_tank.Health / 1000.0) # 6. HP
    else:
        features.extend([0.0] * 6)

    # --- 3. Missiles : 2 plus proches (10 features) ---
    # Pour les missiles, on ne filtre pas car ils sont guidés et peuvent faire demi-tour.
    sorted_missiles = sorted(state.MissileStates, key=lambda m: dist_sq(m.Position, self_pos))
    for i in range(2):
        if i < len(sorted_missiles):
            m = sorted_missiles[i]
            features.append(1.0) # Exists
            features.append(np.clip((m.Position.X - self_pos.X) / NORM_DIST_X, -1.0, 1.0))
            features.append(np.clip((m.Position.Y - self_pos.Y) / NORM_DIST_Y, -1.0, 1.0))
            features.append(np.clip(m.Velocity.X / NORM_VEL, -1.0, 1.0))
            features.append(np.clip(m.Velocity.Y / NORM_VEL, -1.0, 1.0))
        else:
            features.extend([0.0] * 5)

    # --- 4. Balles : 5 plus proches, FILTRÉES (25 features) ---
    # On filtre les balles qui s'éloignent de nous.
    # Vecteur Tank -> Balle
    dangerous_bullets = []
    for b in state.BulletStates:
        vec_to_bullet = Vector2Int(X=b.Position.X - self_pos.X, Y=b.Position.Y - self_pos.Y)
        # Si le produit scalaire entre (Balle -> Tank) et Vitesse de la Balle est positif, 
        # la balle se rapproche de nous.
        # Donc produit scalaire entre (Tank -> Balle) et Vitesse doit être NÉGATIF pour se rapprocher.
        dp = dot_product(vec_to_bullet, b.Velocity)
        if dp <= 0: # La balle se rapproche (ou est à l'arrêt)
            dangerous_bullets.append(b)
            
    sorted_bullets = sorted(dangerous_bullets, key=lambda b: dist_sq(b.Position, self_pos))
    for i in range(5):
        if i < len(sorted_bullets):
            b = sorted_bullets[i]
            features.append(1.0) # Exists
            features.append(np.clip((b.Position.X - self_pos.X) / NORM_DIST_X, -1.0, 1.0))
            features.append(np.clip((b.Position.Y - self_pos.Y) / NORM_DIST_Y, -1.0, 1.0))
            features.append(np.clip(b.Velocity.X / NORM_VEL, -1.0, 1.0))
            features.append(np.clip(b.Velocity.Y / NORM_VEL, -1.0, 1.0))
        else:
            features.extend([0.0] * 5)

    # --- 5. Boucliers : 2 plus proches (12 features) ---
    sorted_shields = sorted(state.ShieldStates, key=lambda s: dist_sq(s.Position, self_pos))
    for i in range(2):
        if i < len(sorted_shields):
            s = sorted_shields[i]
            features.append(1.0) # Exists
            features.append(np.clip((s.Position.X - self_pos.X) / NORM_DIST_X, -1.0, 1.0))
            features.append(np.clip((s.Position.Y - self_pos.Y) / NORM_DIST_Y, -1.0, 1.0))
            features.append(np.clip(s.Velocity.X / NORM_VEL, -1.0, 1.0))
            features.append(np.clip(s.Velocity.Y / NORM_VEL, -1.0, 1.0))
            features.append(s.Health / 1500.0) # Health
        else:
            features.extend([0.0] * 6)

    # --- 6. Murs : 4 plus proches (20 features) ---
    sorted_walls = sorted(state.WallStates, key=lambda w: dist_sq(w.Position, self_pos))
    for i in range(4):
        if i < len(sorted_walls):
            w = sorted_walls[i]
            features.append(1.0) # Exists
            features.append(np.clip((w.Position.X - self_pos.X) / NORM_DIST_X, -1.0, 1.0))
            features.append(np.clip((w.Position.Y - self_pos.Y) / NORM_DIST_Y, -1.0, 1.0))
            features.append(np.clip(w.Size.X / NORM_DIST_X, -1.0, 1.0)) # Size X
            features.append(np.clip(w.Size.Y / NORM_DIST_Y, -1.0, 1.0)) # Size Y
        else:
            features.extend([0.0] * 5)

    # Convertir en tableau Numpy float32
    return np.array(features, dtype=np.float32)
