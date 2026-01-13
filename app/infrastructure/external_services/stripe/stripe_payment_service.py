import stripe
from app.application.interfaces.services.payment_service import PaymentService
from typing import Any, Dict
from app.config import settings

class StripePaymentService(PaymentService):
    def __init__(self, secret_key: str):
        stripe.api_key = secret_key

    def create_checkout_session(self, user_id: int, plan: str) -> Dict[str, Any]:
        """Create a Stripe Checkout Session for a subscription."""
        # Use price ID from settings (configured via .env)
        price_id = settings.STRIPE_PRICE_ID
        
        if not price_id or price_id == "price_test":
            raise ValueError("STRIPE_PRICE_ID is not configured or is using a placeholder. Please set a valid Price ID from your Stripe Dashboard.")

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=settings.STRIPE_SUCCESS_URL or "http://localhost:8000/dashboard?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=settings.STRIPE_CANCEL_URL or "http://localhost:8000/dashboard",
            client_reference_id=str(user_id),
        )
        return {"session_id": session.id, "url": session.url}

    def handle_webhook(self, payload: bytes, sig_header: str) -> stripe.Event:
        """Verify and construct a Stripe Webhook event."""
        webhook_secret = settings.STRIPE_WEBHOOK_SECRET
        if not webhook_secret:
            raise ValueError("STRIPE_WEBHOOK_SECRET is not configured.")
            
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
            return event
        except ValueError as e:
            raise e
        except stripe.error.SignatureVerificationError as e:
            raise e

    def cancel_subscription(self, user_id: int) -> None:
        # Lookup user's Stripe subscription and cancel it
        # ... (to be implemented)
        pass

    def get_subscription_status(self, user_id: int) -> str:
        # Lookup user's subscription status
        # ... (to be implemented)
        return "free"
