# Fuji Sakura Food Delivery — Sprint Documentation


---

## ✅ COMPLETED WORK

### Authentication & User Management
- User signup, login, logout with JWT tokens
- OTP-based email verification on signup
- Forgot password with 4-digit reset code (10-min expiry) via email
- Profile page — update name, phone, profile picture
- Password change from profile
- Session stored in localStorage (user), sessionStorage (restaurant, delivery partner)

### Restaurant Application & Onboarding
- Restaurant signup form — business name, owner, email, phone, address, city, area, cuisine, license, food permit
- Admin reviews and approves/rejects applications with notes
- Approval/rejection email sent to restaurant owner
- Restaurant login with JWT, tab-isolated session (sessionStorage)
- Restaurant dashboard — view profile, menu, orders

### Menu Management
- Add menu items — name, description, price, category, veg/non-veg, image upload
- Edit and delete menu items
- Image stored in `/uploads/menu_images/`
- Menu visible to users on restaurant page

### User Ordering Flow
- Browse restaurants filtered by city/area
- View menu, add to cart, update quantities
- Cart persists per user in DB
- Checkout — delivery address, landmark, city, pincode, phone
- COD and online payment (Razorpay) options
- Order number generated as `ORD-YYYY-NNNNNN` using `max(id)` to avoid duplicates
- COD orders confirmed immediately, restaurant notified via WebSocket
- Online orders stay PENDING until Razorpay payment verified, then restaurant notified
- Failed/cancelled payments — order stays PENDING, not shown to restaurant
- Cart cleared only after successful payment (online) or on COD order placement

### Payment Integration (Razorpay)
- Razorpay order created on checkout
- Payment verified server-side using signature validation
- Refund initiated automatically when restaurant cancels an online-paid order
- Test mode with Razorpay test keys

### Order Tracking (User Side)
- Real-time tracking page at `/orders/[id]`
- 5-step progress bar: Order Confirmed → Preparing → Ready for Pickup → On the Way → Delivered
- WebSocket connection (`ws/orders/{orderId}`) updates steps live without refresh
- Shows delivery info, items, price breakdown, payment method
- Review/rating system after delivery (1–5 stars + comment)

### Restaurant Order Management
- Orders page shows all non-pending orders in real-time
- New order popup notification via WebSocket
- Filter by status: All, Confirmed, Preparing, Out for Delivery, Delivered
- Action buttons per status:
  - Confirmed → Start Preparing / Cancel
  - Preparing → Ready for Pickup
  - Ready → shows "Waiting for Pickup" badge
  - Ready + partner assigned → shows "Partner On The Way · Name · Phone"
  - Out for Delivery → shows "Picked Up — Out for Delivery · Name · Phone"
  - Delivered → shows "Delivered" badge
- Cancel order with automatic Razorpay refund for online payments
- Special instructions displayed on order card
- IST timezone on all timestamps

### Delivery Partner System
- Signup form — name, email, phone, password, vehicle type/number, driving license, Aadhar, city, area, UPI ID
- City + area both mandatory
- Admin reviews application, approves/rejects with email notification
- Login with JWT (8-hour token)
- Forgot password with reset code (10-min expiry)
- Profile page — edit phone, UPI ID, city, area (city/area blocked during active delivery)
- UPI ID required before accepting orders

### Delivery Partner Dashboard
- Online/Offline toggle
- Available orders list — filtered by matching city + area with restaurant
- Shows orders with status: CONFIRMED, PREPARING, READY (unassigned only)
- Real-time WebSocket notifications for new orders and ready-for-pickup
- When another partner takes an order, it disappears from list instantly
- **Two-step delivery flow:**
  - Accept Order → status READY, partner assigned (heading to restaurant)
  - Food Picked Up → status OUT_FOR_DELIVERY (heading to customer)
  - Mark as Delivered → status DELIVERED
- Active order card shows current phase with progress steps (Accepted → Picked Up → Delivered)
- COD orders — "Mark Cash Collected" button before delivery
- Active order restored on page reload / back button via `/api/delivery/active-order`
- Earnings cards — today's earnings, total earnings, pending payout
- ₹40 fixed delivery fee per completed order

### Delivery Earnings & Payouts
- ₹40 recorded per delivery (dedup protected — no double recording)
- COD amount tracked separately from earnings
- Earnings not counted until order is DELIVERED
- Admin payout tab — shows each partner's pending payout, COD collected, net settlement
- Net settlement = pending payout − COD collected (partner owes COD back to platform)
- "Mark Paid" button — marks all pending earnings as paid, records amount + UPI

### Admin Dashboard
- Secure login with JWT, token verified on every load
- Super admin can add/deactivate/reactivate other admins
- Stats cards — total applications, pending, approved restaurants, delivery partners
- **Restaurants tab** — filter by status, view details modal, approve/reject with notes
- **Delivery Partners tab** — filter all/pending/approved/rejected, review modal with license/Aadhar, approve/reject
- **Payouts tab** — all approved partners, pending payout, COD, net settlement, Mark Paid
- **Live Orders tab** — all active orders (confirmed → out_for_delivery) with partner info
- All tabs inside consistent `maxWidth: 1200px` container — same card structure
- WebSocket notification when new delivery partner applies

### Real-time WebSocket Architecture
- `ws/orders/{orderId}` — user order tracking
- `ws/restaurant-dashboard/{restaurantId}` — restaurant new orders + status updates
- `ws/restaurant-dashboard/0` — delivery partner broadcast channel
- `send_restaurant_notification()` — wraps as `{event: new_order}` for new orders
- `send_restaurant_status_update()` — sends status updates directly (no wrapping)
- `broadcast_to_delivery_partners()` — broadcasts to channel 0
- Heartbeat ping/pong every 30 seconds, auto-reconnect on disconnect

### Infrastructure & Config
- MySQL with IST timezone set on every DB connection (`SET time_zone = '+05:30'`)
- All timestamps stored and displayed in IST
- File uploads — menu images, restaurant images, profile pictures
- Unused file cleanup utility
- CORS configured for frontend origin
- Environment variables for DB, JWT, Razorpay, SMTP

---

## 🔴 PENDING / NOT YET DONE

### User-Facing
- No push notifications (browser/mobile) — only in-app WebSocket
- No order cancellation by user after restaurant starts preparing
- No re-order feature from order history
- No address book — user re-enters address every order
- No estimated delivery time update in real-time (static 30 mins)
- No delivery partner live location tracking on map

### Restaurant-Facing
- No restaurant-side analytics (revenue, popular items, peak hours)
- No ability to mark items as out-of-stock temporarily
- No opening/closing hours — restaurant always shown as available
- No restaurant profile edit after approval (requires admin)

### Delivery Partner
- No earnings history pagination (shows last 10 only)
- No in-app chat between partner and customer
- No route/map navigation integration
- Partner can only handle one order at a time (by design, but not enforced if DB is edited directly)

### Admin
- No bulk actions (approve all pending, export data)
- No revenue/commission analytics dashboard
- No order dispute/refund management UI (refunds happen automatically, no manual override UI)
- Live orders tab not auto-refreshing via WebSocket (manual refresh button only)

### Technical / Infrastructure
- No rate limiting on API endpoints (brute force risk on login)
- No email queue — emails sent synchronously (can slow down API on SMTP failure)
- Razorpay in test mode only — production keys not configured
- No automated tests (unit/integration)
- No Docker/deployment config
- File uploads stored locally — not on cloud storage (S3/Cloudinary)
- No pagination on restaurant orders list (loads all orders)
- WebSocket connections not authenticated — any client can connect to any channel

---

## ⚠️ KNOWN RISKS & POTENTIAL ISSUES

### Race Conditions
- **Two partners accepting same order simultaneously** — handled with `delivery_partner_id IS NULL` check + DB commit, but under high load a race window exists. Fix: add DB-level row locking (`SELECT FOR UPDATE`).
- **Duplicate order numbers** — fixed using `max(id)` but if two orders are created in the same millisecond, collision is still theoretically possible. Fix: use DB auto-increment as order number suffix.

### WebSocket
- **Delivery partner on channel 0** — all delivery partners share one broadcast channel regardless of city/area. A partner in Chennai will get notified about an order in Mumbai. The frontend filters on refresh, but the toast notification fires for everyone. Fix: use city+area as the channel key.
- **No WebSocket auth** — anyone who knows the channel URL can connect and receive order data. Fix: pass JWT as query param and validate on connect.
- **Memory leak on server restart** — all WebSocket connections drop and clients must reconnect. Auto-reconnect is implemented on frontend (3-second retry).

### Payments
- **Razorpay test cards only** — international cards blocked, UPI scanner only works with real UPI apps. In production, switch to live keys.
- **Refund failure silent** — if Razorpay refund fails, order is still cancelled but customer may not get money back. Fix: add a refund_status field and admin alert.
- **Payment verification replay** — the verify endpoint doesn't check if a payment_id was already used. Fix: store payment_id and reject duplicates.

### Data Integrity
- **Order items not re-validated at checkout** — price is taken from cart which was set when item was added. If restaurant changes price after item is in cart, old price is used. Fix: re-fetch price from menu at order creation.
- **Delivery partner earnings on manual DB edit** — if order status is changed directly in DB to DELIVERED without going through the API, earnings are not recorded.

### Security
- **No rate limiting** — login endpoints can be brute-forced. Fix: add slowapi or similar.
- **Admin notes visible in API response** — delivery partner's admin_notes are returned in the partner profile API. Fix: exclude from partner-facing endpoints.
- **File upload no virus scan** — uploaded images are stored as-is. Fix: validate MIME type server-side, add size limit.

### UX Edge Cases
- **Partner goes offline mid-delivery** — no enforcement. Partner can toggle offline while carrying an order. Fix: block offline toggle when active order exists.
- **Restaurant marks order Ready before food is actually ready** — no validation, purely trust-based.
- **User closes browser during Razorpay payment** — order stays PENDING forever. Fix: add a cron job to expire PENDING orders older than 30 minutes.

---

## 📁 KEY FILE LOCATIONS

| Area | File |
|------|------|
| Backend entry | `food-delivery-backend/main.py` |
| DB config | `food-delivery-backend/app/core/database.py` |
| Order routes | `food-delivery-backend/app/routes/orders.py` |
| Delivery routes | `food-delivery-backend/app/routes/delivery.py` |
| Payment routes | `food-delivery-backend/app/routes/payment.py` |
| Restaurant routes | `food-delivery-backend/app/routes/restaurant.py` |
| Admin routes | `food-delivery-backend/app/routes/admin_auth.py` |
| WebSocket manager | `food-delivery-backend/app/utils/websocket_manager.py` |
| User tracking page | `food-delivery-ui/src/app/orders/[id]/page.tsx` |
| Delivery dashboard | `food-delivery-ui/src/app/delivery/dashboard/page.tsx` |
| Restaurant orders | `food-delivery-ui/src/app/restaurant/orders/page.tsx` |
| Admin dashboard | `food-delivery-ui/src/app/admin/dashboard/page.tsx` |
