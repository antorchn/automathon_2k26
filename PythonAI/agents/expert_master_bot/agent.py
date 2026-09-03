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
    """L'Adversaire Heuristique Ultime."""
    def __init__(self):
        super().__init__()
        self.noise_vec = Vector2Int(X=0, Y=0)
        self.noise_frames = 0
        self.smoothed_enemy_vel = [0.0, 0.0]

    def get_action(self, state: GameState) -> AIAction:
        if not state.SelfTank or not state.EnemyTank:
            return DummyBot().get_action(state)

        my_pos = state.SelfTank.Position
        enemy_pos = state.EnemyTank.Position
        enemy_vel = state.EnemyTank.Velocity
        
        dx = enemy_pos.X - my_pos.X
        dy = enemy_pos.Y - my_pos.Y
        dist = math.sqrt(dx*dx + dy*dy)
        
        # Lissage de la vélocité (EMA)
        if self.smoothed_enemy_vel == [0.0, 0.0] and (enemy_vel.X != 0 or enemy_vel.Y != 0):
            self.smoothed_enemy_vel = [float(enemy_vel.X), float(enemy_vel.Y)]
        else:
            self.smoothed_enemy_vel[0] = 0.85 * self.smoothed_enemy_vel[0] + 0.15 * enemy_vel.X
            self.smoothed_enemy_vel[1] = 0.85 * self.smoothed_enemy_vel[1] + 0.15 * enemy_vel.Y

        # --- 1. Tir Prédictif (Lead Targeting) Exact ---
        # Après analyse du code source C# (Bullet.cs et Rigidbody.cs) :
        # - La vitesse de la balle est de 17000 unités/seconde
        # - La vélocité des tanks (EnemyTank.Velocity) est de 7000 unités/seconde
        # - Le jeu tourne à 60 FPS, mais la vélocité renvoyée par le serveur est bien en unités/seconde !
        
        bullet_speed = 17000.0
        time_to_impact_sec = dist / bullet_speed
        
        # Le déplacement réel (en unités) est simplement : vitesse (unités/s) * temps (s)
        displacement_x = self.smoothed_enemy_vel[0] * time_to_impact_sec
        displacement_y = self.smoothed_enemy_vel[1] * time_to_impact_sec
        
        # On n'a plus besoin du clamp brutal, car les mathématiques sont maintenant exactes !
        predicted_target_x = int(enemy_pos.X + displacement_x)
        predicted_target_y = int(enemy_pos.Y + displacement_y)
        
        aimDir = normalize(Vector2Int(
            X=predicted_target_x - my_pos.X,
            Y=predicted_target_y - my_pos.Y
        ))

        # --- 2. Esquive Vectorielle (Vectorial Dodging) ---
        # On calcule une force de répulsion par rapport aux balles/missiles ennemis proches
        dodge_vector = [0.0, 0.0]
        critical_danger = False
        
        threats = state.BulletStates + state.MissileStates
        for threat in threats:
            # Vecteur de la menace vers nous
            tx = my_pos.X - threat.Position.X
            ty = my_pos.Y - threat.Position.Y
            tdist = math.sqrt(tx*tx + ty*ty)
            
            if tdist < 2000 and tdist > 0: # Si la menace est proche
                # Produit scalaire pour savoir si la balle vient vers nous
                dot_product = threat.Velocity.X * tx + threat.Velocity.Y * ty
                if dot_product > 0: # La balle s'approche
                    # Force perpendiculaire pour esquiver
                    perp_x = -threat.Velocity.Y
                    perp_y = threat.Velocity.X
                    
                    # On choisit le côté le plus proche de notre position relative
                    side_dot = tx * perp_x + ty * perp_y
                    if side_dot < 0:
                        perp_x = -perp_x
                        perp_y = -perp_y
                        
                    length_perp = math.sqrt(perp_x*perp_x + perp_y*perp_y)
                    if length_perp > 0:
                        # La répulsion est inversement proportionnelle à la distance
                        weight = 2000.0 / tdist
                        dodge_vector[0] += (perp_x / length_perp) * weight
                        dodge_vector[1] += (perp_y / length_perp) * weight
                        
                        if tdist < 800:
                            critical_danger = True
                            
        # Si l'ennemi est trop proche, on est aussi en danger critique (déclenche le Dash de fuite)
        if dist < 2500:
            critical_danger = True

        # --- 3. Déplacement de Base (Kiting + Esquive) ---
        base_move_x, base_move_y = 0.0, 0.0
        # Distances de kiting ajustées (6000 / 4000) pour ne pas tourner en rond en miroir avec SmartShieldBot
        if dist > 6000:
            base_move_x = enemy_pos.X - my_pos.X
            base_move_y = enemy_pos.Y - my_pos.Y
        elif dist < 4000:
            base_move_x = -(enemy_pos.X - my_pos.X)
            base_move_y = -(enemy_pos.Y - my_pos.Y)
        else:
            base_move_x = -dy
            base_move_y = dx
            
        base_length = math.sqrt(base_move_x**2 + base_move_y**2)
        if base_length > 0:
            base_move_x = (base_move_x / base_length) * 1000
            base_move_y = (base_move_y / base_length) * 1000
            
        # Fusion déplacement + esquive + bruit aléatoire fluide
        if self.noise_frames <= 0:
            self.noise_vec = Vector2Int(X=random.randint(-200, 200), Y=random.randint(-200, 200))
            self.noise_frames = random.randint(10, 30)
        self.noise_frames -= 1
        final_move_x = base_move_x + dodge_vector[0] * 200 + self.noise_vec.X
        final_move_y = base_move_y + dodge_vector[1] * 200 + self.noise_vec.Y
        
        movingDir = normalize(Vector2Int(X=int(final_move_x), Y=int(final_move_y)))

        # --- 4. Actions Binaires (Shield, Dash, Tir) ---
        action = AIAction(MovingDirection=movingDir, AimingDirection=aimDir)
        
        # Vérification des murs proches pour ne pas s'auto-détruire avec un missile
        wall_in_front = False
        for w in state.WallStates:
            wx = w.Position.X - my_pos.X
            wy = w.Position.Y - my_pos.Y
            wdist = math.sqrt(wx*wx + wy*wy)
            if wdist < 1500 and wdist > 0 and wdist < dist:
                # Vérifier si le mur est dans la direction de visée
                dot_aim = (wx * aimDir.X + wy * aimDir.Y) / (wdist * 1000)
                if dot_aim > 0.7: # Environ 45 degrés d'ouverture
                    wall_in_front = True
                    break

        action.MachineGun = (state.SelfTank.MachineGunCooldownFramesLeft == 0) and not wall_in_front
        action.Missile = (state.SelfTank.MissileCooldownFramesLeft == 0) and not wall_in_front
        
        # Shield Réactif
        if critical_danger and state.SelfTank.ShieldCooldownFramesLeft == 0:
            action.Shield = True
            
        # Dash Tactique (fuite d'urgence ou esquive)
        if critical_danger and state.SelfTank.DashCooldownFramesLeft == 0 and not action.Shield:
            action.Dash = True

        return action

