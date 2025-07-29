import asyncio
import json
import threading
# import redis
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List
import os
from redis import Redis
from fastapi.responses import HTMLResponse

# Redis connection
r = Redis(host="redis", db=int(os.environ.get('REDIS_READING_DB', 0)), port=int(os.environ.get('REDIS_PORT', 6379)), decode_responses=True)

# Enable Redis keyspace events for hash types (you can also do this in redis.conf)
r.config_set("notify-keyspace-events", "Kh")

app = FastAPI()

# Allow WebSocket test from Postman, browser, etc.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# # ---------------- REST API ----------------

@app.get("/api/engines")
def get_all_engines():
    keys = r.keys("engine:*")
    engines = {}
    for key in keys:
        name = key.split(":")[1]
        data = r.hgetall(key)
        engines[name] = data
    return JSONResponse(content=engines)


@app.get("/api/engine/{name}")
def get_engine(name: str):
    key = f"engine:{name}"
    if not r.exists(key):
        return JSONResponse(status_code=404, content={"error": "Not found"})
    return JSONResponse(content=r.hgetall(key))

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print("Send error:", e)

manager = ConnectionManager()

@app.websocket("/ws/engine")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await asyncio.sleep(1)  # Keep connection alive
    except:
        pass
    finally:
        manager.disconnect(websocket)

# Async wrapper for sending to WS
async def send_to_websockets(engine_name, data):
    await manager.broadcast(json.dumps({
        "engine": engine_name,
        "data": data
    }))

# Redis pubsub thread
def redis_pubsub_forward():
    pubsub = r.pubsub()
    # pubsub.psubscribe("__keyspace@0__:engine:*")
    pubsub.psubscribe("__keyspace@2__:engine:*")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    for message in pubsub.listen():
        if message["type"] == "pmessage":
            key = message["channel"].split(":")[-1]
            engine_name = key.split(":")[-1]
            data = r.hgetall(f"engine:{engine_name}")
            loop.run_until_complete(send_to_websockets(engine_name, data))

@app.on_event("startup")
def startup_event():
    thread = threading.Thread(target=redis_pubsub_forward, daemon=True)
    thread.start()

@app.get("/")
async def get():
    return HTMLResponse("""
    <html>
    <body>
    <h1>Engine WebSocket Test</h1>
    <script>
      let ws = new WebSocket("ws://localhost:8082/ws/engine");
      ws.onmessage = function(event) {
        console.log("Received: ", event.data);
        document.body.innerHTML += "<pre>" + event.data + "</pre>";
      };
    </script>
    </body>
    </html>
    """)