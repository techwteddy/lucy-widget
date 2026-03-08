import stripe
from api.config import settings

def get_stripe():
    stripe.api_key = settings.stripe_secret_key
    return stripe

PLANS = {
    "free": {"chatbots": 1, "messages_per_month": 100, "price_id": None},
    "pro": {"chatbots": 5, "messages_per_month": 5000, "price_id": settings.stripe_pro_price_id},
    "business": {"chatbots": -1, "messages_per_month": 50000, "price_id": settings.stripe_business_price_id},
}
