# Fuji Sakura Food Delivery - Backend API

FastAPI backend for the Fuji Sakura food delivery application with complete authentication system.

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your database and email credentials

# Run the server
python main.py
```

Server runs on: `http://localhost:8000`

## 🔗 Frontend Integration

This backend works with the frontend repository:
- **Frontend**: https://github.com/Dinul043/fuji-sakura-food-delivery
- **API Base URL**: `http://localhost:8000`

## 📊 Features

- ✅ Complete authentication system
- ✅ MySQL database integration  
- ✅ JWT token management
- ✅ OTP verification via Mailtrap
- ✅ Password reset functionality
- ✅ Email templates with branding
- ✅ Production-ready configuration

## 📁 Project Structure

```
food-delivery-backend/
├── app/
│   ├── core/          # Database & config
│   ├── models/        # Database models
│   ├── routes/        # API endpoints
│   └── utils/         # Utilities
├── main.py            # Server entry point
└── requirements.txt   # Dependencies
```

## 🔧 Configuration

Update `.env` file with your credentials:
- MySQL database connection
- Mailtrap email settings
- JWT secret key

## 📖 API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`