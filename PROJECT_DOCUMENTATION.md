# Fuji Sakura Food Delivery — Backend Documentation

## Tech Stack
- **Framework:** FastAPI (Python)
- **Database:** MySQL
- **ORM:** SQLAlchemy
- **Auth:** JWT (python-jose)
- **Payment:** Razorpay
- **Real-time:** WebSocket (FastAPI native)
- **Email:** Mailtrap (SMTP)

## Setup & Run
```bash
cd food-delivery-backend
pip install -r requirements.txt
# Configure .env (see .env.example)
uvicorn main:app --reload
```
API runs at: `http://localhost:8000`
Swagger docs: `http://localhost:8000/docs`

---

## Folder Structure
```
food-delivery-backend/
├── main.py                        # App entry point, route registration, static files
├── requirements.txt
├── .env                           # DB, JWT secret, Razorpay keys, email config
├── .env.example
├── uploads/
│   ├── menu_images/               # Restaurant menu item images
│   ├── restaurant_images/         # Restaurant banner images
│   └── profile_images/            # User profile photos
└── app/
    ├── core/
    │   ├── config.py              # Settings (DB URL, JWT, email config)
    │   └── database.py            # SQLAlchemy engine, session, Base
    ├── models/
    │   ├── user.py                # User table (customers)
    │   ├── user_token.py          # OTP / reset tokens
    │   ├── user_cart.py           # Shopping cart items
    │   ├── admin.py               # Admin accounts
    │   ├── restaurant_application.py  # Restaurant accounts + approval status
    │   ├── restaurant_menu.py     # Menu items per restaurant
    │   ├── orders.py              # Orders + OrderItems
    │   ├── payment.py             # Payment records (Razorpay)
    │   └── review.py              # Customer reviews
    ├─
─ routes/
    │   ├── auth.py                # User signup, login, OTP, profile, password
    │   ├── admin_auth.py          # Admin login, manage admins
    │   ├── restaurant.py          # Restaurant apply, login, profile, menu, stats, public APIs
    │   ├── menu.py                # Menu CRUD, image upload
    │   ├── cart.py                # Add/remove/update cart
    │   ├── orders.py              # Create order, get orders, update status
    │   ├── payment.py             # Razorpay create-order, verify, refund
    │   ├── reviews.py             # Submit review, get by restaurant/order
    │   └── websocket.py           # WebSocket endpoints
    ├── services/
    │   └── razorpay_service.py    # Razorpay API wrapper
    └── utils/
        ├── security.py            # JWT create/verify, password hash, get_current_user
        ├── email.py               # Send OTP email, password reset email
        ├── otp.py                 # Generate OTP, expiry helpers
        ├── file_cleanup.py        # Delete old uploaded images
        └── websocket_manager.py   # WebSocket connection manager
```

---

## Database Tables

| Table | Purpose |
|-------|---------|
| users | Customer accounts |
| user_tokens | OTP and password reset tokens |
| user_cart | Cart items per user |
| admins | Admin accounts |
| restaurant_applications | Restaurant accounts + approval |
| restaurant_menus | Menu items |
| orders | Customer orders |
| order_items | Items within each order |
| payments | Payment records |
| reviews | Customer reviews (1 per order) |

---

## Key API Endpoints

### Auth (User)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/signup | Register new user |
| POST | /api/auth/verify-otp | Verify email OTP |
| POST | /api/auth/login | Login |
| GET | /api/auth/me | Get profile |
| PUT | /api/auth/me | Update name/phone/address |
| PUT | /api/auth/me/change-password | Change password |
| POST | /api/auth/me/upload-image | Upload profile photo |
| POST | /api/auth/forgot-password | Send reset email |
| POST | /api/auth/reset-password | Reset password |

### Restaurant
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/restaurant/apply | Submit restaurant application |
| POST | /api/restaurant/login | Restaurant login |
| POST | /api/restaurant/logout | Restaurant logout |
| GET | /api/restaurant/profile | Get restaurant profile |
| PUT | /api/restaurant/profile | Update profile |
| GET | /api/restaurant/stats | Dashboard stats (real data) |
| GET | /api/restaurant/public/restaurants | All approved restaurants (user home) |
| GET | /api/restaurant/public/restaurants/{id} | Restaurant detail + menu |
| PUT | /api/restaurant/toggle-online-status | Go online/offline |
| POST | /api/restaurant/upload-restaurant-image | Upload banner image |

### Orders
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/orders/create | Place order |
| GET | /api/orders/ | Get user's orders |
| GET | /api/orders/{id} | Get order detail |
| GET | /api/orders/restaurant/{id} | Get restaurant's orders |
| PUT | /api/orders/{id}/status | Update order status |
| DELETE | /api/orders/{id}/cancel | Cancel order |

### Payments
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/payments/razorpay/create-order | Create Razorpay order |
| POST | /api/payments/razorpay/verify | Verify payment + confirm order |

### Reviews
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/reviews | Submit review (auth required) |
| GET | /api/reviews/order/{id} | Check if order has review |
| GET | /api/reviews/restaurant/{id} | Get all reviews for restaurant (public) |

### WebSocket
| Endpoint | Description |
|----------|-------------|
| ws://localhost:8000/ws/orders/{order_id} | User order tracking |
| ws://localhost:8000/ws/restaurant/{id} | Restaurant menu updates |
| ws://localhost:8000/ws/restaurant-dashboard/{id} | New order notifications |

---

## Completed Features
- [x] User signup with OTP email verification
- [x] User login (remember me, JWT)
- [x] User profile (name, phone, address, profile photo)
- [x] Restaurant application + admin approval
- [x] Restaurant login (multiple sessions allowed, sessionStorage)
- [x] Restaurant menu management (CRUD + image upload)
- [x] Restaurant online/offline toggle
- [x] Shopping cart (per user, per restaurant)
- [x] Order placement (COD + Razorpay online)
- [x] Razorpay payment integration + verification
- [x] Auto refund on restaurant cancellation
- [x] Real-time order notifications (WebSocket)
- [x] Order status updates (confirmed → preparing → out_for_delivery → delivered)
- [x] Customer reviews (1 per delivered order, shown publicly)
- [x] Real ratings replacing hardcoded values
- [x] Special instructions shown to restaurant
- [x] Admin panel (approve/reject restaurants, manage admins)

---

## Next Steps (Pending)
1. **Delivery Partner module**
   - DB: `delivery_partners` table, add `delivery_partner_id` to orders
   - Apply, login, dashboard, accept/complete orders
   - Entry point on login page alongside restaurant partner
2. **Mobile responsive UI** (media queries for all pages)
3. **Analytics page** (restaurant side — real data)
4. **Push/email notifications** for order status changes
5. **Admin dashboard improvements** (order overview, revenue stats)
