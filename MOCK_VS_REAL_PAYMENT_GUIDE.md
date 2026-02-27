# 🔐 Mock vs Real Payment Gateway - Complete Guide

**Project:** Food Delivery Application  
**Date:** February 27, 2026  
**Purpose:** Understand the difference between mock payment (localhost) and real payment gateway (production)

---

## 📋 Table of Contents

1. [Current System (Mock Payment)](#current-system-mock-payment)
2. [Real Payment Gateway (Razorpay)](#real-payment-gateway-razorpay)
3. [How Card Validation Works](#how-card-validation-works)
4. [Migration Guide: Mock → Razorpay](#migration-guide-mock--razorpay)
5. [Testing Guide](#testing-guide)
6. [Security Considerations](#security-considerations)

---

## 🎭 Current System (Mock Payment)

### What We Have Now:

**Purpose:** Development and testing on localhost

**How It Works:**
```
User enters card details
  ↓
Frontend validates format only (16 digits, MM/YY, 3-digit CVV)
  ↓
Backend accepts ANY card details
  ↓
Generates fake transaction ID (MOCK-UUID-123)
  ↓
Marks payment as PAID
  ↓
No real money involved
```

### What We DON'T Check:
- ❌ Is the card number real?
- ❌ Does the card have money?
- ❌ Is the card active/not expired?
- ❌ Is CVV correct?
- ❌ Does cardholder name match?
- ❌ Is card stolen/blocked?

### Mock Payment Features:
- ✅ Accepts any 16-digit number (even 1111 1111 1111 1111)
- ✅ Accepts any name, expiry, CVV
- ✅ Always succeeds (unless you manually trigger failure)
- ✅ No real money transfer
- ✅ Instant response (no bank delays)
- ✅ Free (no transaction fees)

### When to Use Mock:
- ✅ Local development
- ✅ Testing order flow
- ✅ UI/UX testing
- ✅ Demo to stakeholders
- ❌ Production/Live environment

---

## 💳 Real Payment Gateway (Razorpay)

### What Razorpay Does:

**Purpose:** Real payment processing with actual money transfer

**How It Works:**
```
User enters card details
  ↓
Razorpay SDK captures details securely
  ↓
Razorpay sends to card issuing bank
  ↓
Bank validates:
  - Card number (Luhn algorithm)
  - Card active/not expired
  - Sufficient balance
  - CVV matches
  - Cardholder verification
  - Fraud checks
  ↓
Bank sends OTP to cardholder (3D Secure)
  ↓
User enters OTP
  ↓
Bank approves/rejects
  ↓
Money deducted from card
  ↓
Razorpay sends webhook to our backend
  ↓
We verify signature and confirm order
```

### What Razorpay Checks:

#### 1. Card Validation
- ✅ **Luhn Algorithm**: Mathematical check if card number is valid
- ✅ **Card Type**: Visa, Mastercard, Amex, RuPay
- ✅ **Expiry Date**: Not expired
- ✅ **CVV**: Matches bank records
- ✅ **Card Status**: Active, not blocked

#### 2. Bank Communication
- ✅ Talks to card issuing bank (HDFC, SBI, ICICI, etc.)
- ✅ Talks to payment networks (Visa, Mastercard)
- ✅ Gets real-time approval/rejection

#### 3. Security Features
- ✅ **PCI DSS Compliance**: We never store card data
- ✅ **3D Secure (OTP)**: Two-factor authentication
- ✅ **Fraud Detection**: AI-based risk analysis
- ✅ **Encryption**: All data encrypted in transit
- ✅ **Tokenization**: Card data replaced with tokens

#### 4. Money Transfer
- ✅ Deducts money from customer's card
- ✅ Transfers to your merchant account (minus fees)
- ✅ Settlement in 2-3 business days
- ✅ Handles refunds automatically
- ✅ Manages chargebacks

---

## 🔍 How Card Validation Works

### Step-by-Step Process:

#### 1. **Luhn Algorithm Check** (Client-side)
```javascript
// Check if card number is mathematically valid
function isValidCardNumber(cardNumber) {
  const digits = cardNumber.replace(/\s/g, '');
  let sum = 0;
  let isEven = false;
  
  for (let i = digits.length - 1; i >= 0; i--) {
    let digit = parseInt(digits[i]);
    
    if (isEven) {
      digit *= 2;
      if (digit > 9) digit -= 9;
    }
    
    sum += digit;
    isEven = !isEven;
  }
  
  return sum % 10 === 0;
}

// Example:
isValidCardNumber('4532 1488 0343 6467'); // true (valid Visa)
isValidCardNumber('1111 1111 1111 1111'); // false (invalid)
```

#### 2. **Card Type Detection** (Client-side)
```javascript
function getCardType(cardNumber) {
  const cleaned = cardNumber.replace(/\s/g, '');
  
  if (/^4/.test(cleaned)) return 'Visa';
  if (/^5[1-5]/.test(cleaned)) return 'Mastercard';
  if (/^3[47]/.test(cleaned)) return 'Amex';
  if (/^6(?:011|5)/.test(cleaned)) return 'Discover';
  if (/^(?:2131|1800|35)/.test(cleaned)) return 'JCB';
  if (/^(6062|60|81)/.test(cleaned)) return 'RuPay';
  
  return 'Unknown';
}
```

#### 3. **Bank Validation** (Razorpay/Bank)
- Checks card status in bank database
- Verifies CVV matches
- Checks available balance
- Runs fraud detection algorithms
- Sends OTP for verification

#### 4. **3D Secure (OTP)** (Bank)
```
Bank sends OTP to cardholder's registered mobile
  ↓
User enters OTP
  ↓
Bank verifies OTP
  ↓
If correct: Approve transaction
If wrong: Reject transaction
```

---

## 🔄 Migration Guide: Mock → Razorpay

### Prerequisites:

1. **Razorpay Account**
   - Sign up at https://razorpay.com
   - Complete KYC verification
   - Get API credentials

2. **Business Documents**
   - PAN card
   - Business registration
   - Bank account details
   - GST certificate (if applicable)

3. **Test Mode First**
   - Use Razorpay test keys initially
   - Test with test cards
   - Switch to live keys only when ready

---

### Step 1: Install Razorpay SDK

**Frontend:**
```bash
cd food-delivery-ui
npm install razorpay
```

**Backend:**
```bash
cd food-delivery-backend
pip install razorpay
```

---

### Step 2: Update Backend Configuration

**File:** `food-delivery-backend/app/core/config.py`

```python
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Existing settings...
    
    # Razorpay Configuration
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET", "")
    RAZORPAY_WEBHOOK_SECRET: str = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
    
    # Payment Mode
    PAYMENT_MODE: str = os.getenv("PAYMENT_MODE", "mock")  # "mock" or "razorpay"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

**File:** `food-delivery-backend/.env`

```env
# Razorpay Test Keys (for testing)
RAZORPAY_KEY_ID=rzp_test_YOUR_TEST_KEY_ID
RAZORPAY_KEY_SECRET=YOUR_TEST_SECRET
RAZORPAY_WEBHOOK_SECRET=YOUR_WEBHOOK_SECRET

# Payment Mode
PAYMENT_MODE=mock  # Change to "razorpay" for production
```

---

### Step 3: Create Razorpay Service

**File:** `food-delivery-backend/app/services/razorpay_service.py`

```python
import razorpay
from app.core.config import settings

class RazorpayService:
    def __init__(self):
        self.client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
    
    def create_order(self, amount: float, order_id: int):
        """Create Razorpay order"""
        try:
            razorpay_order = self.client.order.create({
                "amount": int(amount * 100),  # Convert to paise
                "currency": "INR",
                "receipt": f"order_{order_id}",
                "payment_capture": 1  # Auto capture
            })
            return razorpay_order
        except Exception as e:
            raise Exception(f"Failed to create Razorpay order: {str(e)}")
    
    def verify_payment_signature(
        self,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str
    ):
        """Verify payment signature for security"""
        try:
            self.client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            })
            return True
        except razorpay.errors.SignatureVerificationError:
            return False
    
    def fetch_payment(self, payment_id: str):
        """Fetch payment details"""
        return self.client.payment.fetch(payment_id)
    
    def refund_payment(self, payment_id: str, amount: float = None):
        """Refund a payment"""
        data = {}
        if amount:
            data['amount'] = int(amount * 100)
        
        return self.client.payment.refund(payment_id, data)

razorpay_service = RazorpayService()
```

---

### Step 4: Update Payment Routes

**File:** `food-delivery-backend/app/routes/payment.py`

```python
from app.core.config import settings
from app.services.razorpay_service import razorpay_service

@router.post("/api/payments/create-order")
async def create_payment_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create payment order (Razorpay or Mock)"""
    
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if settings.PAYMENT_MODE == "razorpay":
        # Real Razorpay order
        razorpay_order = razorpay_service.create_order(
            amount=order.total_amount,
            order_id=order.id
        )
        
        return {
            "mode": "razorpay",
            "razorpay_key_id": settings.RAZORPAY_KEY_ID,
            "razorpay_order_id": razorpay_order['id'],
            "amount": razorpay_order['amount'],
            "currency": razorpay_order['currency'],
            "order_id": order.id
        }
    else:
        # Mock payment
        return {
            "mode": "mock",
            "order_id": order.id,
            "amount": order.total_amount
        }

@router.post("/api/payments/verify")
async def verify_payment(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify Razorpay payment"""
    
    # Verify signature
    is_valid = razorpay_service.verify_payment_signature(
        razorpay_order_id,
        razorpay_payment_id,
        razorpay_signature
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail="Invalid payment signature"
        )
    
    # Fetch payment details
    payment_details = razorpay_service.fetch_payment(razorpay_payment_id)
    
    # Update payment record
    payment = db.query(Payment).filter(Payment.order_id == order_id).first()
    payment.payment_status = PaymentStatus.PAID
    payment.transaction_reference = razorpay_payment_id
    payment.gateway_order_id = razorpay_order_id
    payment.gateway_signature = razorpay_signature
    payment.payment_completed_at = datetime.now()
    
    # Update order
    order = db.query(Order).filter(Order.id == order_id).first()
    order.status = OrderStatus.CONFIRMED
    order.payment_status = PaymentStatus.PAID
    order.confirmed_at = datetime.now()
    
    db.commit()
    
    return {
        "status": "success",
        "payment_id": razorpay_payment_id,
        "order_status": "confirmed"
    }
```

---

### Step 5: Update Frontend

**File:** `food-delivery-ui/src/app/checkout/page.tsx`

Add Razorpay script to `layout.tsx`:
```typescript
<Script src="https://checkout.razorpay.com/v1/checkout.js" />
```

Update payment processing:
```typescript
const processPayment = async (orderId: number) => {
  try {
    const token = localStorage.getItem('token');
    
    // Create payment order
    const response = await fetch('http://localhost:8000/api/payments/create-order', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ order_id: orderId })
    });
    
    const data = await response.json();
    
    if (data.mode === 'razorpay') {
      // Real Razorpay payment
      const options = {
        key: data.razorpay_key_id,
        amount: data.amount,
        currency: data.currency,
        name: "Your Restaurant Name",
        description: "Order Payment",
        order_id: data.razorpay_order_id,
        handler: async function (response: any) {
          // Payment successful, verify on backend
          await verifyPayment(
            response.razorpay_order_id,
            response.razorpay_payment_id,
            response.razorpay_signature,
            orderId
          );
          
          router.push(`/order-success?orderId=${orderId}`);
        },
        prefill: {
          name: deliveryAddress.fullName,
          email: userEmail,
          contact: deliveryAddress.phone
        },
        theme: {
          color: "#ff6b6b"
        },
        modal: {
          ondismiss: function() {
            // User closed payment modal
            setErrors({ submit: 'Payment cancelled' });
          }
        }
      };
      
      const rzp = new (window as any).Razorpay(options);
      rzp.open();
      
    } else {
      // Mock payment
      const mockResponse = await fetch('http://localhost:8000/api/payments/success', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ order_id: orderId })
      });
      
      if (mockResponse.ok) {
        router.push(`/order-success?orderId=${orderId}`);
      }
    }
    
  } catch (err) {
    setErrors({ submit: 'Payment failed. Please try again.' });
  }
};

const verifyPayment = async (
  razorpay_order_id: string,
  razorpay_payment_id: string,
  razorpay_signature: string,
  order_id: number
) => {
  const token = localStorage.getItem('token');
  
  await fetch('http://localhost:8000/api/payments/verify', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      razorpay_order_id,
      razorpay_payment_id,
      razorpay_signature,
      order_id
    })
  });
};
```

---

## 🧪 Testing Guide

### Mock Payment Testing:

**Test Cards (Always Work):**
- Any 16-digit number: `4532 1488 0343 6467`
- Any name: `JOHN DOE`
- Any expiry: `12/25`
- Any CVV: `123`

**Test Scenarios:**
1. ✅ Successful payment
2. ✅ Failed payment (manual trigger)
3. ✅ Retry after failure
4. ✅ COD flow

---

### Razorpay Test Mode:

**Test Cards (Provided by Razorpay):**

**Success:**
- Card: `4111 1111 1111 1111`
- Expiry: Any future date
- CVV: Any 3 digits
- OTP: `123456`

**Failure:**
- Card: `4000 0000 0000 0002`
- Will always fail

**Insufficient Funds:**
- Card: `4000 0000 0000 9995`

**More test cards:** https://razorpay.com/docs/payments/payments/test-card-details/

---

## 🔒 Security Considerations

### Mock Payment (Current):
- ⚠️ **NOT secure for production**
- ⚠️ No real validation
- ⚠️ Anyone can fake payments
- ✅ Safe for localhost testing

### Razorpay (Production):
- ✅ **PCI DSS Level 1 Certified**
- ✅ We never store card data
- ✅ All data encrypted (TLS 1.2+)
- ✅ 3D Secure (OTP) mandatory
- ✅ Fraud detection AI
- ✅ Webhook signature verification
- ✅ IP whitelisting available

### Best Practices:
1. ✅ Never log card details
2. ✅ Always verify webhook signatures
3. ✅ Use HTTPS in production
4. ✅ Keep API keys secret
5. ✅ Rotate keys periodically
6. ✅ Monitor for suspicious activity
7. ✅ Implement rate limiting
8. ✅ Use environment variables for keys

---

## 💰 Cost Comparison

### Mock Payment:
- **Cost:** Free
- **Transaction Fee:** ₹0
- **Setup Fee:** ₹0
- **Maintenance:** ₹0

### Razorpay:
- **Setup Fee:** ₹0
- **Transaction Fee:** 2% + GST per transaction
- **Example:** ₹1000 order = ₹20 + ₹3.60 GST = ₹23.60 fee
- **Settlement:** T+2 days (2 business days)
- **Refund Fee:** ₹0 (free)

---

## 📊 Feature Comparison

| Feature | Mock | Razorpay |
|---------|------|----------|
| Card Validation | ❌ Format only | ✅ Full validation |
| Real Money | ❌ No | ✅ Yes |
| OTP Verification | ❌ No | ✅ Yes |
| Fraud Detection | ❌ No | ✅ Yes |
| Refunds | ❌ Manual | ✅ Automatic |
| Chargebacks | ❌ N/A | ✅ Handled |
| International Cards | ❌ No | ✅ Yes |
| UPI | ❌ Fake | ✅ Real |
| Wallets | ❌ Fake | ✅ Real (Paytm, PhonePe) |
| Net Banking | ❌ No | ✅ Yes |
| EMI | ❌ No | ✅ Yes |
| Webhooks | ❌ No | ✅ Yes |
| Dashboard | ❌ No | ✅ Yes |
| Analytics | ❌ No | ✅ Yes |
| Support | ❌ No | ✅ 24/7 |

---

## 🚀 Go-Live Checklist

Before switching to Razorpay in production:

### Business Setup:
- [ ] Razorpay account created
- [ ] KYC completed
- [ ] Bank account linked
- [ ] Test mode tested thoroughly
- [ ] Live keys obtained

### Technical Setup:
- [ ] Razorpay SDK installed
- [ ] Environment variables configured
- [ ] Webhook endpoint created
- [ ] Webhook signature verification implemented
- [ ] Error handling added
- [ ] Logging configured

### Testing:
- [ ] Test cards work in test mode
- [ ] Payment success flow tested
- [ ] Payment failure flow tested
- [ ] Refund flow tested
- [ ] Webhook delivery tested
- [ ] Load testing done

### Security:
- [ ] HTTPS enabled
- [ ] API keys in environment variables
- [ ] Webhook signature verification working
- [ ] Rate limiting enabled
- [ ] Error messages don't leak sensitive data

### Compliance:
- [ ] Privacy policy updated
- [ ] Terms of service updated
- [ ] Refund policy defined
- [ ] Customer support ready

---

## 📞 Support

### Mock Payment Issues:
- Check backend logs
- Verify API endpoints
- Check browser console

### Razorpay Issues:
- **Documentation:** https://razorpay.com/docs/
- **Support:** support@razorpay.com
- **Dashboard:** https://dashboard.razorpay.com
- **Status:** https://status.razorpay.com

---

## 🎯 Summary

**Current System (Mock):**
- ✅ Perfect for development
- ✅ Free and fast
- ✅ No real validation
- ❌ Not for production

**Razorpay (Production):**
- ✅ Real payment processing
- ✅ Full card validation by banks
- ✅ Secure and compliant
- ✅ Easy to integrate
- 💰 2% + GST per transaction

**Your architecture is ready** - just change `PAYMENT_MODE` from `mock` to `razorpay` when you're ready to go live!

---

**Last Updated:** February 27, 2026  
**Version:** 1.0  
**Status:** Production Ready
