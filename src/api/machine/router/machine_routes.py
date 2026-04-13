from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from redis import Redis
import os
import json

# Redis connection
r = Redis(
    host=os.environ.get('REDIS_HOST', 'redis'),
    db=int(os.environ.get('REDIS_READING_DB', 0)),
    port=int(os.environ.get('REDIS_PORT', 6379)),
    decode_responses=True
)

router = APIRouter(prefix="/api/machines", tags=["machines"])


@router.get("")
def get_all_machines():
    """
    Get all machines/equipment
    Returns: {"machine_name": {field: value, ...}}
    """
    try:
        keys = r.keys("machine:*")
        machines = {}
        for key in keys:
            # Extract machine name from key format: machine:name
            parts = key.split(":")
            if len(parts) >= 2:
                name = ":".join(parts[1:])  # Handle names with colons
                data = r.hgetall(key)
                machines[name] = data
        
        return JSONResponse(content=machines)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{machine_name}")
def get_machine(machine_name: str):
    """
    Get specific machine data by name
    """
    try:
        key = f"machine:{machine_name}"
        if not r.exists(key):
            raise HTTPException(status_code=404, detail=f"Machine '{machine_name}' not found")
        
        data = r.hgetall(key)
        return JSONResponse(content=data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{machine_name}/items")
def get_machine_items(machine_name: str):
    """
    Get all items/parameters for a specific machine
    """
    try:
        key = f"machine:{machine_name}:items"
        if not r.exists(key):
            raise HTTPException(status_code=404, detail=f"No items found for machine '{machine_name}'")
        
        items = r.hgetall(key)
        return JSONResponse(content=items)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{machine_name}/latest")
def get_machine_latest(machine_name: str):
    """
    Get latest data for a specific machine
    """
    try:
        key = f"machine:{machine_name}:LATEST"
        if not r.exists(key):
            raise HTTPException(status_code=404, detail=f"No latest data found for machine '{machine_name}'")
        
        data = r.hgetall(key)
        return JSONResponse(content=data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{machine_name}/data")
def post_machine_data(machine_name: str, data: dict):
    """
    Post machine data to Redis (for external systems)
    """
    try:
        key = f"machine:{machine_name}:LATEST"
        r.hset(key, mapping=data)
        r.expire(key, 3600)  # Expire after 1 hour
        
        return JSONResponse(content={
            "status": "success",
            "machine": machine_name,
            "message": "Data saved successfully"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/connections")
def get_connection_status():
    """
    Get Redis connection status
    """
    try:
        r.ping()
        return JSONResponse(content={"status": "connected", "redis": True})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis connection error: {str(e)}")