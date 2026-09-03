from dataclasses import field
from pydantic import BaseModel, Field
from typing import Union, List, Annotated, Literal

# Define your base structures
class Vector2Int(BaseModel):
    X: int
    Y: int

class StateBase(BaseModel):
    Position: Vector2Int

# Define your subclasses
class BulletState(StateBase):
    Type: Literal["BulletState"] = "BulletState"
    Radius: int
    Velocity: Vector2Int

class MissileState(StateBase):
    Type: Literal["MissileState"] = "MissileState"
    Radius: int
    Velocity: Vector2Int

class BaseWallState(StateBase):
    Size: Vector2Int
    RotationMilli: int

class WallState(BaseWallState):
    Type: Literal["WallState"] = "WallState"

class ShieldState(BaseWallState):
    Type: Literal["ShieldState"] = "ShieldState"
    Velocity: Vector2Int
    Health: int

class TankState(StateBase):
    Type: Literal["TankState"] = "TankState"
    Width: int
    Height: int
    Velocity: Vector2Int
    Health: int
    ShieldCooldownFramesLeft: int
    MissileCooldownFramesLeft: int
    MachineGunCooldownFramesLeft: int
    DashCooldownFramesLeft: int

State = Annotated[
    Union[BulletState, MissileState, WallState, ShieldState, TankState], 
    Field(discriminator='Type')
]

class GameState(BaseModel):
    SelfTank: TankState | None = None
    EnemyTank: TankState | None = None
    BulletStates: List[BulletState]  = Field(default_factory=lambda: [])
    MissileStates: List[MissileState] = Field(default_factory=lambda: [])
    WallStates: List[WallState] = Field(default_factory=lambda: [])
    ShieldStates: List[ShieldState] = Field(default_factory=lambda: [])
    Done: bool

class AIAction(BaseModel):
    MovingDirection: Vector2Int = Field(default_factory=lambda: Vector2Int(X=1000, Y=0))
    AimingDirection: Vector2Int = Field(default_factory=lambda: Vector2Int(X=0, Y=1000))
    MachineGun: bool = False
    Missile: bool = False
    Shield: bool = False
    Dash: bool = False

class AIMessage(BaseModel):
    Reset: bool
    DoneWithTraining: bool
    SelfAction: AIAction | None
    EnemyAction: AIAction | None
