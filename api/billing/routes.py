from fastapi import APIRouter, Depends, HTTPException, Request, Header
from pydantic import BaseModel
from api.auth.middleware import get_current_user, CurrentUser
from api.dependencies import get_redis
from .stripe_client import get_stripe, PLANS
from api.config import settings
import redis.asyncio as aioredis
import stripe as _stripe

router = APIRouter(prefix="/billing", tags=["billing"])


class CheckoutRequest(BaseModel):
    plan: str  # "pro" or "business"
    success_url: str
    cancel_url: str


@router.post("/checkout")
async def create_checkout(
    body: CheckoutRequest,
    user: CurrentUser = Depends(get_current_user),
):
    s = get_stripe()
    plan = PLANS.get(body.plan)
    if not plan or not plan["price_id"]:
        raise HTTPException(status_code=400, detail="Invalid plan")
    session = s.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": plan["price_id"], "quantity": 1}],
        customer_email=user.email,
        success_url=body.success_url,
        cancel_url=body.cancel_url,
        metadata={"user_email": user.email, "plan": body.plan},
    )
    return {"checkout_url": session.url}


@router.post("/portal")
async def billing_portal(
    body: dict,
    user: CurrentUser = Depends(get_current_user),
):
    s = get_stripe()
    customers = s.Customer.list(email=user.email, limit=1)
    if not customers.data:
        raise HTTPException(status_code=404, detail="No billing account found")
    session = s.billing_portal.Session.create(
        customer=customers.data[0].id,
        return_url=body.get("return_url", "/dashboard"),
    )
    return {"portal_url": session.url}


PLAN_TIER_MAP = {
    settings.stripe_pro_price_id: "pro",
    settings.stripe_business_price_id: "business",
}


async def _handle_subscription_upsert(
    subscription: dict, redis_client: aioredis.Redis
) -> None:
    """Handle subscription.created and subscription.updated events."""
    customer_id = subscription["customer"]
    price_id = (
        subscription["items"]["data"][0]["price"]["id"]
        if subscription.get("items")
        else None
    )
    status = subscription["status"]
    plan = PLAN_TIER_MAP.get(price_id, "free") if price_id else "free"

    if status in ("active", "trialing"):
        await redis_client.hset(
            f"subscription:{customer_id}",
            mapping={
                "plan": plan,
                "status": status,
                "subscription_id": subscription["id"],
                "price_id": price_id or "",
            },
        )
        await redis_client.expire(f"subscription:{customer_id}", 86400 * 30)


async def _handle_subscription_deleted(
    subscription: dict, redis_client: aioredis.Redis
) -> None:
    """Handle subscription.deleted — reset customer to free plan."""
    customer_id = subscription["customer"]
    await redis_client.hset(
        f"subscription:{customer_id}",
        mapping={
            "plan": "free",
            "status": "canceled",
        },
    )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(..., alias="stripe-signature"),
    redis_client: aioredis.Redis = Depends(get_redis),
):
    payload = await request.body()
    try:
        event = _stripe.Webhook.construct_event(
            payload, stripe_signature, settings.stripe_webhook_secret
        )
    except _stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    subscription = event["data"]["object"]

    if event["type"] in (
        "customer.subscription.created",
        "customer.subscription.updated",
    ):
        await _handle_subscription_upsert(subscription, redis_client)
    elif event["type"] == "customer.subscription.deleted":
        await _handle_subscription_deleted(subscription, redis_client)

    return {"received": True}
