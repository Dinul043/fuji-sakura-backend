# Payment System Documentation
## Fuji Sakura Food Delivery - Complete Payment Integration Guide

---

## Overview

The payment system supports two payment methods:
1. **Cash on Delivery (COD)** - Immediate order confirmation
2. **Online Payment (Razorpay)** - Card, UPI, Wallets, Netbanking

---

## Architecture

### Payment Flow

```
User Checkout
    ↓
Select Payment Method (COD / Online)
    ↓
Click "Place Order"
    ↓
Backend Creates Order (status=PENDING for online, CONFIRMED for COD)
    ↓
    ├─→ COD: Cart cleared → Order confirmed → Success page
    │
    └─→ Online Payment:
            ↓
        Create Razorpay Order
            ↓
        Open Razorpay Popup
            ↓
        User Completes Payment
            ↓
        Verify Payment Signature
            ↓
        Update Order (status=CONFIRMED)
            ↓
        Clear Cart → Success page
```

### Database Schema

**Orders Table:**
- `payment_method`: ENUM('online', 'cod')
- `status`: ENUM('PENDING', 'CONFIRMED', 'PREPARING', 'OUT_FOR_DELIVERY', 'DELIVERED', 'CANCELLED')
- `payment_status`: ENUM('PENDING', 'PAID', 'FAILED', 'REFUNDED')

**Payments Table:**
- `payment_method`: ENUM('ONLINE', 'COD')
- `payment_status`: ENUM('pending', 'paid', 'failed', 'refunded')
- `gateway_order_id`: Razorpay order ID
- `gateway_payment_id`: Razorpay payment ID
- `gateway_signature`: Payment verification signature
- `failure_reason`: Reason for payment failure
- `retry_count`: Number of retry attempts

---

## Backend Implementation

### 1. Configuration (.env)

```env
# Razorpay Configuration (Test Mode)
RAZORPAY_KEY_ID=rzp_test_SMcqmPYL8fapIy
RAZORPAY_KEY_SECRET=dINCmlb236eDzfwLvRdCNDhj
PAYMENT_MODE=razorpay
```

### 2. Razorpay Service (`app/services/razorpay_service.py`)

**Methods:**
- `create_order(amount, order_id)` - Creates Razorpay order
- `verify_payment_signature()` - Verifies payment authenticity
- `fetch_payment()` - Gets payment details
- `refund_payment()` - Processes refunds

### 3. API Endpoints (`app/routes/payment.py`)

**POST /api/payments/razorpay/create-order**
- Creates Razorpay order for payment
- Returns: razorpay_order_id, key_id, amount

**POST /api/payments/razorpay/verify**
- Verifies payment signature
- Updates order status to CONFIRMED
- Clears user's cart
- Returns: success, order details

**POST /api/payments/failure**
- Records payment failure
- Updates failure_reason and retry_count
- Keeps cart items for retry

### 4. Order Creation (`app/routes/orders.py`)

**POST /api/orders/create**
- Creates order with payment_method
- For COD: Clears cart immediately
- For Online: Keeps cart until payment verified

**GET /api/orders/**
- Returns only CONFIRMED orders (excludes PENDING)
- Pending orders don't show until payment succeeds

---

## Frontend Implementation

### 1. Razorpay Script (`src/app/layout.tsx`)

```tsx
<script src="https://checkout.razorpay.com/v1/checkout.js" async></script>
```

### 2. Checkout Flow (`src/app/checkout/page.tsx`)

**Payment Options:**
- Cash on Delivery (COD)
- Pay Online (Razorpay)

**Functions:**
- `handlePlaceOrder()` - Creates order
- `openRazorpay()` - Opens Razorpay popup
- `verifyPayment()` - Verifies payment with backend
- `handlePaymentFailure()` - Records failure

**Cart Management:**
- COD: Cart cleared immediately
- Online: Cart cleared only after successful payment
- Failed payment: Cart items remain

---

## Testing

### Test Mode (Current Setup)

**Razorpay Test Keys:**
- Key ID: `rzp_test_SMcqmPYL8fapIy`
- Key Secret: `dINCmlb236eDzfwLvRdCNDhj`

**Test Payment Methods:**

1. **UPI (Recommended):**
   - UPI ID: `success@razorpay`
   - Result: Instant success

2. **Cards:**
   - Enable international cards in Razorpay Dashboard
   - Card: 4111 1111 1111 1111
   - Expiry: Any future date
   - CVV: Any 3 digits

3. **Netbanking:**
   - Select any bank
   - Result: Simulated success

4. **Wallets:**
   - Select any wallet
   - Result: Simulated success

### Test Scenarios

**Scenario 1: COD Order**
1. Add items to cart
2. Go to checkout
3. Select "Cash on Delivery"
4. Click "Place Order"
5. ✅ Order confirmed immediately
6. ✅ Cart cleared
7. ✅ Redirected to success page

**Scenario 2: Successful Online Payment**
1. Add items to cart
2. Go to checkout
3. Select "Pay Online"
4. Click "Place Order"
5. Razorpay popup opens
6. Complete payment (use `success@razorpay` for UPI)
7. ✅ Payment verified
8. ✅ Cart cleared
9. ✅ Order confirmed
10. ✅ Redirected to success page

**Scenario 3: Failed/Cancelled Payment**
1. Add items to cart
2. Go to checkout
3. Select "Pay Online"
4. Click "Place Order"
5. Razorpay popup opens
6. Close popup without paying
7. ✅ Cart items remain
8. ✅ Order NOT shown in orders page
9. ✅ Failure recorded in database
10. ✅ User can retry

---

## Production Deployment

### 1. Get Live Razorpay Keys

1. Complete KYC verification in Razorpay Dashboard
2. Go to Settings → API Keys
3. Generate Live Keys
4. Update `.env`:

```env
RAZORPAY_KEY_ID=rzp_live_XXXXXXXXXX
RAZORPAY_KEY_SECRET=XXXXXXXXXXXXXXXXXX
PAYMENT_MODE=razorpay
```

### 2. Enable Payment Methods

In Razorpay Dashboard:
- Settings → Configuration → Payment Methods
- Enable: Cards, UPI, Wallets, Netbanking
- Configure international cards if needed

### 3. Webhook Setup (Optional)

For payment status updates:
1. Go to Settings → Webhooks
2. Add webhook URL: `https://yourdomain.com/api/payments/webhook`
3. Select events: payment.captured, payment.failed

---

## Security

### Payment Verification

- All payments verified using HMAC SHA256 signature
- Signature = HMAC(order_id|payment_id, secret_key)
- Backend validates signature before confirming order

### Data Protection

- Razorpay keys stored in environment variables
- Never expose secret key to frontend
- Only key_id sent to frontend

### Cart Protection

- Cart items not deleted until payment verified
- Failed payments keep items in cart
- Retry mechanism with failure tracking

---

## Troubleshooting

### Issue: "International cards not supported"
**Solution:** Enable international cards in Razorpay Dashboard → Settings → Payment Methods

### Issue: Payment succeeds but order not confirmed
**Solution:** Check backend logs for signature verification errors

### Issue: Cart cleared but payment failed
**Solution:** This shouldn't happen - cart only cleared after verification. Check backend logs.

### Issue: Pending orders showing in orders page
**Solution:** Orders endpoint filters out PENDING status - check filter logic

---

## File Structure

```
food-delivery-backend/
├── app/
│   ├── services/
│   │   └── razorpay_service.py      # Razorpay integration
│   ├── routes/
│   │   ├── payment.py                # Payment endpoints
│   │   └── orders.py                 # Order endpoints
│   └── models/
│       ├── payment.py                # Payment model
│       └── orders.py                 # Order model
├── .env                              # Configuration
├── requirements.txt                  # Dependencies
└── main.py                           # App entry point
```

---

## Dependencies

```txt
razorpay==2.0.0
fastapi
sqlalchemy
pymysql
```

---

## Support

For issues or questions:
1. Check Razorpay Dashboard logs
2. Check backend terminal logs
3. Review this documentation
4. Contact Razorpay support for payment gateway issues

---

**Last Updated:** March 3, 2026
**Version:** 1.0
**Status:** Production Ready
