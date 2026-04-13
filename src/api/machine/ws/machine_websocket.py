import json
from typing import List
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)


class MachineConnectionManager:
    """Manages WebSocket connections for real-time machine data"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        logger.info("MachineConnectionManager initialized")
    
    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a disconnected WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast(self, message: str):
        """Send message to all connected clients"""
        if not self.active_connections:
            logger.debug("No WebSocket clients connected")
            return
        
        disconnected_clients = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.warning(f"Error sending to client: {e}")
                disconnected_clients.append(connection)
        
        # Clean up disconnected clients
        for client in disconnected_clients:
            self.disconnect(client)
    
    async def broadcast_machine_data(self, machine_name: str, data: dict):
        """
        Broadcast machine data to all connected clients
        
        Args:
            machine_name: Name of the equipment/machine
            data: Dictionary containing equipment data
        """
        try:
            from datetime import datetime
            
            message = json.dumps({
                "machine": machine_name,
                "data": data,
                "timestamp": datetime.now().isoformat()
            })
            
            logger.info(f"Broadcasting to WebSocket: {machine_name} ({len(self.active_connections)} clients)")
            await self.broadcast(message)
            logger.info("Broadcast complete")
            
        except Exception as e:
            logger.error(f"Broadcast error: {e}", exc_info=True)
    
    def get_connection_count(self) -> int:
        """Get current number of active connections"""
        return len(self.active_connections)


# Global instance
machine_manager = MachineConnectionManager()