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
        self.client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
        self.client.set_app_details({
            "title": "Fuji Sakura Food Delivery",
            "version": "1.0"
        })
    
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
            
            
            # Create order in Razorpay
            razorpay_order = self.client.order.create({
                "amount": amount_in_paise,
                "currency": currency,
                "receipt": f"order_{order_id}",
                "payment_capture": 1  # Auto capture payment
            })
            
            
            return {
                "success": True,
                "razorpay_order_id": razorpay_order["id"],
                "amount": razorpay_order["amount"],
                "currency": razorpay_order["currency"],
                "receipt": razorpay_order["receipt"]
            }
        except Exception as e:
            import traceback
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
        """Verify payment signature for security"""
        try:
            
            message = f"{razorpay_order_id}|{razorpay_payment_id}"
            
            expected_signature = hmac.new(
                settings.RAZORPAY_KEY_SECRET.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            is_valid = hmac.compare_digest(expected_signature, razorpay_signature)
            
            if is_valid:
                pass
            else:
                pass
            
            return is_valid
        except Exception as e:
            import traceback
            return False
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
            amount: Amount to refund in rupees (None for full refund)
            
        Returns:
            dict: Refund details
        """
        try:
            # Amount must be integer paise for Razorpay
            data = {}
            if amount:
                data['amount'] = int(round(amount * 100))  # Convert rupees to paise as integer
            
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

