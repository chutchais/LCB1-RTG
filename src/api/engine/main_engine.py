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

from fastapi import Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# Added on June 11,2026 -- To support new management of WebSocket connections and error handling
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Set
import asyncio

from pathlib import Path

# Redis connection
r = Redis(host="redis", db=int(os.environ.get('REDIS_READING_DB', 0)), port=int(os.environ.get('REDIS_PORT', 6379)), decode_responses=True)

# Enable Redis keyspace events for hash types (you can also do this in redis.conf)
r.config_set("notify-keyspace-events", "Kh")

app = FastAPI()

# Templates setup
BASE_DIR = Path(__file__).resolve().parent



# Allow WebSocket test from Postman, browser, etc.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the dashboard HTML file directly"""
    html_path = BASE_DIR / "templates" / "dashboard3.html"
    
    if not html_path.exists():
        return HTMLResponse(content=f"Dashboard file not found at {html_path}", status_code=404)
    
    # Read and return the HTML file
    html_content = html_path.read_text(encoding='utf-8')
    return HTMLResponse(content=html_content)

# @app.get("/test-dashboard", response_class=HTMLResponse)
# async def test_dashboard():
#     """Serve the test HTML file directly"""
#     html_path = BASE_DIR / "templates" / "test.html"
    
#     if not html_path.exists():
#         return HTMLResponse(content=f"Test file not found at {html_path}", status_code=404)
    
#     html_content = html_path.read_text(encoding='utf-8')
#     return HTMLResponse(content=html_content)

# Route to serve the HTML dashboard
# @app.get("/dashboard", response_class=HTMLResponse)
# async def get_dashboard(request: Request):
#     return templates.TemplateResponse("dashboard3.html", {"request": request})


# Added on Oct 13,2025 -- TO show battery status on dashboard
# @app.get("/battery", response_class=HTMLResponse)
# async def get_battery(request: Request):
#     return templates.TemplateResponse("battery.html", {"request": request})

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
# # Added on June 11,2026 -- To support new management of WebSocket connections and error handling
# # Active WebSocket connections management
# class ConnectionManager:
#     def __init__(self):
#         self.active_connections: Set[WebSocket] = set()
    
#     async def connect(self, websocket: WebSocket):
#         await websocket.accept()
#         self.active_connections.add(websocket)
#         print(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
#     def disconnect(self, websocket: WebSocket):
#         if websocket in self.active_connections:
#             self.active_connections.remove(websocket)
#             print(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
#     async def send_message(self, message: dict, websocket: WebSocket):
#         """Send message to a specific websocket with error handling"""
#         try:
#             await websocket.send_json(message)
#         except RuntimeError as e:
#             if "Cannot call 'send' once a close message has been sent" in str(e):
#                 # Connection is closing, remove it
#                 self.disconnect(websocket)
#             else:
#                 print(f"Unexpected error sending message: {e}")
#         except WebSocketDisconnect:
#             self.disconnect(websocket)
#         except Exception as e:
#             print(f"Error sending message: {e}")
    
#     async def broadcast(self, message: dict):
#         """Broadcast message to all connected clients"""
#         disconnected = set()
#         for connection in self.active_connections:
#             try:
#                 await connection.send_json(message)
#             except (RuntimeError, WebSocketDisconnect) as e:
#                 # Mark for removal
#                 disconnected.add(connection)
#             except Exception as e:
#                 print(f"Broadcast error: {e}")
#                 disconnected.add(connection)
        
#         # Clean up disconnected clients
#         for connection in disconnected:
#             self.disconnect(connection)

# manager = ConnectionManager()

# @app.websocket("/ws/engine")
# async def websocket_endpoint(websocket: WebSocket):
#     await manager.connect(websocket)
#     try:
#         # Keep the connection alive and handle incoming messages
#         while True:
#             # Wait for any message from client (ping/pong)
#             data = await websocket.receive_text()
            
#             # Optional: Handle client pings
#             if data == "ping":
#                 await manager.send_message({"type": "pong"}, websocket)
                
#     except WebSocketDisconnect:
#         manager.disconnect(websocket)
#     except RuntimeError as e:
#         if "Cannot call 'send' once a close message has been sent" in str(e):
#             manager.disconnect(websocket)
#         else:
#             print(f"WebSocket error: {e}")
#             manager.disconnect(websocket)
#     except Exception as e:
#         print(f"Unexpected WebSocket error: {e}")
#         manager.disconnect(websocket)




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
      let ws = new WebSocket("ws://10.24.50.96:8082/ws/engine");
      ws.onmessage = function(event) {
        console.log("Received: ", event.data);
        document.body.innerHTML += "<pre>" + event.data + "</pre>";
      };
    </script>
    </body>
    </html>
    """)