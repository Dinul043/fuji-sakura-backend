# Fuji Sakura Food Delivery - Backend Project Structure

## 🏗️ Architecture Overview
FastAPI-based REST API with MySQL database, JWT authentication, and email integration via Mailtrap.

## 📁 Project Structure

```
food-delivery-backend/
├── app/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py          # Configuration settings
│   │   └── database.py        # Database connection & session management
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py           # User SQLAlchemy model
│   │   └── user_token.py     # UserToken SQLAlchemy model
│   ├── routes/
│   │   ├── __init__.py
│   │   └── auth.py           # Authentication endpoints
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── email.py          # Email sending utilities (Mailtrap)
│   │   ├── otp.py            # OTP generation & validation
│   │   └── security.py       # Password hashing & JWT tokens
│   └── __init__.py
├── .env                      # Environment variables (gitignored)
├── .env.example             # Environment template
├── .gitignore               # Git ignore rules
├── database_migration.sql   # Database migration script (two-table structure)
├── main.py                  # FastAPI application entry point
├── requirements.txt         # Python dependencies
├── BACKEND_PROJECT_STRUCTURE.md  # This documentation
└── SQL_QUERIES_REFERENCE.md      # SQL query examples
```

## 🔧 Core Components

### 1. **Database Configuration** (`app/core/`)
- **config.py**: Environment-based settings management
- **database.py**: SQLAlchemy engine, session factory, and dependency injection

### 2. **Data Models** (`app/models/`)
- **user.py**: Main user model with core user data
  - Fields: id, email, name, password, is_verified, is_active
  - Timestamps: created_at, updated_at, last_login, deleted_at
  - Relationship: One-to-many with UserToken
- **user_token.py**: Temporary token model for OTP and reset tokens
  - Fields: id, user_id (FK), otp, otp_expires_at, reset_token, reset_token_expires_at
  - Auto-deleted when user is deleted (CASCADE)
  - Automatically cleared after successful verification

### 3. **API Routes** (`app/routes/`)
- **auth.py**: Complete authentication system
  - `POST /signup` - User registration with OTP
  - `POST /verify-otp` - Email verification
  - `POST /login` - User authentication
  - `POST /resend-otp` - Resend verification code
  - `POST /forgot-password` - Password reset request
  - `POST /reset-password` - Password reset with token
  - `PUT /update-user-details` - Update user info after verification

### 4. **Utilities** (`app/utils/`)
- **security.py**: Password hashing (bcrypt) & JWT token management
- **otp.py**: 4-digit OTP generation & expiration handling
- **email.py**: Mailtrap SMTP integration for OTP & reset emails

## 🔐 Authentication Flow

### User Registration (Sign Up)
1. **Email Submission** → Creates user with temp data + generates OTP
2. **OTP Email** → Sent via Mailtrap (4-digit code, 10min expiry)
3. **OTP Verification** → Activates account (`is_verified = true`)
4. **Details Update** → User provides real name/password
5. **Complete Registration** → User logged in & redirected

### User Login (Sign In)
1. **Credentials Check** → Email/password validation
2. **Account Verification** → Must be verified to login
3. **JWT Token** → Generated for authenticated sessions
4. **Login Success** → User redirected to dashboard

## 🗄️ Database Schema (Two-Table Structure)

### Users Table (Main Data)
```sql
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    deleted_at TIMESTAMP NULL
);
```

### User Tokens Table (Temporary Data)
```sql
CREATE TABLE user_tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    otp VARCHAR(6) NULL,
    otp_expires_at TIMESTAMP NULL,
    reset_token VARCHAR(6) NULL,
    reset_token_expires_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

### Benefits of Two-Table Structure:
- **Cleaner main table**: Users table only contains permanent data
- **Better performance**: Smaller main table for frequent queries
- **Automatic cleanup**: Tokens auto-deleted when user is deleted
- **Future-ready**: Easy to add features like email updates, account deletion
- **Security**: Temporary sensitive data isolated and auto-cleared

## 📧 Email Integration

### Mailtrap Configuration
- **SMTP Server**: sandbox.smtp.mailtrap.io:2525
- **Authentication**: Username/Password based
- **Email Templates**: OTP verification & password reset
- **Testing**: All emails captured in Mailtrap inbox

### Email Types
1. **OTP Verification**: 4-digit code for account activation
2. **Password Reset**: 4-digit token for password recovery
3. **Welcome Email**: Account creation confirmation (future)

## 🔑 Security Features

### Password Security
- **Hashing**: bcrypt with salt rounds
- **Validation**: Minimum 8 chars, 5 uppercase, 1 lowercase, 1 number
- **Storage**: Only hashed passwords stored

### JWT Tokens
- **Algorithm**: HS256
- **Expiry**: 30 days
- **Claims**: User ID in subject field
- **Secret**: Environment-based secret key

### OTP Security
- **Length**: 4 digits (manager preference)
- **Expiry**: 10 minutes
- **Single Use**: Cleared after verification
- **Rate Limiting**: Built-in via expiry mechanism

## 🌐 API Endpoints

### Authentication Routes (`/api/auth/`)
| Method | Endpoint | Description | Request Body |
|--------|----------|-------------|--------------|
| POST | `/signup` | Create new user account | `{email, firstName, lastName, password}` |
| POST | `/verify-otp` | Verify email with OTP | `{email, otp}` |
| POST | `/login` | User authentication | `{email, password}` |
| POST | `/resend-otp` | Resend verification OTP | `{email}` |
| POST | `/forgot-password` | Request password reset | `{email}` |
| POST | `/reset-password` | Reset password with token | `{email, token, newPassword}` |
| PUT | `/update-user-details` | Update user info | `{email, firstName, lastName, password}` |

### Response Formats
- **Success**: JSON with data/message
- **Error**: JSON with error details & HTTP status codes
- **Authentication**: JWT token in response for login/verification

## 🔧 Environment Configuration

### Required Variables (.env)
```env
# Database
DATABASE_URL=mysql+pymysql://root:20cs1149@localhost:3306/fuji_sakura_db

# JWT Security
SECRET_KEY=fuji-sakura-super-secret-key-2024
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_DAYS=30

# Mailtrap Email
MAIL_USERNAME=ac8c79e5058631
MAIL_PASSWORD=bd9bc02f0a4c0f
MAIL_FROM=noreply@fujisakura.com
MAIL_SERVER=sandbox.smtp.mailtrap.io
MAIL_PORT=2525

# Application
APP_NAME=Fuji Sakura Food Delivery
DEBUG=True
```

## 🚀 Deployment & Running

### Development Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Run database migration (if needed)
# Execute database_migration.sql in MySQL Workbench

# Run development server
python main.py
# Server runs on http://localhost:8000
```

### API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## ✅ Current Status

### Completed Features
- ✅ User registration with email OTP verification
- ✅ User login with JWT authentication
- ✅ Password reset functionality
- ✅ Email integration via Mailtrap
- ✅ Secure password hashing
- ✅ Database schema & models
- ✅ API documentation
- ✅ Error handling & validation
- ✅ Frontend integration (signup flow working)

### Tested & Working
- ✅ Complete signup flow (email → OTP → details → login)
- ✅ Two-table database structure with automatic token cleanup
- ✅ OTP generation & email delivery via Mailtrap
- ✅ Database user creation & verification
- ✅ Frontend-backend integration
- ✅ Error handling & user feedback
- ✅ Automatic token deletion after verification
- ✅ Clean folder structure without cache files

### Next Steps (Future Development)
- 🔄 Restaurant management endpoints
- 🔄 Menu & food item APIs
- 🔄 Order management system
- 🔄 Payment integration
- 🔄 User profile management
- 🔄 Admin dashboard APIs
- 🔄 Real-time order tracking
- 🔄 Push notifications

## 🧪 Testing

### Database Testing
```sql
-- Check user creation and token management
SELECT u.email, u.is_verified, ut.otp, ut.otp_expires_at 
FROM users u 
LEFT JOIN user_tokens ut ON u.id = ut.user_id 
ORDER BY u.created_at DESC LIMIT 5;

-- Verify automatic token cleanup after verification
SELECT COUNT(*) as active_tokens FROM user_tokens;
```

### Manual Testing Flow
1. **Signup**: Enter email → Check `user_tokens` table for OTP
2. **Verify**: Enter OTP → Check token is deleted from `user_tokens`
3. **Complete**: Fill details → User verified, no tokens remaining

---

**Last Updated**: January 21, 2026  
**Status**: Authentication system complete and working  
**Next Phase**: Restaurant & menu management APIs


need to update : separte table for otp and mails 


updated at have to be add in tables and need to add deleted at(optional)