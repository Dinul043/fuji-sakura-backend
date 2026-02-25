# 💳 Payment Flow Documentation - Food Delivery App

## 📋 Table of Contents
1. [Overview](#overview)
2. [Current Payment Implementation](#current-implementation)
3. [Order Creation Flow](#order-creation-flow)
4. [Payment Methods](#payment-methods)
5. [Success & Failure Handling](#success-failure-handling)
6. [Frontend-Backend Integration](#frontend-backend-integration)
7. [Future Payment Gateway Integration](#future-integration)

---

## 🎯 Overview

### What is Payment Flow?
Payment flow is the complete journey from when a user clicks "Place Order" to when the order is confirmed and payment is processed.

### Key Components:
1. **Order Creation** - Creating order record in database
2. **Payment Initiation** - Starting payment process
3. **Payment Processing** - Handling payment (currently simulated)
4. **Success/Failure Handling** - What happens after payment
5. **Order Confirmation** - Finalizing the order

---

## 🔄 Current Payment Implementation

### Current Status: **Simulated Payment (No Real Gateway)**

Our app currently uses **simulated payment** - meaning:
- ✅ User can select payment method (Card, UPI, Wallet, COD)
- ✅ Order is created in database
- ✅ Payment is marked as "PAID" automatically
- ❌ No real money is charged
- ❌ No payment gateway (Razorpay/Stripe) integrated yet

**Why Simulated?**
- Allows testing full order flow without real payments
- No payment gateway fees during development
- Easy to test success/failure scenarios

---

## 📦 Order Creation Flow

### Step-by-Step Process:

#### 1. User Adds Items to Cart
```
User browses menu → Adds items → Cart stored in localStorage (guest) or database (logged in)
```

#### 2. User Goes to Checkout
**Frontend**: `src/app/checkout/page.tsx`
```typescript
// User fills delivery details:
- Full Name
- Phone Number
- Address
- Pincode
- Payment Method (card/upi/wallet/cod)
- Special Instructions (optional)
```

#### 3. User Clicks "Place Order"
**Frontend Code**:
```typescript
const handlePlaceOrder = async () => {
  const orderData = {
    items: cartItems,              // What user ordered
    delivery_address: address,     // Where to deliver
    delivery_phone: phone,         // Contact number
    payment_method: paymentMethod, // How they'll pay
    special_instructions: notes    // Any special requests
  };
  
  // Send to backend
  const response = await fetch('/api/orders/create', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: JSON.stringify(orderData)
  });
}
```

#### 4. Backend Creates Order
**Backend**: `app/routes/orders.py`
```python
@router.post("/create")
def create_order(request: OrderRequest, db: Session):
    # 1. Calculate totals
    subtotal = sum(item.price * item.quantity for item in items)
    delivery_fee = 50.0  # Fixed delivery fee
    tax = subtotal * 0.05  # 5% tax
    total = subtotal + delivery_fee + tax
    
    # 2. Generate unique order number
    order_number = f"ORD-{datetime.now().year}-{count:06d}"
    
    # 3. Create order in database
    order = Order(
        order_number=order_number,
        user_id=user.id,
        restaurant_id=restaurant_id,
        status=OrderStatus.PENDING,
        payment_status=PaymentStatus.PENDING,
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        tax_amount=tax,
        total_amount=total,
        delivery_address=address,
        payment_method=payment_method,
        confirmed_at=datetime.now()
    )
    db.add(order)
    
    # 4. Create order items
    for item in cart_items:
        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=item.id,
            item_name=item.name,
            item_price=item.price,
            quantity=item.quantity
        )
        db.add(order_item)
    
    db.commit()
    
    # 5. Return order details
    return {
        "order_id": order.id,
        "order_number": order.order_number,
        "total_amount": total,
        "status": "pending"
    }
```

#### 5. Payment Processing (Simulated)
```python
# Currently: Payment automatically marked as PAID
order.payment_status = PaymentStatus.PAID
order.status = OrderStatus.CONFIRMED
db.commit()

# In future with real gateway:
# - Redirect to payment gateway
# - Wait for callback
# - Update status based on payment result
```

#### 6. Order Confirmation
```
Order created → Payment marked as paid → User redirected to success page → Email sent (optional)
```

---

## 💰 Payment Methods

### 1. Credit/Debit Card (💳)
**Current**: Simulated
**Future**: Razorpay/Stripe card processing
```json
{
  "payment_method": "card",
  "card_details": {
    "number": "4111111111111111",
    "expiry": "12/25",
    "cvv": "123"
  }
}
```

### 2. UPI Payment (📱)
**Current**: Simulated
**Future**: UPI intent/QR code
```json
{
  "payment_method": "upi",
  "upi_id": "user@paytm"
}
```

### 3. Digital Wallet (👛)
**Current**: Simulated
**Future**: Paytm/PhonePe wallet integration
```json
{
  "payment_method": "wallet",
  "wallet_provider": "paytm"
}
```

### 4. Cash on Delivery (💵)
**Current**: Working (no payment needed)
**Future**: Same (no changes needed)
```json
{
  "payment_method": "cod"
}
```

---

## ✅ Success & Failure Handling

### Success Flow:

#### 1. Payment Successful
```
Payment Gateway → Success Callback → Update Order Status → Redirect User
```

**Backend Updates**:
```python
order.payment_status = PaymentStatus.PAID
order.status = OrderStatus.CONFIRMED
order.payment_reference = transaction_id
db.commit()
```

**Frontend Redirect**:
```typescript
// Redirect to success page
router.push(`/order-success?orderId=${orderId}`);
```

#### 2. Success Page Display
**Frontend**: `src/app/order-success/page.tsx`
```typescript
// Shows:
- Order number
- Total amount
- Delivery address
- Estimated delivery time
- Order items
- Payment method
```

### Failure Flow:

#### 1. Payment Failed
```
Payment Gateway → Failure Callback → Update Order Status → Show Error
```

**Backend Updates**:
```python
order.payment_status = PaymentStatus.FAILED
order.status = OrderStatus.CANCELLED
db.commit()
```

**Frontend Display**:
```typescript
// Show error message
setError("Payment failed. Please try again.");
// Keep user on checkout page
// Allow retry
```

#### 2. Timeout Scenario
```
No response from gateway → Timeout (30 seconds) → Mark as pending → Manual verification
```

---

## 🔗 Frontend-Backend Integration

### Data Flow Diagram:
```
[Frontend Checkout Page]
        ↓
    (User clicks Place Order)
        ↓
[POST /api/orders/create]
        ↓
    [Backend validates]
        ↓
    [Create order in DB]
        ↓
    [Process payment - simulated]
        ↓
    [Return order details]
        ↓
[Frontend receives response]
        ↓
[Redirect to success page]
        ↓
[GET /api/orders/{id}]
        ↓
[Display order details]
```

### Key Data Passed:

#### Frontend → Backend (Order Creation):
```typescript
{
  items: [
    {
      menu_item_id: 1,
      quantity: 2,
      price: 250.00
    }
  ],
  delivery_address: "123 Main St, Tokyo",
  delivery_phone: "+81-90-1234-5678",
  payment_method: "card",
  special_instructions: "Ring doorbell twice"
}
```

#### Backend → Frontend (Order Response):
```json
{
  "order_id": 123,
  "order_number": "ORD-2026-000123",
  "status": "confirmed",
  "payment_status": "paid",
  "total_amount": 575.00,
  "estimated_delivery_time": 30,
  "created_at": "2026-02-18T14:30:00"
}
```

---

## 🚀 Future Payment Gateway Integration

### When Real Payment Gateway is Added:

#### 1. Choose Payment Gateway
**Options**:
- **Razorpay** (India) - Most popular
- **Stripe** (Global) - International
- **PayPal** (Global) - Widely accepted
- **Paytm** (India) - UPI focused

#### 2. Integration Steps:

**Step 1: Get API Keys**
```env
RAZORPAY_KEY_ID=rzp_test_xxxxx
RAZORPAY_KEY_SECRET=xxxxx
```

**Step 2: Install SDK**
```bash
pip install razorpay
```

**Step 3: Create Payment Order**
```python
import razorpay

client = razorpay.Client(auth=(KEY_ID, KEY_SECRET))

# Create payment order
payment_order = client.order.create({
    "amount": total_amount * 100,  # Amount in paise
    "currency": "INR",
    "receipt": order_number,
    "payment_capture": 1
})

# Return to frontend
return {
    "order_id": order.id,
    "razorpay_order_id": payment_order['id'],
    "amount": total_amount,
    "currency": "INR"
}
```

**Step 4: Frontend Payment**
```typescript
// Load Razorpay script
const options = {
  key: "rzp_test_xxxxx",
  amount: amount * 100,
  currency: "INR",
  order_id: razorpay_order_id,
  handler: function(response) {
    // Payment successful
    verifyPayment(response);
  },
  modal: {
    ondismiss: function() {
      // Payment cancelled
      handlePaymentCancel();
    }
  }
};

const rzp = new Razorpay(options);
rzp.open();
```

**Step 5: Verify Payment**
```python
@router.post("/verify-payment")
def verify_payment(payment_data: PaymentVerification):
    # Verify signature
    signature = hmac.new(
        KEY_SECRET.encode(),
        f"{payment_data.order_id}|{payment_data.payment_id}".encode(),
        hashlib.sha256
    ).hexdigest()
    
    if signature == payment_data.signature:
        # Payment verified
        order.payment_status = PaymentStatus.PAID
        order.payment_reference = payment_data.payment_id
        db.commit()
        return {"status": "success"}
    else:
        # Invalid signature
        return {"status": "failed"}
```

---

## 📊 Payment Status Flow

### Order Status Progression:
```
PENDING → CONFIRMED → PREPARING → READY → OUT_FOR_DELIVERY → DELIVERED
   ↓
CANCELLED (if payment fails)
```

### Payment Status:
```
PENDING → PAID → (Order proceeds)
   ↓
FAILED → (Order cancelled)
   ↓
REFUNDED → (If order cancelled after payment)
```

---

## 🔐 Security Considerations

### 1. Never Store Card Details
```python
# ❌ NEVER DO THIS
card_number = request.card_number  # Don't store

# ✅ DO THIS
payment_reference = gateway_response.transaction_id  # Store only reference
```

### 2. Verify Payment Signatures
```python
# Always verify payment gateway callbacks
if not verify_signature(payment_data):
    raise HTTPException(status_code=400, detail="Invalid signature")
```

### 3. Use HTTPS
```
All payment APIs must use HTTPS (not HTTP)
```

### 4. Validate Amounts
```python
# Verify amount matches order
if payment_amount != order.total_amount:
    raise HTTPException(status_code=400, detail="Amount mismatch")
```

---

## 📝 Key Concepts Summary

### 1. Order ID
- **What**: Unique identifier for each order
- **Format**: `ORD-2026-000123`
- **Used for**: Tracking, reference, customer support

### 2. Transaction Status
- **PENDING**: Payment not yet processed
- **PAID**: Payment successful
- **FAILED**: Payment failed
- **REFUNDED**: Money returned to customer

### 3. Callbacks
- **What**: Payment gateway notifies our server about payment result
- **Types**: 
  - Success callback (payment successful)
  - Failure callback (payment failed)
  - Webhook (async notification)

### 4. Error Scenarios
- **Payment Declined**: Card declined by bank
- **Insufficient Funds**: Not enough money
- **Network Error**: Connection lost
- **Timeout**: Payment took too long
- **Invalid Details**: Wrong card info

---

## 🎯 Learning Checklist

- [ ] Understand order creation flow
- [ ] Know what data is passed between frontend and backend
- [ ] Understand payment status progression
- [ ] Know difference between simulated and real payment
- [ ] Understand success/failure handling
- [ ] Know basic payment gateway concepts
- [ ] Understand security considerations
- [ ] Know how callbacks work

---

## 📚 Additional Resources

### Payment Gateway Documentation:
- Razorpay: https://razorpay.com/docs/
- Stripe: https://stripe.com/docs
- PayPal: https://developer.paypal.com/

### Key Files in Our Project:
- **Backend**: `app/routes/orders.py` - Order creation
- **Backend**: `app/models/orders.py` - Order database model
- **Frontend**: `src/app/checkout/page.tsx` - Checkout page
- **Frontend**: `src/app/order-success/page.tsx` - Success page

---

**Note**: This documentation covers the current implementation (simulated payment) and explains how real payment gateway integration would work in the future.
