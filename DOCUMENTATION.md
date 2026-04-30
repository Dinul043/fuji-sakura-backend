# Fuji Sakura Food Delivery — Project Documentation

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15 (App Router), TypeScript, inline styles |
| Backend | FastAPI (Python), SQLAlchemy ORM |
| Database | MySQL |
| Payments | Razorpay |
| Real-time | WebSocket (FastAPI + custom manager) |
| Auth | JWT tokens |

---

## Running the Project

**Backend**
```
cd food-delivery-backend
python main.py
```
Runs on `http://localhost:8000`

**Frontend**
```
cd food-delivery-ui
npm run dev
```
Runs on `http://localhost:3000`

---

## Folder Structure

### Backend — `food-delivery-backend/`

```
food-delivery-backend/
├── main.py                        # App entry point, route registration
├── requirements.txt
├── .env                           # DB credentials, Razorpay keys, JWT secret
├── uploads/
│   ├── menu_images/
│   ├── profile_images/
│   └── restaurant_images/
└── app/
    ├── core/
    │   ├── config.py              # Settings from .env
    │   └── database.py            # SQLAlchemy engine + session
    ├── models/
    │   ├── user.py                # User, OTP
    │   ├── user_token.py          # User reset tokens
    │   ├── admin.py               # Admin accounts
    │   ├── admin_token.py         # Admin reset tokens
    │   ├── restaurant_application.py  # Restaurant profile + commission_rate
    │   ├── restaurant_menu.py     # Menu items
    │   ├── restaurant_token.py    # Restaurant reset tokens
    │   ├── restaurant_payout.py   # Per-order payout records
    │   ├── orders.py              # Orders + OrderItems
    │   ├── payment.py             # Payment records
    │   ├── delivery_partner.py    # DeliveryPartner, DeliveryToken, DeliveryEarning
    │   ├── cod_settlement.py      # COD settlement via Razorpay
    │   └── review.py              # Customer reviews
    ├── routes/
    │   ├── auth.py                # User signup/login/OTP/forgot password
    │   ├── restaurant.py          # Restaurant profile, stats, earnings
    │   ├── menu.py                # Menu CRUD + image upload
    │   ├── cart.py                # Cart management
    │   ├── orders.py              # Order creation, status updates
    │   ├── payment.py             # Razorpay payment flow
    │   ├── reviews.py             # Submit + fetch reviews
    │   ├── delivery.py            # Delivery partner flow (apply, login, orders, earnings, COD)
    │   ├── admin_auth.py          # Admin login, restaurant/delivery approvals, payouts
    │   └── websocket.py           # WebSocket endpoints
    ├── services/
    │   └── razorpay_service.py    # Razorpay API wrapper
    └── utils/
        ├── security.py            # JWT, password hashing
        ├── email.py               # Email sending (OTP, reset, notifications)
        ├── otp.py                 # OTP generation + expiry
        ├── file_cleanup.py        # Old image cleanup
        └── websocket_manager.py   # WebSocket connection manager
```

### Frontend — `food-delivery-ui/`

```
food-delivery-ui/
├── src/
│   ├── app/
│   │   ├── page.tsx               # Splash screen → redirects to /login
│   │   ├── login/                 # User auth (signup, login, OTP, forgot password)
│   │   ├── home/                  # Restaurant listing, search, categories
│   │   ├── restaurant/[id]/       # Restaurant detail + menu
│   │   ├── cart/                  # Cart management
│   │   ├── checkout/              # Order placement + payment
│   │   ├── order-success/         # Post-order confirmation
│   │   ├── orders/                # Order history list
│   │   ├── orders/[id]/           # Real-time order tracking + review
│   │   ├── profile/               # User profile
│   │   ├── restaurant/
│   │   │   ├── apply/             # Restaurant application form
│   │   │   ├── login/             # Restaurant login
│   │   │   ├── dashboard/         # Stats, quick actions, WebSocket new orders
│   │   │   ├── orders/            # Incoming orders management
│   │   │   ├── menu/              # Menu CRUD
│   │   │   ├── profile/           # Restaurant profile + UPI ID
│   │   │   ├── earnings/          # Payout history
│   │   │   └── reviews/           # Customer reviews
│   │   ├── delivery/
│   │   │   ├── page.tsx           # Delivery partner landing/portal
│   │   │   ├── apply/             # Application form
│   │   │   ├── login/             # Login + forgot password
│   │   │   ├── dashboard/         # Available orders, active delivery, earnings summary
│   │   │   ├── earnings/          # Full earnings history
│   │   │   ├── profile/           # Profile + UPI ID
│   │   │   └── settle/            # COD settlement via Razorpay
│   │   └── admin/
│   │       ├── page.tsx           # Admin login
│   │       ├── dashboard/         # Applications, delivery partners, live orders
│   │       ├── payouts/restaurant/ # Restaurant payout management
│   │       └── payouts/delivery/  # Delivery partner payout management
│   └── hooks/
│       └── useWebSocket.ts        # Reusable WebSocket hook with auto-reconnect
```

---

## User Flows

### Customer
1. Splash → Login/Signup (email OTP verification)
2. Browse restaurants by city/area, search, filter by category
3. View restaurant menu → Add to cart
4. Checkout → Enter delivery address → Choose payment (Online / COD)
5. Real-time order tracking at `/orders/[id]` — live status via WebSocket
6. Cancel within 1 minute of placing (online orders auto-refunded)
7. Submit review after delivery

### Restaurant
1. Apply with business details → Admin approves
2. Login → Dashboard (today's orders, revenue, rating)
3. Receive new orders via WebSocket notification
4. Update order status: Confirmed → Preparing → Ready for Pickup
5. View earnings and payout history
6. Manage menu items (add/edit/delete/toggle availability)

### Delivery Partner
1. Apply with vehicle + documents → Admin approves
2. Login → Toggle Online
3. See available orders filtered by city/area
4. Accept order → Head to restaurant → Mark Food Picked Up → Mark Delivered
5. COD orders: must mark cash collected before marking delivered
6. Settle COD via Razorpay when net due reaches limit
7. View earnings breakdown

### Admin
1. Login (super admin can create/manage other admins)
2. Review restaurant applications → Approve with commission rate / Reject
3. Review delivery partner applications → Approve / Reject
4. Restaurant Payouts: view pending payouts, mark paid with UTR/notes
5. Delivery Partner Payouts: 4-column breakdown (earnings / COD collected / platform received / still pending)
6. COD Settlement history: view all settlements, initiate refunds if needed
7. Live Orders: real-time view of all active orders

---

## Key Business Logic

### Commission
- Each restaurant has a `commission_rate` (default 10%)
- On every delivered order: `commission = subtotal × rate / 100`
- `payout_amount = subtotal - commission`
- Admin marks payout as paid via UPI with UTR reference

### COD Settlement
- Delivery partner collects cash from customer
- Net COD due = total COD collected − delivery earnings (₹40/order)
- Partner must settle via Razorpay when net due ≥ ₹1500
- Admin can view settlement history and initiate refunds

### Delivery Earnings
- Fixed ₹40 per delivered order
- Pending until admin marks as paid via UPI

### Order Cancellation
- User can cancel within 1 minute of placing
- Online payments are auto-refunded via Razorpay
- Restaurant can cancel confirmed/preparing orders (refund initiated)

---

## WebSocket Channels

| Channel | Used By | Events |
|---------|---------|--------|
| `/ws/orders/{order_id}` | Customer tracking page | `order_status_update` |
| `/ws/restaurant-dashboard/{restaurant_id}` | Restaurant orders page | `new_order`, `order_status_update` |
| `/ws/restaurant-dashboard/0` | Delivery partner dashboard | `order_ready_for_pickup`, `order_taken`, `order_cancelled` |
| `/ws/admin` | Admin dashboard | `new_delivery_application`, `cod_settlement_paid` |

---

## Environment Variables

### Backend `.env`
```
DB_HOST=localhost
DB_PORT=3306
DB_NAME=fuji_sakura_db
DB_USER=root
DB_PASSWORD=your_password
SECRET_KEY=your_jwt_secret
RAZORPAY_KEY_ID=rzp_test_xxx
RAZORPAY_KEY_SECRET=xxx
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=your_email
EMAIL_PASSWORD=your_app_password
```

### Frontend `.env.local`
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_RAZORPAY_KEY_ID=rzp_test_xxx
```

---

## Pending / Phase 2

- [ ] User saved address book (multiple delivery addresses)
- [ ] Favourite restaurants
- [ ] Promo codes / discount system
- [ ] Restaurant tax configuration (restaurant sets their own tax %)
- [ ] Delivery partner GPS tracking on map
- [ ] Push notifications (mobile)
- [ ] Order history export
- [ ] Review moderation by admin
- [ ] Restaurant response to reviews
- [ ] Pagination on order/review lists
- [ ] Multi-language support
