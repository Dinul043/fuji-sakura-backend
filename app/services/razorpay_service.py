"""
Razorpay Payment Service
Handles all Razorpay payment operations
"""
import razorpay
from app.core.config import settings
import hmac
import hashlib

class RazorpayService:
    def __init__(self):
        """Initialize Razorpay client with API keys"""
        print(f"Initializing Razorpay with Key ID: {settings.RAZORPAY_KEY_ID[:10]}...")
        self.client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
        self.client.set_app_details({
            "title": "Fuji Sakura Food Delivery",
            "version": "1.0"
        })
        print("Razorpay client initialized successfully")
    
    def create_order(self, amount: float, order_id: int, currency: str = "INR"):
        """
        Create a Razorpay order
        
        Args:
            amount: Order amount in rupees (will be converted to paise)
            order_id: Our internal order ID
            currency: Currency code (default: INR)
            
        Returns:
            dict: Razorpay order details
        """
        try:
            # Convert amount to paise (smallest currency unit)
            amount_in_paise = int(amount * 100)
            
            print(f"📝 Creating Razorpay order:")
            print(f"   Amount: ₹{amount} ({amount_in_paise} paise)")
            print(f"   Order ID: {order_id}")
            print(f"   Currency: {currency}")
            
            # Create order in Razorpay
            razorpay_order = self.client.order.create({
                "amount": amount_in_paise,
                "currency": currency,
                "receipt": f"order_{order_id}",
                "payment_capture": 1  # Auto capture payment
            })
            
            print(f"✅ Razorpay order created: {razorpay_order['id']}")
            
            return {
                "success": True,
                "razorpay_order_id": razorpay_order["id"],
                "amount": razorpay_order["amount"],
                "currency": razorpay_order["currency"],
                "receipt": razorpay_order["receipt"]
            }
        except Exception as e:
            print(f"❌ Razorpay order creation failed: {str(e)}")
            import traceback
            print(f"❌ Full traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def verify_payment_signature(
        self,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str
    ) -> bool:
        """
        Verify payment signature for security
        This ensures the payment callback is genuine from Razorpay
        
        Args:
            razorpay_order_id: Razorpay order ID
            razorpay_payment_id: Razorpay payment ID
            razorpay_signature: Signature from Razorpay
            
        Returns:
            bool: True if signature is valid, False otherwise
        """
        try:
            print(f"🔐 Verifying payment signature:")
            print(f"   Order ID: {razorpay_order_id}")
            print(f"   Payment ID: {razorpay_payment_id}")
            print(f"   Signature: {razorpay_signature[:20]}...")
            
            # Create signature string
            message = f"{razorpay_order_id}|{razorpay_payment_id}"
            
            # Generate expected signature
            expected_signature = hmac.new(
                settings.RAZORPAY_KEY_SECRET.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            print(f"   Expected: {expected_signature[:20]}...")
            
            # Compare signatures
            is_valid = hmac.compare_digest(expected_signature, razorpay_signature)
            
            if is_valid:
                print(f"✅ Signature verification successful!")
            else:
                print(f"❌ Signature verification failed!")
                print(f"   Message: {message}")
            
            return is_valid
        except Exception as e:
            print(f"❌ Signature verification error: {e}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            return False
            
            # Generate expected signature
            expected_signature = hmac.new(
                settings.RAZORPAY_KEY_SECRET.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            return hmac.compare_digest(expected_signature, razorpay_signature)
        except Exception as e:
            print(f"Signature verification error: {e}")
            return False
    
    def fetch_payment(self, payment_id: str):
        """
        Fetch payment details from Razorpay
        
        Args:
            payment_id: Razorpay payment ID
            
        Returns:
            dict: Payment details
        """
        try:
            payment = self.client.payment.fetch(payment_id)
            return {
                "success": True,
                "payment": payment
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def refund_payment(self, payment_id: str, amount: float = None):
        """
        Refund a payment
        
        Args:
            payment_id: Razorpay payment ID
            amount: Amount to refund (None for full refund)
            
        Returns:
            dict: Refund details
        """
        try:
            data = {}
            if amount:
                data['amount'] = int(amount * 100)  # Convert to paise
            
            refund = self.client.payment.refund(payment_id, data)
            return {
                "success": True,
                "refund": refund
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

# Create singleton instance
razorpay_service = RazorpayService()
