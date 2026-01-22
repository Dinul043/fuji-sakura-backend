"""
Fuji Sakura Food Delivery - Main FastAPI Application
Entry point for the backend server
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routes import auth

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
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Next.js frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include authentication routes
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])

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