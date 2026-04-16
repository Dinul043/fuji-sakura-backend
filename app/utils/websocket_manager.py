"""
WebSocket Manager for real-time updates
Handles connections and broadcasts for order status, restaurant status, etc.
"""

from typing import Dict, Set
from fastapi import WebSocket
import json

class ConnectionManager:
    def __init__(self):
        # Store active connections by user_id
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # Store connections for order tracking by order_id
        self.order_connections: Dict[int, Set[WebSocket]] = {}
        # Store connections for restaurant updates
        self.restaurant_watchers: Dict[int, Set[WebSocket]] = {}
        # Store connections for restaurant dashboards (for new order notifications)
        self.restaurant_connections: Dict[int, Set[WebSocket]] = {}

    async def connect_user(self, websocket: WebSocket, user_id: int):
        """Connect a user for general updates"""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

    async def connect_order(self, websocket: WebSocket, order_id: int):
        """Connect to track a specific order"""
        await websocket.accept()
        if order_id not in self.order_connections:
            self.order_connections[order_id] = set()
        self.order_connections[order_id].add(websocket)

    async def connect_restaurant_watcher(self, websocket: WebSocket, restaurant_id: int):
        """Connect to watch restaurant status changes"""
        await websocket.accept()
        if restaurant_id not in self.restaurant_watchers:
            self.restaurant_watchers[restaurant_id] = set()
        self.restaurant_watchers[restaurant_id].add(websocket)

    def disconnect_user(self, websocket: WebSocket, user_id: int):
        """Disconnect a user"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    def disconnect_order(self, websocket: WebSocket, order_id: int):
        """Disconnect from order tracking"""
        if order_id in self.order_connections:
            self.order_connections[order_id].discard(websocket)
            if not self.order_connections[order_id]:
                del self.order_connections[order_id]

    def disconnect_restaurant_watcher(self, websocket: WebSocket, restaurant_id: int):
        """Disconnect from restaurant watching"""
        if restaurant_id in self.restaurant_watchers:
            self.restaurant_watchers[restaurant_id].discard(websocket)
            if not self.restaurant_watchers[restaurant_id]:
                del self.restaurant_watchers[restaurant_id]

    async def send_to_user(self, user_id: int, message: dict):
        """Send message to a specific user"""
        if user_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.add(connection)
            
            # Clean up disconnected connections
            for connection in disconnected:
                self.active_connections[user_id].discard(connection)

    async def send_order_update(self, order_id: int, message: dict):
        """Send update to all connections tracking an order"""
        if order_id in self.order_connections:
            disconnected = set()
            for connection in self.order_connections[order_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.add(connection)
            
            # Clean up disconnected connections
            for connection in disconnected:
                self.order_connections[order_id].discard(connection)

    async def broadcast_restaurant_update(self, restaurant_id: int, message: dict):
        """Broadcast restaurant status update to all watchers"""
        if restaurant_id in self.restaurant_watchers:
            disconnected = set()
            for connection in self.restaurant_watchers[restaurant_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.add(connection)
            
            # Clean up disconnected connections
            for connection in disconnected:
                self.restaurant_watchers[restaurant_id].discard(connection)
    
    async def connect_restaurant(self, websocket: WebSocket, restaurant_id: int):
        """Connect restaurant dashboard for new order notifications"""
        await websocket.accept()
        if restaurant_id not in self.restaurant_connections:
            self.restaurant_connections[restaurant_id] = set()
        self.restaurant_connections[restaurant_id].add(websocket)
        print(f"✅ Restaurant {restaurant_id} connected for notifications")
    
    def disconnect_restaurant(self, websocket: WebSocket, restaurant_id: int):
        """Disconnect restaurant dashboard"""
        if restaurant_id in self.restaurant_connections:
            self.restaurant_connections[restaurant_id].discard(websocket)
            if not self.restaurant_connections[restaurant_id]:
                del self.restaurant_connections[restaurant_id]
            print(f"🔌 Restaurant {restaurant_id} disconnected")
    
    async def send_restaurant_notification(self, restaurant_id: int, notification_data: dict):
        """
        Send new order notification to specific restaurant dashboard.
        Wraps data as {"event": "new_order", "data": ...} for new orders.
        For status updates, use send_restaurant_status_update instead.
        """
        if restaurant_id in self.restaurant_connections:
            disconnected = set()
            message = {
                "event": "new_order",
                "data": notification_data
            }
            
            for connection in self.restaurant_connections[restaurant_id]:
                try:
                    await connection.send_json(message)
                    print(f"📤 Sent new order notification to restaurant {restaurant_id}")
                except Exception as e:
                    print(f"❌ Failed to send notification: {e}")
                    disconnected.add(connection)
            
            # Clean up disconnected connections
            for connection in disconnected:
                self.restaurant_connections[restaurant_id].discard(connection)
        else:
            print(f"⚠️ No active connections for restaurant {restaurant_id}")

    async def send_restaurant_status_update(self, restaurant_id: int, message: dict):
        """
        Send order status update directly to restaurant dashboard (no wrapping).
        Used when delivery partner accepts/delivers an order.
        """
        if restaurant_id in self.restaurant_connections:
            disconnected = set()
            for connection in self.restaurant_connections[restaurant_id]:
                try:
                    await connection.send_json(message)
                    print(f"📤 Sent status update to restaurant {restaurant_id}: {message.get('status')}")
                except Exception as e:
                    print(f"❌ Failed to send status update: {e}")
                    disconnected.add(connection)
            for connection in disconnected:
                self.restaurant_connections[restaurant_id].discard(connection)
        else:
            print(f"⚠️ No active connections for restaurant {restaurant_id}")

    async def broadcast_to_delivery_partners(self, message: dict):
        """
        Broadcast a message to all connected delivery partner dashboards.
        Delivery partners connect on restaurant_id=0 channel.
        """
        if 0 in self.restaurant_connections:
            disconnected = set()
            for connection in self.restaurant_connections[0]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"❌ Failed to send to delivery partner: {e}")
                    disconnected.add(connection)
            for connection in disconnected:
                self.restaurant_connections[0].discard(connection)

# Global instance
manager = ConnectionManager()
