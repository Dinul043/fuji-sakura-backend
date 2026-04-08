"""
WebSocket endpoints for real-time updates
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.utils.websocket_manager import manager
from app.utils.security import verify_token
import json

router = APIRouter()

@router.websocket("/ws/orders/{order_id}")
async def websocket_order_tracking(
    websocket: WebSocket,
    order_id: int
):
    """WebSocket endpoint for real-time order tracking"""
    await manager.connect_order(websocket, order_id)
    try:
        while True:
            # Keep connection alive and listen for messages
            data = await websocket.receive_text()
            # Echo back for heartbeat
            await websocket.send_json({"type": "heartbeat", "status": "connected"})
    except WebSocketDisconnect:
        manager.disconnect_order(websocket, order_id)

@router.websocket("/ws/restaurant/{restaurant_id}")
async def websocket_restaurant_updates(
    websocket: WebSocket,
    restaurant_id: int
):
    """WebSocket endpoint for restaurant status updates"""
    await manager.connect_restaurant_watcher(websocket, restaurant_id)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            await websocket.send_json({"type": "heartbeat", "status": "connected"})
    except WebSocketDisconnect:
        manager.disconnect_restaurant_watcher(websocket, restaurant_id)

@router.websocket("/ws/user/{user_id}")
async def websocket_user_updates(
    websocket: WebSocket,
    user_id: int
):
    """WebSocket endpoint for user-specific updates"""
    await manager.connect_user(websocket, user_id)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            await websocket.send_json({"type": "heartbeat", "status": "connected"})
    except WebSocketDisconnect:
        manager.disconnect_user(websocket, user_id)

@router.websocket("/ws/restaurant-dashboard/{restaurant_id}")
async def websocket_restaurant_dashboard(
    websocket: WebSocket,
    restaurant_id: int
):
    """WebSocket endpoint for restaurant dashboard - receives new order notifications"""
    await manager.connect_restaurant(websocket, restaurant_id)
    try:
        while True:
            # Keep connection alive and listen for heartbeat
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            else:
                await websocket.send_json({"type": "heartbeat", "status": "connected"})
    except WebSocketDisconnect:
        manager.disconnect_restaurant(websocket, restaurant_id)

@router.websocket("/ws/admin")
async def websocket_admin(websocket: WebSocket):
    """WebSocket endpoint for admin dashboard — receives delivery partner application notifications"""
    # Use restaurant_id=0 as admin broadcast channel
    await manager.connect_restaurant(websocket, 0)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect_restaurant(websocket, 0)
