import pytest
from httpx import AsyncClient
from app.config import settings

pytestmark = pytest.mark.asyncio

@pytest.mark.skipif(not settings.STRIPE_WEBHOOK_SECRET, reason="No STRIPE_WEBHOOK_SECRET configured")
async def test_stripe_webhook_endpoint(client):
    # Send a dummy payload and signature (should fail with 400, but endpoint should exist)
    payload = b'{}'
    sig = 'whsec_test'
    r = await client.post("/api/v1/stripe/webhook", content=payload, headers={"stripe-signature": sig})
    assert r.status_code in (200, 400)
