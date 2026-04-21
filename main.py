"""
Fuji Sakura Food Delivery - Main FastAPI Application
Entry point for the backend server

It initializes the FastAPI app, configures middleware, serves static files,
 and connects all feature-based routes like auth, restaurant, menu, and cart.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.core.config import settings
from app.routes import auth, restaurant, admin_auth, menu, cart, orders, websocket, payment, reviews, delivery
from app.models import admin_token  # Register AdminToken model with SQLAlchemy
from app.models import cod_settlement  # Register CodSettlement model

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for Fuji Sakura Food Delivery App",
    version="1.0.0",
    debug=settings.DEBUG
)

# Configure CORS for frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"],  # Next.js frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Create uploads directory if it doesn't exist
uploads_dir = Path("uploads")
uploads_dir.mkdir(exist_ok=True)#Prevents runtime errors,Auto-creates directory

'''I used FastAPI’s StaticFiles to serve uploaded images,
so the frontend can directly access menu and restaurant images'''
# Mount static files for uploaded images
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Include authentication routes
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])

# Include admin authentication routes
app.include_router(admin_auth.router, prefix="/api/admin", tags=["Admin Authentication"])

# Include restaurant routes
app.include_router(restaurant.router, prefix="/api/restaurant", tags=["Restaurant"])

# Include menu management routes
app.include_router(menu.router, prefix="/api/menu", tags=["Menu Management"])

# Include cart routes
app.include_router(cart.router, prefix="/api/cart", tags=["Cart Management"])

# Include order routes
app.include_router(orders.router, prefix="/api/orders", tags=["Order Management"])

# Include payment routes
app.include_router(payment.router, prefix="/api/payments", tags=["Payment Processing"])

# Include reviews routes
app.include_router(reviews.router, prefix="/api/reviews", tags=["Reviews"])

# Include delivery partner routes
app.include_router(delivery.router, prefix="/api/delivery", tags=["Delivery Partners"])

# Include WebSocket routes
app.include_router(websocket.router, tags=["WebSocket"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )



    