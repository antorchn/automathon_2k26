import os
import sys
import subprocess
import time
import threading

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bridge.play import Play
from bridge.datatypes import GameState, AIAction
import importlib

try:
    import obswebsocket
    from obswebsocket import requests as obsrequests
except ImportError:
    obswebsocket = None

try:
    import pyautogui
except ImportError:
    pyautogui = None

class OBSController:
    """Wrapper pour piloter OBS Studio via obs-websocket-py."""
    def __init__(self, host='localhost', port=4455, password=''):
        if obswebsocket is None:
            raise ImportError("Veuillez installer obs-websocket-py via pip.")
        self.client = obswebsocket.obsws(host, port, password)
        self.client.connect()

    def start_recording(self):
        self.client.call(obsrequests.StartRecord())

    def stop_recording(self):
        response = self.client.call(obsrequests.StopRecord())
        time.sleep(2)
        if hasattr(response, 'getOutputPath'):
            return response.getOutputPath()
        elif hasattr(response, 'datain') and 'outputPath' in response.datain:
            return response.datain['outputPath']
        return None

    def disconnect(self):
        self.client.disconnect()


is_recording = False
match_done = False
process = None

def record_match(agent1=None, agent2=None):
    global is_recording, match_done, process
    is_recording = False
    match_done = False
    last_state_time = time.time()
    last_hp1, last_hp2 = 100, 100
    last_x1, last_y1 = 0, 0
    last_x2, last_y2 = 0, 0
    final_video_path = None
    match_winner = 1
    
    print("Connexion à OBS...")
    try:
        obs_controller = OBSController(password="zR2dGpAMhzQxWsmj") 
    except Exception as e:
        print(f"Erreur OBS : {e}")
        return

    if agent1 is None:
        mod1 = importlib.import_module("agents.expert_master_bot.agent")
        agent1 = mod1.ParticipantAgent()
    if agent2 is None:
        mod2 = importlib.import_module("agents.rush_bot.agent")
        agent2 = mod2.ParticipantAgent()

    # --- Wrapper pour intercepter le début et la fin du match via l'Agent 1 ---
    def agent1_callback(state: GameState) -> AIAction:
        global is_recording, match_done
        nonlocal last_state_time, last_hp1, last_hp2, last_x1, last_y1, last_x2, last_y2
        
        last_state_time = time.time()
        
        if state.SelfTank:
            last_hp1 = state.SelfTank.Health
            last_x1 = state.SelfTank.Position.X
            last_y1 = state.SelfTank.Position.Y
        if state.EnemyTank:
            last_hp2 = state.EnemyTank.Health
            last_x2 = state.EnemyTank.Position.X
            last_y2 = state.EnemyTank.Position.Y
            
        # Si on reçoit un état et qu'on n'enregistre pas encore, c'est que le match commence !
        if not is_recording and not match_done:
            print("OBS: Start Recording (Match détecté !)")
            obs_controller.start_recording()
            is_recording = True
            
        action = agent1.get_action(state)
        
        # Détection de la fin du match
        hp1 = state.SelfTank.Health if state.SelfTank else 0
        hp2 = state.EnemyTank.Health if state.EnemyTank else 0
        out_of_bounds = False
        if state.SelfTank and (abs(state.SelfTank.Position.X) > 15000 or abs(state.SelfTank.Position.Y) > 10000):
            out_of_bounds = True
        if state.EnemyTank and (abs(state.EnemyTank.Position.X) > 15000 or abs(state.EnemyTank.Position.Y) > 10000):
            out_of_bounds = True
            
        if is_recording and (state.Done or hp1 <= 0 or hp2 <= 0 or out_of_bounds):
            print("OBS: Stop Recording (Fin du match détectée !)")
            video_path = obs_controller.stop_recording()
            if video_path:
                print(f"✅ Vidéo sauvegardée : {video_path}")
            is_recording = False
            match_done = True
            
        return action
        
    def agent2_callback(state: GameState) -> AIAction:
        action = agent2.get_action(state)
        return action

    # Lancer les deux serveurs TCP en parallèle
    def start_server1():
        play = Play(agent1_callback, tcp_port="5555")
        while not match_done:
            play.respond()
            
    def start_server2():
        play = Play(agent2_callback, tcp_port="5556")
        while not match_done:
            play.respond()

    t1 = threading.Thread(target=start_server1, daemon=True)
    t2 = threading.Thread(target=start_server2, daemon=True)
    t1.start()
    t2.start()

    print("\n" + "="*50)
    print("Serveurs démarrés sur les ports 5555 et 5556.")
    
    python_ai_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    unity_exe_path = os.path.join(os.path.dirname(python_ai_dir), "AutomathonGame.exe")
    print(f"Lancement de Unity : {unity_exe_path}")
    process = subprocess.Popen([unity_exe_path])
    
    if pyautogui is None:
        print("Veuillez sélectionner 'Agent (Port 5555)' pour J1 et 'Agent (Port 5556)' pour J2, puis JOUER !")
        print("(Installez 'pyautogui' pour automatiser cette étape : pip install pyautogui)")
    else:
        print("🤖 [MACRO] La souris va bouger toute seule dans 3 secondes. NE TOUCHEZ À RIEN !")
        
        def auto_setup_menu():
            time.sleep(3)
            screen_w, screen_h = pyautogui.size()
            mid_x, mid_y = screen_w // 2, screen_h // 2
            
            print("🤖 [MACRO] Clic initial...")
            pyautogui.click(mid_x, mid_y)
            time.sleep(1)
            
            print("🤖 [MACRO] Configuration J1...")
            pyautogui.click(745, 156)
            time.sleep(0.5)
            pyautogui.click(476, 883)
            time.sleep(0.5)
            pyautogui.press('backspace', presses=4)
            pyautogui.write('5555')
            time.sleep(0.5)
            
            print("🤖 [MACRO] Configuration J2...")
            pyautogui.click(1724, 156)
            time.sleep(0.5)
            pyautogui.click(1445, 886)
            time.sleep(0.5)
            pyautogui.press('backspace', presses=4)
            pyautogui.write('5556')
            time.sleep(0.5)
            
            print("🤖 [MACRO] Lancement de la partie !")
            pyautogui.click(mid_x, mid_y)
            time.sleep(0.5)
            pyautogui.click(mid_x, mid_y)
            
        threading.Thread(target=auto_setup_menu, daemon=True).start()

    print("="*50 + "\n")

    # Attendre que le match soit fini
    while not match_done:
        time.sleep(1)
        # Si on est en train d'enregistrer mais que Unity ne nous a rien envoyé depuis 3 secondes, 
        # c'est que le match s'est terminé brutalement (retour au menu ou fermeture) !
        if is_recording and (time.time() - last_state_time > 3.0):
            print("OBS: Stop Recording (Plus de messages de Unity, fin du match supposée !)")
            final_video_path = obs_controller.stop_recording()
            if final_video_path:
                print(f"✅ Vidéo sauvegardée : {final_video_path}")
            is_recording = False
            match_done = True
            
            # Calcul du gagnant
            if abs(last_x1) > 15000 or abs(last_y1) > 10000:
                match_winner = 2
            elif abs(last_x2) > 15000 or abs(last_y2) > 10000:
                match_winner = 1
            elif last_hp1 < last_hp2:
                match_winner = 2
            elif last_hp1 > last_hp2:
                match_winner = 1
            else:
                match_winner = 1
        
    print("\nArrêt de Unity...")
    process.kill()
    obs_controller.disconnect()
    print("Terminé.")
    return final_video_path, match_winner

if __name__ == "__main__":
    record_match()
