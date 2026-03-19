class StripeIntegration:
    """Mock interface to show production topology for Stripe Checkout APIs."""
    @staticmethod
    async def create_payment_link(amount: float, booking_id: str) -> str:
        from app.config.settings import settings
        if settings.ENV == "dev":
            print(f">>> [DEV STRIPE] Mock payment link for ${amount}")
            return "mock_payment|Payment assumed successful"
            
        """
        Creates a payment link. In real life, hitting the stripe API:
        """
        try:
            # Simulate real Stripe session creation
            # session = stripe.checkout.Session.create(...)
            return f"https://buy.stripe.com/test_{booking_id}"
        except Exception:
            # Fallback circuit breaker
            import logging
            logging.getLogger(__name__).warning("Stripe API failed. Marking payment as pending via text instructions bypass.")
            return "PAYMENT_SYSTEM_DOWN_FALLBACK"
