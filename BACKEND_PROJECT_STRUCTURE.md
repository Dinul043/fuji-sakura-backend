# Fuji Sakura Food Delivery - Backend Project Structure

## 🏗️ Architecture Overview
FastAPI-based REST API with MySQL database, JWT authentication, and email integration via Mailtrap.

## 📁 Project Structure & Frontend Connections

```
food-delivery-backend/
├── app/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py          # App settings & environment variables
│   │   └── database.py        # MySQL connection for all frontend data
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py           # Customer accounts (login/signup pages)
│   │   ├── user_token.py     # OTP verification (signup/forgot password)
│   │   ├── admin.py          # Admin accounts (admin portal)
│   │   └── restaurant_application.py  # Restaurant applications (partnership)
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py           # Customer authentication APIs
│   │   ├── admin_auth.py     # Admin authentication APIs
│   │   └── restaurant.py     # Restaurant application APIs
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── email.py          # Mailtrap email sending (OTP/reset emails)
│   │   ├── otp.py            # 4-digit OTP generation & validation
│   │   └── security.py       # Password hashing & JWT tokens
│   └── __init__.py
├── .env                      # Environment variables (database, email config)
├── .env.example             # Environment template
├── .gitignore               # Git ignore rules
├── database_migration.sql   # Database setup script
├── main.py                  # FastAPI application entry point
├── requirements.txt         # Python dependencies
└── BACKEND_PROJECT_STRUCTURE.md  # This documentation
```

## 🔗 Frontend-Backend Connection Map

### **Customer Authentication Flow**
```
Frontend Pages → Backend APIs → Database Tables
─────────────────────────────────────────────────
/login (signup)     → POST /api/auth/signup        → users + user_tokens
/login (OTP)        → POST /api/auth/verify-otp    → user_tokens (cleanup)
/login (signin)     → POST /api/auth/login         → users (authentication)
/forgot-password    → POST /api/auth/forgot-password → user_tokens (reset)
/forgot-password    → POST /api/auth/reset-password  → users (password update)
```

### **Admin System Flow**
```
Frontend Pages → Backend APIs → Database Tables
─────────────────────────────────────────────────
/admin              → POST /api/admin/login       → admins (authentication)
/admin/dashboard    → GET /api/admin/verify       → admins (session check)
/admin/dashboard    → GET /api/restaurant/applications → restaurant_applications
/admin/dashboard    → PUT /api/restaurant/applications/{id}/status → restaurant_applications (approve/reject)
```

### **Restaurant Partnership Flow**
```
Frontend Pages → Backend APIs → Database Tables
─────────────────────────────────────────────────
/restaurant/apply   → POST /api/restaurant/apply  → restaurant_applications (new application)
```

## 🗂️ Detailed Folder Explanations

### **1. `app/core/` - Foundation Layer**
**Purpose**: Core application configuration and database connectivity
**Frontend Connection**: 
- `config.py` → Manages all environment settings (database URL, JWT secrets, email config)
- `database.py` → Provides MySQL connection for all frontend data operations

**What it does for frontend**:
- Ensures all API calls have database connectivity
- Manages application-wide settings like JWT expiry times
- Handles database session management for all user interactions

### **2. `app/models/` - Data Layer**
**Purpose**: Database table definitions and data operations
**Frontend Connection**: Each model directly corresponds to frontend functionality

#### **`user.py` - Customer Data**
- **Frontend Pages**: `/login`, `/home`, `/cart`, `/checkout`, `/orders`
- **What it stores**: Customer accounts, login sessions, user preferences
- **Frontend Usage**: Every customer login, signup, and profile operation

#### **`user_token.py` - Temporary Data**
- **Frontend Pages**: `/login` (OTP verification), `/forgot-password`
- **What it stores**: 4-digit OTP codes, password reset tokens
- **Frontend Usage**: Email verification during signup, password reset flow

#### **`admin.py` - Admin Data**
- **Frontend Pages**: `/admin`, `/admin/dashboard`
- **What it stores**: Admin accounts, login sessions, permissions
- **Frontend Usage**: Admin authentication and session management

#### **`restaurant_application.py` - Partnership Data**
- **Frontend Pages**: `/restaurant/apply`, `/admin/dashboard`
- **What it stores**: Restaurant applications, approval status, admin notes
- **Frontend Usage**: Restaurant partnership applications and admin review process

### **3. `app/routes/` - API Layer**
**Purpose**: HTTP endpoints that frontend calls directly
**Frontend Connection**: Each route file serves specific frontend pages

#### **`auth.py` - Customer APIs**
**Serves Frontend Pages**: `/login`, `/forgot-password`
**API Endpoints**:
- `POST /signup` → Customer registration form
- `POST /verify-otp` → OTP verification step
- `POST /login` → Customer login form
- `POST /forgot-password` → Password reset request
- `POST /reset-password` → New password submission

#### **`admin_auth.py` - Admin APIs**
**Serves Frontend Pages**: `/admin`, `/admin/dashboard`
**API Endpoints**:
- `POST /login` → Admin login form
- `GET /verify` → Dashboard session validation (every minute)

#### **`restaurant.py` - Restaurant APIs**
**Serves Frontend Pages**: `/restaurant/apply`, `/admin/dashboard`
**API Endpoints**:
- `POST /apply` → Restaurant application form
- `GET /applications` → Admin dashboard application list
- `PUT /applications/{id}/status` → Admin approve/reject actions

### **4. `app/utils/` - Service Layer**
**Purpose**: Shared utilities used across all frontend operations
**Frontend Connection**: Behind-the-scenes services for frontend features

#### **`security.py` - Authentication Services**
- **Frontend Usage**: Every login, signup, and session management
- **What it provides**: Password hashing, JWT token creation/validation
- **Connected to**: All authentication forms and protected pages

#### **`email.py` - Email Services**
- **Frontend Usage**: Signup OTP, password reset, application notifications
- **What it provides**: Mailtrap email sending with HTML templates
- **Connected to**: OTP verification, password reset flow

#### **`otp.py` - Verification Services**
- **Frontend Usage**: Signup verification, password reset
- **What it provides**: 4-digit OTP generation, expiry management
- **Connected to**: Email verification steps in signup/reset flows

## 🔄 Complete User Journey Examples

### **Customer Signup Journey**
1. **Frontend**: User fills signup form at `/login`
2. **Backend**: `POST /api/auth/signup` → Creates user in `users` table
3. **Backend**: `otp.py` generates 4-digit code → Stores in `user_tokens` table
4. **Backend**: `email.py` sends OTP via Mailtrap
5. **Frontend**: User enters OTP at `/login`
6. **Backend**: `POST /api/auth/verify-otp` → Validates and activates user
7. **Backend**: Cleans up `user_tokens` table automatically
8. **Frontend**: User redirected to `/home`

### **Admin Review Journey**
1. **Frontend**: Admin logs in at `/admin`
2. **Backend**: `POST /api/admin/login` → Validates against `admins` table
3. **Frontend**: Admin accesses `/admin/dashboard`
4. **Backend**: `GET /api/restaurant/applications` → Fetches from `restaurant_applications`
5. **Frontend**: Admin clicks approve/reject
6. **Backend**: `PUT /api/restaurant/applications/{id}/status` → Updates status + admin_id
7. **Frontend**: Beautiful notification shows success
8. **Backend**: Records which admin made the decision

### **Restaurant Application Journey**
1. **Frontend**: Restaurant owner fills form at `/restaurant/apply`
2. **Backend**: `POST /api/restaurant/apply` → Creates application in `restaurant_applications`
3. **Frontend**: Success page with application confirmation
4. **Backend**: Application appears in admin dashboard
5. **Frontend**: Admin reviews and approves/rejects
6. **Backend**: Status updated with admin tracking

## 🛡️ Security Implementation

### **Authentication Flow**
- **Frontend**: Login forms collect credentials
- **Backend**: `security.py` validates passwords with bcrypt
- **Database**: Only hashed passwords stored in `users`/`admins` tables
- **Frontend**: JWT tokens stored in localStorage for session management

### **Session Management**
- **Frontend**: 10-minute admin session timer with warnings
- **Backend**: JWT tokens with configurable expiry
- **Database**: Admin login tracking in `admins.last_login`

### **Data Protection**
- **Frontend**: Input validation on all forms
- **Backend**: SQL injection protection via SQLAlchemy ORM
- **Database**: Foreign key constraints and data integrity

## 📊 Database Relationships

```sql
-- Customer System
users (1) ←→ (many) user_tokens  -- One user can have multiple temp tokens

-- Admin System  
admins (1) ←→ (many) restaurant_applications  -- One admin reviews many applications

-- Application Tracking
restaurant_applications.reviewed_by → admins.id  -- Track which admin approved
```

## 👨‍💼 Admin Management

### **Adding New Admin Accounts**
Admins are created manually in the database for security. Follow these steps:

#### **Step 1: Hash the Password**
```python
# Use Python to hash the password
from app.utils.security import hash_password
hashed_password = hash_password("your_admin_password")
print(hashed_password)
```

#### **Step 2: Insert into Database**
```sql
INSERT INTO admins (name, email, password_hash, is_active, created_at, updated_at) 
VALUES (
    'Admin Name', 
    'admin@company.com', 
    'hashed_password_from_step_1', 
    1, 
    NOW(), 
    NOW()
);
```

#### **Step 3: Test Login**
- Go to `/admin` portal
- Login with the new email and password
- Verify access to `/admin/dashboard`

### **Removing Admin Access**
```sql
-- Deactivate admin (recommended - preserves audit trail)
UPDATE admins SET is_active = 0 WHERE email = 'admin@company.com';

-- Or completely remove (not recommended)
DELETE FROM admins WHERE email = 'admin@company.com';
```

### **Current Admin Accounts**
- **latheefdinul@gmail.com** (Admin ID: 1) - Primary administrator
- Password: dinulasan1

## 🚀 Production Deployment

### **Environment Configuration**
```env
# Database (connects to MySQL for all frontend data)
DATABASE_URL=mysql+pymysql://user:pass@host:port/database

# JWT Security (for all frontend authentication)
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_DAYS=30

# Email Service (for frontend OTP/notifications)
MAIL_SERVER=smtp.mailtrap.io
MAIL_USERNAME=your-username
MAIL_PASSWORD=your-password
```

### **API Documentation**
- **Swagger UI**: http://localhost:8000/docs (Interactive API testing)
- **ReDoc**: http://localhost:8000/redoc (Clean API documentation)
- **Frontend Integration**: All endpoints documented with request/response examples

## ✅ Current Status & Frontend Integration

### **Fully Integrated Features**
- ✅ **Customer Authentication**: Complete signup/login flow with frontend
- ✅ **Admin Portal**: Secure admin login and dashboard
- ✅ **Restaurant Applications**: Full application and review system
- ✅ **Email System**: OTP and notification emails working
- ✅ **Session Management**: JWT tokens with frontend session handling
- ✅ **Database Operations**: All CRUD operations connected to frontend

### **Frontend Pages Connected**
- ✅ `/login` → `auth.py` APIs
- ✅ `/admin` → `admin_auth.py` APIs  
- ✅ `/admin/dashboard` → `restaurant.py` APIs
- ✅ `/restaurant/apply` → `restaurant.py` APIs
- ✅ `/forgot-password` → `auth.py` APIs

### **Real-time Features Working**
- ✅ **Live session validation**: Admin dashboard checks every minute
- ✅ **Automatic token cleanup**: Expired OTPs removed automatically  
- ✅ **Beautiful notifications**: Replace all alert() with UI notifications
- ✅ **Timezone handling**: UTC backend with local frontend display
- ✅ **Admin tracking**: Records which admin approved each application

---

**Last Updated**: January 28, 2026  
**Status**: Production-ready backend with complete frontend integration  
**Next Phase**: Restaurant owner dashboard and menu management system


## 🎯 Latest Updates (January 28, 2026)

### Admin System & Restaurant Applications
- ✅ **Separate Admin Table**: Created `admins` table isolated from customers
- ✅ **Admin Authentication**: Separate login system at `/api/admin/login`
- ✅ **Restaurant Applications**: Complete application system with approval workflow
- ✅ **Admin Dashboard Security**: Protected `/admin/dashboard` with proper authentication
- ✅ **Application Status Tracking**: Records which admin approved/rejected applications
- ✅ **Session Management**: 10-minute auto-logout with warnings and manual logout
- ✅ **Beautiful Notifications**: Replaced all alert() with professional UI notifications

### New API Endpoints
- `POST /api/admin/login` - Admin authentication (separate from customers)
- `POST /api/restaurant/apply` - Restaurant partnership applications
- `GET /api/restaurant/applications` - View all applications (admin only)
- `PUT /api/restaurant/applications/{id}/status` - Approve/reject applications

### Database Updates
- **admins table**: Company employees (manual creation only)
- **restaurant_applications table**: Partnership requests with full business info
- **reviewed_by tracking**: Records which admin processed each application

### Security Enhancements
- Admin accounts created manually with bcrypt hashing
- Dashboard access requires valid admin authentication
- Role-based access control (customers vs admins)
- Application approval tracking for audit purposes
- Automatic session expiry with user warnings

### Asset Cleanup (January 28, 2026)
- ✅ **Removed unused files**: auth.ts, utils.ts, README.md, SQL_QUERIES_REFERENCE.md
- ✅ **Cleaned dependencies**: Removed unused packages (clsx, tailwind-merge, @radix-ui/*)
- ✅ **Removed Python cache**: Cleaned all __pycache__ folders
- ✅ **Optimized structure**: Removed empty lib folder



Add New Admin
python admin_manager.py add "Admin Name" "email@company.com" "password123"

List All Admins
python admin_manager.py list

Change Password
python admin_manager.py change-password "email@company.com" "newpassword123"

Deactivate Admin
python admin_manager.py deactivate "email@company.com"

Activate Admin
python admin_manager.py activate "email@company.com"

Delete Admin (Permanent)
python admin_manager.py delete "email@company.com"