import gymnasium as gym
from gymnasium import spaces
import numpy as np

from bridge.gym import Gym
from bridge.datatypes import AIAction, GameState, Vector2Int
from .reward_shaping import calculate_reward

class AutomathonEnv(gym.Env):
    """
    Wrapper Gymnasium complet pour l'entraînement RL sur Automathon.
    """
    
    def __init__(self, tcp_port: str = "5555", max_steps: int = 3600, extractor_fn=None, tcp_timeout: int | None = 500):
        super().__init__()
        self.game = Gym(tcp_port=tcp_port)
        self.tcp_timeout = tcp_timeout
        self.max_steps = max_steps
        self._steps_since_reset = 0
        
        if extractor_fn is None:
            from agents.neural_expert_bot.feature_extractor import extract_features
            self.extractor_fn = extract_features
        else:
            self.extractor_fn = extractor_fn
        
        # Espace d'action continu : 8 valeurs [-1, 1]
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(8,), dtype=np.float32)
        
        # Espace d'observation : 82 features (nouvel extracteur)
        self.observation_space = spaces.Box(low=-1.0, high=1.0, shape=(82,), dtype=np.float32)
        
        # Adversaire par défaut
        import importlib
        try:
            mod = importlib.import_module("agents.rush_bot.agent")
            self.opponent_policy = mod.ParticipantAgent()
        except Exception:
            self.opponent_policy = None
        self._last_state = None
        self.current_step = 0

    def set_opponent(self, opponent_bot):
        """Change dynamiquement l'adversaire (pour le Curriculum Learning / Self Play)."""
        self.opponent_policy = opponent_bot

    def set_opponent_by_name(self, folder_name: str):
        import importlib
        try:
            mod = importlib.import_module(f"agents.{folder_name}.agent")
            self.opponent_policy = mod.ParticipantAgent()
        except Exception as e:
            print(f"Erreur de chargement de l'adversaire {folder_name} : {e}")

    def set_current_step(self, step: int):
        """Permet au callback de synchroniser le step actuel pour le calcul des récompenses dynamiques."""
        self.current_step = step

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        # 1. Reset the underlying environment
        game_state = self.game.reset(tcp_connection_timeout=self.tcp_timeout)
        self._last_state = game_state
        self._steps_since_reset = 0
        
        # 2. Extract features
        obs = self.extractor_fn(game_state)
        
        # 3. Return (obs, info)
        info = {}
        return obs, info

    def step(self, action):
        if isinstance(action, AIAction):
            self_action = action
        else:
            # 1. Convertir l'action numpy en objet AIAction
            self_action = AIAction(
                MovingDirection=Vector2Int(X=int(action[0] * 1000), Y=int(action[1] * 1000)),
                AimingDirection=Vector2Int(X=int(action[2] * 1000), Y=int(action[3] * 1000)),
                MachineGun=bool(action[4] > 0.0),
                Missile=bool(action[5] > 0.0),
                Shield=bool(action[6] > 0.0),
                Dash=bool(action[7] > 0.0),
            )
        
        # Les murs et limites de l'arène sont gérés directement par le moteur Unity.
        # Aucun clamping Python nécessaire.
        # 2. Obtenir l'action de l'adversaire
        # (Note : l'adversaire voit le state tel qu'il est, mais de base les bots heuristiques 
        # supposent qu'ils sont le SelfTank. Il faut intervertir Self et Enemy pour l'adversaire !)
        
        # (Note : l'adversaire voit le state tel qu'il est, mais de base les bots heuristiques 
        # supposent qu'ils sont le SelfTank. Il faut intervertir Self et Enemy pour l'adversaire !)
        
        state_for_enemy = GameState(
            SelfTank=self._last_state.EnemyTank,
            EnemyTank=self._last_state.SelfTank,
            BulletStates=self._last_state.BulletStates,
            MissileStates=self._last_state.MissileStates,
            WallStates=self._last_state.WallStates,
            ShieldStates=self._last_state.ShieldStates,
            Done=self._last_state.Done
        )
        
        enemy_action = self.opponent_policy.get_action(state_for_enemy)
        
        # Les murs et limites de l'arène sont gérés directement par le moteur Unity.
        # Aucun clamping Python nécessaire pour l'adversaire.
        
        # 3. Step in the game
        try:
            next_state = self.game.step(self_action, enemy_action, tcp_connection_timeout=self.tcp_timeout)
        except TimeoutError:
            # En cas de crash ou timeout du jeu, on force un reset à la prochaine étape
            next_state = self._last_state
            next_state.Done = True

        # 4. Extract new observation
        obs = self.extractor_fn(next_state)
        
        # 5. Calculate reward
        reward = calculate_reward(self._last_state, next_state, self_action, self.current_step)
        
        # Check Custom Termination (OOB)
        out_of_bounds = False
        oob_agent1 = False
        oob_agent2 = False
        if next_state.SelfTank:
            pos = next_state.SelfTank.Position
            if abs(pos.X) > 15000 or abs(pos.Y) > 10000:
                out_of_bounds = True
                oob_agent1 = True
        if next_state.EnemyTank:
            pos = next_state.EnemyTank.Position
            if abs(pos.X) > 15000 or abs(pos.Y) > 10000:
                out_of_bounds = True
                oob_agent2 = True
                
        self._last_state = next_state
        
        # 6. Check termination
        terminated = next_state.Done or out_of_bounds
        self._steps_since_reset += 1
        truncated = self._steps_since_reset >= self.max_steps
        info = {
            "oob_agent1": oob_agent1,
            "oob_agent2": oob_agent2,
            "timeout": truncated
        }

        return obs, reward, terminated, truncated, info
