# 🤖 Automathon — Documentation Administrateur

> **Version** : 0.3 Alpha · **Moteur** : Unity (Win64 + Linux) · **Interface IA** : Python 3.11+
> **Repo** : https://github.com/antorchn/automathon_2k26

---

## Table des matières

1. [Vue d'ensemble du projet](#1-vue-densemble-du-projet)
2. [Architecture globale](#2-architecture-globale)
3. [Installation & Prérequis](#3-installation--prérequis)
4. [Workflow Cloud → PC (Databricks / Colab)](#4-workflow-cloud--pc-databricks--colab)
5. [Structure du dossier `PythonAI`](#5-structure-du-dossier-pythonai)
6. [La couche Bridge (Communication Unity ↔ Python)](#6-la-couche-bridge-communication-unity--python)
7. [Les Types de données (`bridge/datatypes.py`)](#7-les-types-de-données-bridgedatatypespy)
8. [L'Environnement RL (`core/env/`)](#8-lenvironnement-rl-coreenv)
9. [Les Agents (`agents/`)](#9-les-agents-agents)
10. [Pipeline d'Entraînement (`training/`)](#10-pipeline-dentraînement-training)
11. [Évaluation & Tournoi (`evaluation/`)](#11-évaluation--tournoi-evaluation)
12. [Workflows Administrateur](#12-workflows-administrateur)
13. [Intégration OBS pour le Hackathon](#13-intégration-obs-pour-le-hackathon)
14. [Guide pour les Participants](#14-guide-pour-les-participants)
15. [Référence des Constantes du Jeu](#15-référence-des-constantes-du-jeu)
16. [Dépannage (Troubleshooting)](#16-dépannage-troubleshooting)

---

## 1. Vue d'ensemble du projet

**Automathon** est un jeu de combat de tanks 2D développé sous Unity, conçu spécifiquement comme support de **hackathon d'intelligence artificielle**. Deux tanks s'affrontent dans une arène parsemée d'obstacles. Chaque participant code son propre agent Python qui contrôle un tank en temps réel via une liaison TCP.

### Concept du Hackathon

Les participants reçoivent :
- L'exécutable du jeu (`AutomathonGame`) pour jouer manuellement et tester leurs agents en visuel.
- Le dossier `PythonAI/` contenant le SDK Python, des agents exemples, et les outils d'entraînement.
- Un accès Databricks pour l'entraînement RL cloud (Linux headless, parallèle).

À la fin du hackathon, les agents des participants sont soumis au **tournoi automatisé** via `run_tournament.py`.

### Méchaniques de Jeu

| Mécanique | Description |
|---|---|
| **Machine Gun** | Tir rapide, cooldown court. Projectile rapide (17 000 u/s). |
| **Missile** | Tir unique, plus puissant. Cooldown long. |
| **Shield** | Déploie un bouclier physique devant le tank. Cooldown court. |
| **Dash** | Impulsion de vitesse dans la direction de déplacement. |
| **Arène** | Zone rectangulaire, les tanks sortant des limites sont éliminés (défaite). |
| **Murs** | Obstacles statiques bloquant les projectiles et les déplacements. |

---

## 2. Architecture globale

```
GitHub repo: antorchn/automathon_2k26  (code Python uniquement)
└── PythonAI/
    ├── agents/
    ├── bridge/
    ├── core/
    ├── training/
    ├── evaluation/
    ├── setup.sh        ← Linux / Databricks
    └── setup.ps1       ← Windows

GitHub Releases (binaires, hors repo) :
  automathon-headless-linux.tar.gz  → Databricks / CI
  automathon-game-linux.tar.gz      → PC Linux (headless + jeu graphique)
  automathon-game-windows.zip       → PC Windows (headless + jeu graphique)
```

### Flux de communication

```
Python (Agent IA)  <──── ZeroMQ TCP (localhost) ────>  Unity (Headless)
  Envoie : AIMessage                                    Renvoie : GameState
```

---

## 3. Installation & Prérequis

### Windows (participant)
```powershell
git clone https://github.com/antorchn/automathon_2k26.git
cd automathon
./PythonAI/setup.ps1
```

### Linux (participant ou admin)
```bash
git clone https://github.com/antorchn/automathon_2k26.git
cd automathon
bash PythonAI/setup.sh --full
```

### Databricks (entraînement cloud)
1. UI Databricks → **Repos** → **Add Repo** → URL : `https://github.com/antorchn/automathon_2k26.git`
2. Dans un notebook :
```python
%sh bash /Workspace/Repos/<user>/automathon/PythonAI/setup.sh --headless
```

Les scripts de setup téléchargent les binaires Unity depuis GitHub Releases et installent les dépendances Python.

---

## 4. Workflow Cloud → PC (Databricks / Colab)

### Schéma complet

```
[Databricks]                              [PC Windows ou Linux]
─────────────────────────────────────     ────────────────────────────────────
1. Databricks Repos → clone du repo
2. setup.sh --headless
3. Coder son agent dans agents/
4. python training/collect_demonstrations.py
5. python training/behavioral_cloning.py
6. python training/rl_training.py
   → checkpoints auto dans DBFS
7. python training/export_agent.py
   → mon_agent_TIMESTAMP.zip
   → copié dans DBFS + lien DL
                                      8. Télécharger mon_agent_TIMESTAMP.zip
                                      9. Copier training/rl_model.zip dans
                                         PythonAI/training/rl_model.zip
                                      10. python agents/run_my_agent.py
                                          → neural_expert_bot, port 5555
                                      11. Lancer AutomathonGame(.exe)
                                          → Agent port 5555, JOUER !
```

### Variables d'environnement clés (Databricks)

| Variable | Défaut | Rôle |
|---|---|---|
| `AUTOMATHON_PORT_BASE` | `5600` | Port de base des instances Unity. Changer si collision entre participants. |
| `AUTOMATHON_CHECKPOINT_DIR` | `training/checkpoints/` | Répertoire des checkpoints SB3. Pointer vers `/dbfs/...` sur Databricks. |
| `AUTOMATHON_HEADLESS_PATH` | *(auto-détecté)* | Chemin custom vers le binaire Headless (si DBFS ou chemin non-standard). |

### Exemple de configuration Databricks

```python
import os
# Dans la première cellule de votre notebook
os.environ["AUTOMATHON_PORT_BASE"]      = "5700"  # Votre plage de ports dédiée
os.environ["AUTOMATHON_CHECKPOINT_DIR"] = "/dbfs/FileStore/automathon/mon_equipe"
os.environ["AUTOMATHON_HEADLESS_PATH"]  = "/dbfs/FileStore/automathon/Headless/Headless"
```

### Compatibilité cross-platform des modèles

Les modèles SB3 (`.zip`) sont **100% cross-platform**. Un modèle entraîné sur Linux Databricks se charge directement sur Windows ou Linux sans modification.

---

## 5. Structure du dossier `PythonAI`

```
PythonAI/
├── README.md
├── setup.sh                           ← Setup Linux / Databricks
├── setup.ps1                          ← Setup Windows
├── requirements_participant.txt
├── requirements_admin.txt
│
├── bridge/
│   ├── datatypes.py                   ← Modèles Pydantic (GameState, AIAction…)
│   ├── gym.py                         ← Client ZMQ (mode entraînement)
│   └── play.py                        ← Serveur ZMQ (mode compétition)
│
├── core/env/
│   ├── automathon_env.py              ← Environnement Gymnasium complet
│   └── reward_shaping.py              ← Fonction de récompense
│
├── agents/
│   ├── run_my_agent.py                ← Lanceur interactif (mode Play)
│   ├── dummy_bot/
│   ├── random_bot/
│   ├── …                              ← 8 autres bots heuristiques
│   ├── expert_master_bot/             ← Meilleur bot heuristique (référence)
│   └── neural_expert_bot/
│       ├── agent.py
│       └── feature_extractor.py       ← Extracteur 82 dimensions (partagé)
│
├── training/
│   ├── utils.py                       ← Utilitaires cross-platform (OS, ports…)
│   ├── collect_demonstrations.py      ← Étape 1 : collecte données expertes
│   ├── expert_dataset.npz             ← Dataset BC pré-généré
│   ├── behavioral_cloning.py          ← Étape 2 : pré-entraînement par imitation
│   ├── bc_model.zip                   ← Modèle BC pré-entraîné
│   ├── rl_training.py                 ← Étape 3 : fine-tuning PPO
│   ├── export_agent.py                ← Export modèle (Databricks → PC)
│   ├── IMPORT_INSTRUCTIONS.md         ← Instructions embarquées dans l'export
│   └── tensorboard/                   ← Logs TensorBoard
│
└── evaluation/
    ├── run_matchup.py                 ← Duel entre deux bots
    ├── run_tournament.py              ← Tournoi complet (16 joueurs)
    ├── record_highlights.py           ← Enregistrement OBS
    └── record_tournament.py           ← Enregistrement automatique des finales
```

---

## 6. La couche Bridge (Communication Unity ↔ Python)

### `bridge/gym.py` — Mode Entraînement (Headless)

Socket ZMQ `REQ`. Python initie chaque échange, contrôle les deux tanks.

```python
from bridge.gym import Gym
gym = Gym(tcp_port="5555")
state = gym.reset()
next_state = gym.step(self_action, enemy_action)
gym.end_training()
```

### `bridge/play.py` — Mode Compétition (Jeu graphique)

Socket ZMQ `REP`. Unity initie chaque échange, Python contrôle un seul tank.

```python
from bridge.play import Play
server = Play(my_decision_function, tcp_port="5555")
while True:
    server.respond()
```

---

## 7. Les Types de données (`bridge/datatypes.py`)

### `GameState`

```python
class GameState(BaseModel):
    SelfTank: TankState | None        # Votre tank (None si mort)
    EnemyTank: TankState | None       # Tank adverse
    BulletStates: List[BulletState]
    MissileStates: List[MissileState]
    WallStates: List[WallState]
    ShieldStates: List[ShieldState]
    Done: bool
```

### `TankState`

```python
class TankState(BaseModel):
    Position: Vector2Int              # Position dans l'arène
    Velocity: Vector2Int              # Vélocité en unités/seconde
    Health: int                       # HP (commence à 1000)
    ShieldCooldownFramesLeft: int     # 0 = prêt
    MissileCooldownFramesLeft: int
    MachineGunCooldownFramesLeft: int
    DashCooldownFramesLeft: int
```

### `AIAction`

```python
class AIAction(BaseModel):
    MovingDirection: Vector2Int   # Direction (magnitude ignorée, seul l'angle compte)
    AimingDirection: Vector2Int
    MachineGun: bool
    Missile: bool
    Shield: bool
    Dash: bool
```

> **Convention d'échelle :** `Vector2Int(X=1000, Y=0)` = direction droite, norme 1. Les positions sont typiquement dans `[-12 000, 12 000]` en X, `[-7 000, 5 000]` en Y.

---

## 8. L'Environnement RL (`core/env/`)

### Espaces

| Espace | Dimensions | Plage |
|---|---|---|
| `observation_space` | 82 | `[-1, 1]` |
| `action_space` | 8 | `[-1, 1]` |

### Terminaison d'épisode

| Condition | `terminated` | `truncated` |
|---|---|---|
| `Done == True` (victoire/défaite) | ✅ | ❌ |
| Hors-limites (`\|X\| > 15 000` ou `\|Y\| > 10 000`) | ✅ | ❌ |
| `steps >= max_steps` (défaut 3 600) | ❌ | ✅ |
| Timeout TCP (crash Unity) | ✅ | ❌ |

### Gestion des limites de l'arène

Les limites de l'arène sont gérées **directement par le moteur Unity** (v0.3+). Python ne clampe pas les actions.

### Reward Shaping

```python
reward = -0.1                   # Pénalité de temps (force l'engagement)
reward += damage_dealt * 1.0    # Dégâts infligés
reward -= damage_taken * 0.1    # Dégâts subis (sensibilité réduite à 10%)
# En fin d'épisode :
reward += 1000.0  # Victoire
reward -= 1000.0  # Défaite ou nul (force l'engagement, interdit la fuite)
reward -= 1000.0  # Hors-limites
```

---

## 9. Les Agents (`agents/`)

### Interface obligatoire

```python
from bridge.datatypes import GameState, AIAction

class ParticipantAgent:
    def __init__(self): pass

    def get_action(self, state: GameState) -> AIAction:
        return AIAction(...)
```

### Extracteur de features (82 dimensions)

`agents/neural_expert_bot/feature_extractor.py` — utilisé à la fois par `AutomathonEnv` (entraînement) et `neural_expert_bot/agent.py` (inférence). Ce partage garantit la cohérence.

| Groupe | Features |
|---|---|
| SelfTank | 9 (pos, vel, HP, 4 cooldowns) |
| EnemyTank | 6 (exists, pos rel, vel, HP) |
| 2 Missiles | 10 (exists, pos rel, vel × 2) |
| 5 Balles dangereuses | 25 (exists, pos rel, vel × 5) |
| 2 Boucliers | 12 (exists, pos rel, vel, HP × 2) |
| 4 Murs | 20 (exists, pos rel, taille × 4) |

---

## 10. Pipeline d'Entraînement (`training/`)

### `training/utils.py` — Utilitaires cross-platform

Module partagé entre tous les scripts d'entraînement et d'évaluation :
- `get_unity_headless_path()` — détecte l'OS, chmod automatique sur Linux
- `make_popen_kwargs()` — `CREATE_NO_WINDOW` sur Windows, vide sur Linux
- `get_port_base()` — lit `AUTOMATHON_PORT_BASE` (défaut 5600)
- `get_checkpoint_dir()` — lit `AUTOMATHON_CHECKPOINT_DIR`

### Étapes

**Étape 1 :** `python training/collect_demonstrations.py`
- 9 instances Unity en parallèle, ports `get_port_base() + 100` à `+108`
- Collecte 50 matchs d'`expert_master_bot` contre 9 adversaires
- Sauvegarde : `expert_dataset.npz`

**Étape 2 :** `python training/behavioral_cloning.py`
- Pré-entraîne le réseau PPO par imitation (20 epochs, MSE)
- Sauvegarde : `bc_model.zip`

**Étape 3 :** `python training/rl_training.py`
- 16 instances Unity en parallèle, ports `get_port_base()` à `+15`
- Fine-tune PPO, 2 000 000 steps, curriculum learning
- Checkpoints automatiques (SB3 `CheckpointCallback`) dans `AUTOMATHON_CHECKPOINT_DIR`
- Sauvegarde finale : `rl_model.zip`

**Export :** `python training/export_agent.py [nom_agent]`
- Crée `mon_agent_TIMESTAMP.zip` avec le modèle + code de l'agent
- Détecte automatiquement Databricks ou Colab pour le téléchargement

---

## 11. Évaluation & Tournoi (`evaluation/`)

### Duel simple

```bash
python evaluation/run_matchup.py
```
Éditer `agent1_folder` et `agent2_folder` en bas du fichier.

### Tournoi complet (16 joueurs)

```bash
python evaluation/run_tournament.py
```
Format : 4 poules round-robin + arbre d'élimination (huitièmes → finale). Résultats dans `tournament_results.json`.

---

## 12. Workflows Administrateur

### Workflow : Préparer un tournoi hackathon

1. Collecter les dossiers agents des participants → placer dans `agents/<nom_equipe>/`
2. Vérifier chaque agent : `python -c "import importlib; m = importlib.import_module('agents.<nom>.agent'); m.ParticipantAgent()"`
3. Lancer le tournoi : `python evaluation/run_tournament.py`
4. Enregistrer les finales : `python evaluation/record_tournament.py`

---

## 13. Intégration OBS pour le Hackathon

OBS Studio requis avec obs-websocket activé (port 4455). Dépendance admin : `pip install -r requirements_admin.txt`.

```bash
python evaluation/record_highlights.py   # Enregistre un match en direct
python evaluation/record_tournament.py   # Enregistre les 3 finales automatiquement
```

Le script rejoue automatiquement si le vainqueur en direct ne correspond pas au résultat officiel.

---

## 14. Guide pour les Participants

### Installation (une seule fois)

```bash
# Windows
git clone https://github.com/antorchn/automathon_2k26.git && cd automathon && ./PythonAI/setup.ps1

# Linux
git clone https://github.com/antorchn/automathon_2k26.git && cd automathon && bash PythonAI/setup.sh --full
```

### Créer votre agent

```python
# agents/mon_equipe/agent.py
from bridge.datatypes import GameState, AIAction, Vector2Int

class ParticipantAgent:
    def get_action(self, state: GameState) -> AIAction:
        if state.SelfTank and state.EnemyTank:
            dx = state.EnemyTank.Position.X - state.SelfTank.Position.X
            dy = state.EnemyTank.Position.Y - state.SelfTank.Position.Y
            return AIAction(
                MovingDirection=Vector2Int(X=dx, Y=dy),
                AimingDirection=Vector2Int(X=dx, Y=dy),
                MachineGun=True,
            )
        return AIAction()
```

### Tester en visuel

```bash
cd PythonAI
python agents/run_my_agent.py   # Choisir son agent, port 5555
# Lancer AutomathonGame(.exe) → Agent port 5555 → JOUER
```

---

## 15. Référence des Constantes du Jeu

| Constante | Valeur | Unité |
|---|---|---|
| Vitesse balles (Machine Gun) | 17 000 | unités/s |
| Vitesse max des tanks | ~7 000 | unités/s |
| HP initial | 1 000 | HP |
| Limite arène X | ±15 000 (OOB) | unités |
| Limite arène Y | ±10 000 (OOB) | unités |
| FPS | 60 | frames/s |
| Steps par épisode (défaut) | 3 600 | frames (~60s) |

---

## 16. Dépannage (Troubleshooting)

### `FileNotFoundError: Binaire Unity Headless introuvable`
Lancer `bash PythonAI/setup.sh --headless` (Linux) ou `./PythonAI/setup.ps1` (Windows).
Ou définir `AUTOMATHON_HEADLESS_PATH` pour pointer manuellement vers le binaire.

### `TimeoutError: Make sure the Headless version is running...`
Augmenter `time.sleep(5)` à `time.sleep(10)` dans `make_env()`.

### Conflits de ports sur Databricks
Définir `AUTOMATHON_PORT_BASE` avec une valeur différente par équipe/notebook.

### Checkpoint perdu après crash Databricks
Vérifier `AUTOMATHON_CHECKPOINT_DIR`. Si non défini, les checkpoints sont en local (perdu au redémarrage du cluster). Toujours pointer vers `/dbfs/...`.

### Modèle entraîné sur Linux ne charge pas sur Windows
Impossible en théorie (SB3 est cross-platform). Vérifier que les versions de `stable-baselines3` et `torch` sont identiques des deux côtés.

---

*Documentation générée le 2 septembre 2026 — Automathon v0.3 Alpha*
*Repo : https://github.com/antorchn/automathon_2k26*
