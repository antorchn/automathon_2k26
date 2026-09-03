# Importer votre agent sur votre PC

## Prerequis : installer le SDK (une seule fois)

### Windows
```powershell
git clone https://github.com/antorchn/automathon_2k26.git
cd automathon
./PythonAI/setup.ps1
```

### Linux
```bash
git clone https://github.com/antorchn/automathon_2k26.git
cd automathon
bash PythonAI/setup.sh --full
```

## Importer le modele entraine

Copier `training/rl_model.zip` (contenu de cet export) vers :
```
automathon/PythonAI/training/rl_model.zip
```

## Lancer votre agent

```bash
cd automathon/PythonAI
python agents/run_my_agent.py
# Selectionner : neural_expert_bot
# Port         : 5555 (defaut)
```

## Lancer le jeu

- **Windows** : double-cliquer sur `AutomathonGame.exe`
- **Linux**   : `./AutomathonGame`

Dans le jeu → Selectionner **Agent (Port 5555)** pour Joueur 1 → **JOUER !**

## Questions frequentes

**Mon modele entraine sur Linux fonctionne-t-il sur Windows ?**
Oui. Les modeles SB3 (.zip) sont 100% cross-platform.

**Quel extracteur de features est utilise ?**
`agents/neural_expert_bot/feature_extractor.py` (82 dimensions).
Il est identique a l entrainement et a l inference.
Si vous avez personnalise votre extracteur, copiez-le dans votre dossier agent.
