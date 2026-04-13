import asyncio
import json
import os
import sys
import logging
from fastapi import FastAPI, WebSocket, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from redis import Redis
from contextlib import asynccontextmanager

import os
from pathlib import Path
from fastapi.templating import Jinja2Templates

# Get absolute path to templates
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
print(f"Template directory: {TEMPLATE_DIR}")
print(f"Exists: {os.path.exists(TEMPLATE_DIR)}")

# Templates setup
templates = Jinja2Templates(directory=TEMPLATE_DIR)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

logger.info("=" * 60)
logger.info("🚀 main_machine.py is loading...")
logger.info("=" * 60)

# Import routers and websocket
try:
    from router.machine_routes import router as machine_router
    logger.info("✓ Imported machine_routes")
except Exception as e:
    logger.error(f"✗ Failed to import machine_routes: {e}")
    import traceback
    traceback.print_exc()

try:
    from ws.machine_websocket import machine_manager
    logger.info("✓ Imported machine_manager")
except Exception as e:
    logger.error(f"✗ Failed to import machine_manager: {e}")
    import traceback
    traceback.print_exc()

try:
    from redis_listener import machine_redis_listener
    logger.info("✓ Imported machine_redis_listener")
except Exception as e:
    logger.error(f"✗ Failed to import machine_redis_listener: {e}")
    import traceback
    traceback.print_exc()


# Redis connection
r = Redis(
    host=os.environ.get('REDIS_HOST', 'redis'),
    db=int(os.environ.get('REDIS_READING_DB', 0)),
    port=int(os.environ.get('REDIS_PORT', 6379)),
    decode_responses=True
)

# Templates setup
templates = Jinja2Templates(directory="templates")


# ==================== Startup/Shutdown Events ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    logger.info("\n" + "=" * 60)
    logger.info("📍 LIFESPAN STARTUP EVENT FIRED")
    logger.info("=" * 60)
    
    try:
        # Get the current event loop and pass it to the listener
        loop = asyncio.get_event_loop()
        logger.info(f"Current event loop: {loop}")
        
        logger.info("→ Starting Machine Redis Listener...")
        machine_redis_listener.start(loop=loop)  # ← Pass the loop here
        logger.info("✓ Listener started successfully")
    except Exception as e:
        logger.error(f"✗ Failed to start listener: {e}")
        import traceback
        traceback.print_exc()
    
    yield
    
    logger.info("\n" + "=" * 60)
    logger.info("📍 LIFESPAN SHUTDOWN EVENT FIRED")
    logger.info("=" * 60)
    
    try:
        machine_redis_listener.stop()
        logger.info("✓ Listener stopped")
    except Exception as e:
        logger.error(f"✗ Failed to stop listener: {e}")


# FastAPI app
logger.info("\n→ Creating FastAPI app...")

app = FastAPI(
    title="Machine API Service",
    description="Real-time Machine/Equipment monitoring API with WebSocket support",
    version="1.0.0",
    lifespan=lifespan
)

logger.info("✓ FastAPI app created with lifespan")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(machine_router)


# ==================== Dashboard Routes ====================

# @app.get("/dashboard", response_class=HTMLResponse)
# async def get_dashboard(request: Request):
#     """Serve machine monitoring dashboard"""
#     return templates.TemplateResponse("machine_dashboard.html", {"request": request})
# ==================== Dashboard Routes ====================

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    """Serve machine monitoring dashboard"""
    with open("/app/templates/machine_dashboard.html", "r") as f:
        return f.read()

# ==================== WebSocket Routes ====================

@app.websocket("/ws/machine")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time machine data streaming"""
    await machine_manager.connect(websocket)
    try:
        while True:
            await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        machine_manager.disconnect(websocket)


# ==================== Health Check ====================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Machine API",
        "websocket_connections": machine_manager.get_connection_count()
    }


# ==================== Info ====================

@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "name": "Machine API Service",
        "version": "1.0.0",
        "endpoints": {
            "api": "/api/machines",
            "dashboard": "/dashboard",
            "websocket": "/ws/machine",
            "health": "/health",
            "docs": "/docs"
        }
    }


logger.info("✓ main_machine.py finished loading\n")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8083,
        reload=True
    )