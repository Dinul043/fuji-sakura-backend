# Fuji Sakura Food Delivery - Backend Project Structure

## 🏗️ Project Architecture

This FastAPI backend serves the Fuji Sakura food delivery platform with separate authentication systems for customers, restaurant owners, and administrators.

## 📁 Directory Structure

```
food-delivery-backend/
├── app/
│   ├── core/
│   │   ├── config.py          # Application configuration and settings
│   │   ├── database.py        # Database connection and session management
│   │   └── __init__.py
│   ├── models/
│   │   ├── admin.py           # Admin user model with authentication
│   │   ├── restaurant_application.py  # Restaurant applications and session management
│   │   ├── user.py            # Customer user model
│   │   ├── user_token.py      # Customer OTP and reset tokens
│   │   └── __init__.py
│   ├── routes/
│   │   ├── admin_auth.py      # Admin authentication and management APIs
│   │   ├── auth.py            # Customer authentication APIs
│   │   ├── restaurant.py      # Restaurant application and profile APIs
│   │   └── __init__.py
│   ├── utils/
│   │   ├── email.py           # Email service with Mailtrap integration
│   │   ├── otp.py             # OTP generation and validation
│   │   ├── security.py        # Password hashing and JWT tokens
│   │   └── __init__.py
│   └── __init__.py
├── admin_manager.py           # CLI tool for admin management
├── main.py                    # FastAPI application entry point
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (not in git)
├── .env.example              # Environment template
└── .gitignore
```

## 🔗 Frontend Integration Points

### **Customer Authentication System**
- **Login/Signup**: `/api/auth/signup`, `/api/auth/login`
- **OTP Verification**: `/api/auth/verify-otp`
- **Password Reset**: `/api/auth/forgot-password`, `/api/auth/reset-password`
- **Frontend Pages**: `food-delivery-ui/src/app/login/page.tsx`

### **Restaurant Management System**
- **Application Submission**: `/api/restaurant/apply`
- **Restaurant Login**: `/api/restaurant/login` (with single session management)
- **Profile Management**: `/api/restaurant/profile` (GET/PUT)
- **Session Management**: `/api/restaurant/logout`
- **Frontend Pages**: 
  - Application: `food-delivery-ui/src/app/restaurant/apply/page.tsx`
  - Login: `food-delivery-ui/src/app/restaurant/login/page.tsx`
  - Dashboard: `food-delivery-ui/src/app/restaurant/dashboard/page.tsx`
  - Profile: `food-delivery-ui/src/app/restaurant/profile/page.tsx`

### **Admin Management System**
- **Admin Authentication**: `/api/admin/login`, `/api/admin/verify`
- **Application Review**: `/api/restaurant/applications`, `/api/restaurant/applications/{id}/status`
- **Admin Management**: `/api/admin/create-admin`, `/api/admin/list-admins`, `/api/admin/deactivate-admin/{id}`
- **Frontend Pages**: 
  - Login: `food-delivery-ui/src/app/admin/page.tsx`
  - Dashboard: `food-delivery-ui/src/app/admin/dashboard/page.tsx`

## 🔐 Security Features

### **Session Management**
- **Single Session Control**: Only one active session per restaurant account
- **Session Validation**: Real-time session verification with database checks
- **Auto-Logout**: 8-hour session expiry for restaurants, 10-minute for admins
- **Token Tracking**: Active session tokens stored in database

### **Authentication Layers**
- **JWT Tokens**: Secure token-based authentication
- **Password Hashing**: bcrypt with salt for all user types
- **Role-Based Access**: Separate authentication for customers, restaurants, admins
- **Session Conflicts**: Prevents multiple simultaneous logins

## 📧 Email Integration

### **Mailtrap Configuration**
- **Service**: Mailtrap SMTP for development
- **Templates**: Custom HTML email templates with Fuji Sakura branding
- **Use Cases**: 
  - Customer OTP verification
  - Password reset codes
  - Restaurant approval/rejection notifications

### **Email Types**
- **Customer**: OTP codes, password reset links
- **Restaurant**: Application status updates (approval/rejection)
- **Admin**: System notifications (future enhancement)

## 🗄️ Database Schema

### **Core Tables**
- **users**: Customer accounts with verification status
- **user_tokens**: Temporary tokens for OTP and password reset
- **restaurant_applications**: Restaurant partnership applications with session management
- **admins**: Admin accounts with role hierarchy

### **Key Relationships**
- `user_tokens.user_id` → `users.id`
- `restaurant_applications.reviewed_by` → `admins.id`
- Session tokens linked to restaurant applications for single-session control

## 🚀 Deployment Configuration

### **Environment Variables**
```env
# Database
DATABASE_URL=mysql+pymysql://user:password@localhost/fuji_sakura

# JWT Security
SECRET_KEY=your-secret-key
ALGORITHM=HS256

# Email Service (Mailtrap)
MAIL_USERNAME=your-mailtrap-username
MAIL_PASSWORD=your-mailtrap-password
MAIL_FROM=noreply@fujisakura.com
MAIL_PORT=2525
MAIL_SERVER=sandbox.smtp.mailtrap.io
```

### **Production Considerations**
- Replace Mailtrap with production email service (SendGrid, AWS SES)
- Use environment-specific database URLs
- Implement proper logging and monitoring
- Add rate limiting for authentication endpoints
- Configure CORS for production domains

## 🔄 API Workflow Examples

### **Restaurant Onboarding Flow**
1. Restaurant submits application → `POST /api/restaurant/apply`
2. Admin reviews application → `GET /api/restaurant/applications`
3. Admin approves/rejects → `PUT /api/restaurant/applications/{id}/status`
4. Restaurant receives email notification
5. Approved restaurant can login → `POST /api/restaurant/login`
6. Restaurant manages profile → `GET/PUT /api/restaurant/profile`

### **Customer Registration Flow**
1. Customer enters email → `POST /api/auth/signup`
2. OTP sent to email → Mailtrap delivery
3. Customer verifies OTP → `POST /api/auth/verify-otp`
4. Customer completes profile → Account created
5. Customer can login → `POST /api/auth/login`

### **Admin Management Flow**
1. Super admin creates new admin → `POST /api/admin/create-admin`
2. New admin can login → `POST /api/admin/login`
3. Admin session monitored → `GET /api/admin/verify`
4. Super admin can deactivate → `PUT /api/admin/deactivate-admin/{id}`

## 📈 Next Development Phases

### **Phase 1: Menu Management** (In Progress)
- Restaurant menu CRUD operations
- Menu item categories and pricing
- Image upload for food items
- Menu availability toggles

### **Phase 2: Order Management**
- Customer order placement
- Restaurant order processing
- Order status tracking
- Real-time notifications

### **Phase 3: Customer Integration**
- Real restaurant data on customer home page
- Restaurant detail pages with real menus
- Shopping cart with actual pricing
- Order history and tracking

### **Phase 4: Advanced Features**
- Payment integration
- Delivery tracking
- Rating and review system
- Analytics and reportingpython admin_manager.py delete "email@company.com"

