import os
import sys
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from stable_baselines3 import PPO
import gymnasium as gym
from gymnasium import spaces

class MockEnv(gym.Env):
    """Environnement vide juste pour initialiser le modèle SB3 avec les bonnes dimensions."""
    def __init__(self):
        super().__init__()
        self.observation_space = spaces.Box(low=-1.0, high=1.0, shape=(82,), dtype=np.float32)
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(8,), dtype=np.float32)

def main():
    dataset_path = os.path.join(os.path.dirname(__file__), "expert_dataset.npz")
    if not os.path.exists(dataset_path):
        print(f"Erreur : Le fichier {dataset_path} est introuvable. Exécutez collect_demonstrations.py en premier.")
        return

    print("Chargement du dataset...")
    data = np.load(dataset_path)
    obs_data = data['obs']
    act_data = data['acts']
    print(f"Dataset chargé : {obs_data.shape[0]} samples.")

    # Créer le modèle SB3 vierge
    env = MockEnv()
    model = PPO("MlpPolicy", env, verbose=1, learning_rate=1e-3)
    
    # Préparation des données pour PyTorch
    device = model.device
    obs_tensor = torch.tensor(obs_data, dtype=torch.float32).to(device)
    act_tensor = torch.tensor(act_data, dtype=torch.float32).to(device)
    
    dataset = TensorDataset(obs_tensor, act_tensor)
    dataloader = DataLoader(dataset, batch_size=256, shuffle=True)
    
    optimizer = torch.optim.Adam(model.policy.parameters(), lr=1e-3)
    loss_fn = nn.MSELoss()

    epochs = 20
    print("Début de l'entraînement par Behavioral Cloning (Imitation Learning)...")
    for epoch in range(epochs):
        epoch_loss = 0.0
        for batch_obs, batch_act in dataloader:
            optimizer.zero_grad()
            
            # En PPO (Continuous), get_distribution() retourne une distribution de probabilité (Normal).
            # La méthode mode() retourne la moyenne (l'action déterministe).
            dist = model.policy.get_distribution(batch_obs)
            pred_actions = dist.mode()
            
            loss = loss_fn(pred_actions, batch_act)
            loss.backward()
            optimizer.step()
            
            epoch_loss += loss.item()
            
        print(f"Epoch {epoch+1}/{epochs} | Loss (MSE): {epoch_loss / len(dataloader):.4f}")

    # Sauvegarde
    save_path = os.path.join(os.path.dirname(__file__), "bc_model.zip")
    model.save(save_path)
    print(f"\nModèle pré-entraîné sauvegardé sous {save_path}")

if __name__ == "__main__":
    main()
