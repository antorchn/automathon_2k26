import zmq
from bridge.datatypes import *
from collections.abc import Callable

class Play:
    def __init__(self, decide_action_function: Callable[[GameState], AIAction], tcp_port:str="5555"):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind("tcp://*:" + tcp_port)

        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)

        self.decide_action = decide_action_function
        print(f"Play server started on {tcp_port} and up and running.")

    def respond(self, timeout: int | None=500):
        if self.poller.poll(timeout):
            state = self.__receive_state__()

            if isinstance(state, str):
                self.socket.send_string("Pong")
                return

            action = self.decide_action(state)
            self.__send_action__(AIMessage(Reset=False, DoneWithTraining=False, SelfAction=action, EnemyAction=None))
    
    def __receive_state__(self) -> GameState | str:
        state_string = self.socket.recv_string()
        if state_string == "Ping":
            return "Ping"
        
        try:
            return GameState.model_validate_json(state_string)
        except Exception as e:
            print(f"\n[ERREUR PYDANTIC] Impossible de parser le GameState envoyé par Unity !")
            print(f"JSON reçu : {state_string}")
            print(f"Détail de l'erreur : {e}\n")
            raise e
    
    def __send_action__(self, msg: AIMessage):
        s = msg.model_dump_json()
        self.socket.send_string(s)