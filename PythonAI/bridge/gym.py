import zmq
from bridge.datatypes import *

class Gym:
    def __init__(self, tcp_port:str="5555"):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect("tcp://localhost:" + tcp_port)

        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)

    def step(self, self_action: AIAction, enemy_action: AIAction, tcp_connection_timeout : None | int=500):

        self.__send_action__(AIMessage(Reset=False, DoneWithTraining=False, SelfAction=self_action, EnemyAction=enemy_action))

        if self.poller.poll(tcp_connection_timeout):
            return self.__receive_state__()
        
        raise TimeoutError()

    def reset(self, tcp_connection_timeout : None | int=500) -> GameState:
        self.__send_action__(AIMessage(Reset=True, DoneWithTraining=False, SelfAction=None, EnemyAction=None))
        
        if self.poller.poll(tcp_connection_timeout):
            return self.__receive_state__()
        
        raise TimeoutError("Make sure the Headless version of the game is running before launching the python training script!")

    def end_training(self):
        self.__send_action__(AIMessage(Reset=False, DoneWithTraining=True, SelfAction=None, EnemyAction=None))

    def __receive_state__(self):
        state_string = self.socket.recv_string()
        return GameState.model_validate_json(state_string)
    
    def __send_action__(self, msg: AIMessage):
        s = msg.model_dump_json()
        self.socket.send_string(s)