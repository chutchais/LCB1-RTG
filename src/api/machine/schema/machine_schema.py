from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class ItemBase(BaseModel):
    name: str
    units: Optional[str] = None
    current_value: int = 0


class ItemResponse(ItemBase):
    id: int
    equipment_name: str
    parameter_name: str
    monitor: bool


class MachineBase(BaseModel):
    name: str
    title: Optional[str] = None
    ip: Optional[str] = None


class MachineCreate(MachineBase):
    pass


class MachineUpdate(BaseModel):
    title: Optional[str] = None
    ip: Optional[str] = None


class MachineResponse(MachineBase):
    created: datetime
    updated: Optional[datetime] = None
    items: Optional[list] = []


class MachineData(BaseModel):
    """Real-time machine data"""
    equipment: str
    timestamp: datetime
    data: Dict[str, Any]


class WebSocketMessage(BaseModel):
    """WebSocket message format"""
    machine: str
    data: Dict[str, Any]
    timestamp: Optional[str] = None