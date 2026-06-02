# Fuji Sakura Food Delivery — Backend

FastAPI backend for the Fuji Sakura food delivery platform.

## Prerequisites

- Python 3.11+
- MySQL 8.0+
- Git

## Setup

```bash
# 1. Clone the repository
git clone https://github.com/Dinul043/fuji-sakura-backend.git
cd fuji-sakura-backend

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — set DATABASE_URL with your MySQL credentials:
#   With password:    mysql+pymysql://root:yourpassword@localhost:3306/fuji_sakura_db
#   Without password: mysql+pymysql://root:@localhost:3306/fuji_sakura_db

# 5. Run setup script (creates DB, tables, default admin)
python setup_database.py

# 6. Run the server
python main.py
```

Server starts at: `http://localhost:8000`

### Default Admin Account (created by setup script)
- Email: `admin@fujisakura.com`
- Password: `Admin@123`
- **Change this after first login!**

## Environment Variables

Copy `.env.example` to `.env` and fill in:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | MySQL connection string |
| `SECRET_KEY` | JWT signing key (any random string) |
| `RAZORPAY_KEY_ID` | Razorpay API key |
| `RAZORPAY_KEY_SECRET` | Razorpay secret |
| `MAIL_USERNAME` | SMTP username (Mailtrap for dev) |
| `MAIL_PASSWORD` | SMTP password |

## API Documentation

Once running, visit: `http://localhost:8000/docs` (Swagger UI)

## Project Structure

```
app/
├── core/          # Config, database connection
├── models/        # SQLAlchemy ORM models
├── routes/        # API endpoints
├── services/      # External services (Razorpay)
└── utils/         # Helpers (auth, email, geocoding)
```

## Tech Stack

- **FastAPI** — Web framework
- **SQLAlchemy** — ORM
- **MySQL** — Database
- **JWT** — Authentication
- **Razorpay** — Payments
- **WebSocket** — Real-time notifications
- **Nominatim** — Geocoding (OpenStreetMap)
