import httpx
from typing import Any, Optional
from config import SETTINGS


class EtsyConfigurationError(RuntimeError):
    pass


class EtsyValidationError(RuntimeError):
    pass


class EtsyService:
    """Governed Etsy Open API v3 integration.

    POD and digital-product semantics are separated. This service fails closed
    when shop/auth configuration is incomplete and always creates POD listings
    as drafts before a separate approval-gated publish step.
    """

    BASE_URL = "https://openapi.etsy.com/v3/application"

    def __init__(self):
        self.api_key = SETTINGS.etsy_api_key
        self.access_token = SETTINGS.etsy_access_token
        self.shop_id = getattr(SETTINGS, "etsy_shop_id", "") or ""

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.access_token and self.shop_id)

    def _require_configured(self) -> None:
        if not self.configured:
            raise EtsyConfigurationError("Etsy api key, access token, and shop id must be configured")

    @property
    def headers(self) -> dict[str, str]:
        self._require_configured()
        return {
            "x-api-key": self.api_key,
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def get_shop(self) -> dict[str, Any]:
        self._require_configured()
        async with httpx.AsyncClient(headers=self.headers) as client:
            response = await client.get(f"{self.BASE_URL}/shops/{self.shop_id}")
            response.raise_for_status()
            body = response.json()
        if str(body.get("shop_id")) != str(self.shop_id):
            raise EtsyValidationError("Configured Etsy shop id could not be verified")
        return body

    async def upload_listing_image(self, listing_id: int, image_bytes: bytes, *, rank: int = 1) -> dict[str, Any]:
        self._require_configured()
        if not listing_id or not image_bytes:
            raise EtsyValidationError("listing_id and image bytes are required")
        headers = {"x-api-key": self.api_key, "Authorization": f"Bearer {self.access_token}"}
        async with httpx.AsyncClient(headers=headers) as client:
            response = await client.post(
                f"{self.BASE_URL}/shops/{self.shop_id}/listings/{int(listing_id)}/images",
                files={"image": ("image.png", image_bytes, "image/png")},
                data={"rank": str(int(rank))},
            )
            response.raise_for_status()
            return response.json()

    async def create_pod_draft_listing(
        self,
        *,
        title: str,
        description: str,
        price: float,
        quantity: int,
        taxonomy_id: int,
        tags: list[str],
        who_made: str = "i_made",
        when_made: str = "2020_2025",
        should_auto_renew: bool = True,
    ) -> dict[str, Any]:
        self._require_configured()
        if not title.strip() or not description.strip():
            raise EtsyValidationError("title and description are required")
        if price <= 0 or quantity <= 0 or taxonomy_id <= 0:
            raise EtsyValidationError("positive price, quantity, and taxonomy_id are required")
        await self.get_shop()

        payload = {
            "quantity": int(quantity),
            "title": title[:140],
            "description": description,
            "price": float(price),
            "who_made": who_made,
            "when_made": when_made,
            "taxonomy_id": int(taxonomy_id),
            "should_auto_renew": bool(should_auto_renew),
            "is_supply": False,
            "type": "physical",
            "tags": [str(tag)[:20] for tag in tags[:13]],
        }
        async with httpx.AsyncClient(headers=self.headers) as client:
            response = await client.post(
                f"{self.BASE_URL}/shops/{self.shop_id}/listings",
                data=payload,
            )
            response.raise_for_status()
            body = response.json()
        if not body.get("listing_id"):
            raise EtsyValidationError("Etsy draft creation returned no listing_id")
        return body

    async def get_listing(self, listing_id: int) -> dict[str, Any]:
        self._require_configured()
        async with httpx.AsyncClient(headers=self.headers) as client:
            response = await client.get(f"{self.BASE_URL}/listings/{int(listing_id)}")
            response.raise_for_status()
            return response.json()

    async def publish_listing(self, listing_id: int) -> dict[str, Any]:
        self._require_configured()
        if not listing_id:
            raise EtsyValidationError("listing_id is required")
        async with httpx.AsyncClient(headers=self.headers) as client:
            response = await client.put(
                f"{self.BASE_URL}/shops/{self.shop_id}/listings/{int(listing_id)}",
                data={"state": "active"},
            )
            response.raise_for_status()
            return response.json()


etsy_service = EtsyService()
