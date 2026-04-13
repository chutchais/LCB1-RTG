import json
import threading
import time
from redis import Redis
import os
import logging
import asyncio

logger = logging.getLogger(__name__)

# Store the main event loop
main_loop = None


class MachineRedisListener:
    """Listen to Redis pub/sub and broadcast to WebSocket"""
    
    def __init__(self):
        self.redis_host = os.environ.get('REDIS_HOST', 'redis')
        self.redis_port = int(os.environ.get('REDIS_PORT', 6379))
        self.redis_db = int(os.environ.get('REDIS_READING_DB', 0))
        self.is_running = False
        self.thread = None
        logger.info(f"Listener initialized: {self.redis_host}:{self.redis_port} db={self.redis_db}")
    
    def start(self, loop=None):
        """Start listener in background thread"""
        global main_loop
        
        if self.is_running:
            logger.warning("Listener already running")
            return
        
        # Store the main event loop
        main_loop = loop
        logger.info(f"Main event loop set: {main_loop}")
        
        self.is_running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        logger.info("Redis Listener Thread Started")
    
    def _listen_loop(self):
        """Main listener loop"""
        logger.info("Listener thread is running")
        
        reconnect_count = 0
        while self.is_running:
            try:
                logger.info(f"Connecting to Redis ({reconnect_count})...")
                r = Redis(
                    host=self.redis_host,
                    port=self.redis_port,
                    db=self.redis_db,
                    decode_responses=True,
                    socket_keepalive=True,
                    health_check_interval=30
                )
                r.ping()
                logger.info("Redis Connected")
                reconnect_count = 0
                
                # Subscribe
                pubsub = r.pubsub(ignore_subscribe_messages=True)
                pubsub.subscribe('MACHINE-NOTIFY', 'RTG-NOTIFY')
                logger.info("Subscribed to MACHINE-NOTIFY, RTG-NOTIFY")
                
                # Listen
                logger.info("Listening for messages...")
                for message in pubsub.listen():
                    if not self.is_running:
                        logger.info("Listener stopping")
                        break
                    
                    if message and message.get('type') == 'message':
                        try:
                            channel = message['channel']
                            data = json.loads(message['data'])
                            machine_name = data.get('machine', 'Unknown')
                            
                            logger.info(f"[{channel}] Received: {machine_name}")
                            
                            # Broadcast to WebSocket
                            self._broadcast_to_websocket(machine_name, data)
                        
                        except Exception as e:
                            logger.error(f"Message processing error: {e}", exc_info=True)
                
                pubsub.close()
                r.close()
            
            except Exception as e:
                reconnect_count += 1
                logger.error(f"Connection error: {e}", exc_info=True)
                logger.info("Reconnecting in 3 seconds...")
                time.sleep(3)
    
    def _broadcast_to_websocket(self, machine_name, data):
        """Broadcast to WebSocket clients"""
        global main_loop
        
        try:
            from ws.machine_websocket import machine_manager
            
            if main_loop is None or main_loop.is_closed():
                logger.warning("Main event loop not available")
                return
            
            logger.info(f"Broadcasting to {machine_manager.get_connection_count()} clients")
            
            # Schedule the coroutine
            future = asyncio.run_coroutine_threadsafe(
                machine_manager.broadcast_machine_data(
                    machine_name=machine_name,
                    data=data
                ),
                main_loop
            )
            
            # Don't wait for result, just schedule it
            logger.info("Broadcast scheduled (non-blocking)")
            
        except Exception as e:
            logger.error(f"Broadcast error: {e}", exc_info=True)
    
    def stop(self):
        """Stop the listener"""
        logger.info("Stopping listener...")
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Listener stopped")


# Global instance
machine_redis_listener = MachineRedisListener()