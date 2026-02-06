"""
Fuji Sakura Food Delivery - Main FastAPI Application
Entry point for the backend server
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.core.config import settings
from app.routes import auth, restaurant, admin_auth, menu, cart

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
uploads_dir.mkdir(exist_ok=True)

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

# Health check endpoint
@app.get("/")
async def root():
    return {
        "message": "Fuji Sakura Food Delivery API",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )