import httpx
from typing import Any
from config import SETTINGS


class EtsyConfigurationError(RuntimeError):
    pass


class EtsyValidationError(RuntimeError):
    pass


class EtsyService:
    """Governed Etsy Open API v3 integration.

    POD and digital-product semantics are separated. Physical POD listings fail
    closed unless shop/auth, shipping profile and processing/readiness profile
    configuration are present. Draft creation and publish remain distinct.
    """

    BASE_URL = "https://openapi.etsy.com/v3/application"

    def __init__(self):
        self.api_key = SETTINGS.etsy_api_key
        self.api_secret = SETTINGS.etsy_secret
        self.access_token = SETTINGS.etsy_access_token
        self.shop_id = SETTINGS.etsy_shop_id
        self.shipping_profile_id = int(SETTINGS.etsy_shipping_profile_id or 0)
        self.readiness_state_id = int(SETTINGS.etsy_readiness_state_id or 0)

    @property
    def configured(self) -> bool:
        return bool(
            self.api_key
            and self.api_secret
            and self.access_token
            and self.shop_id
            and self.shipping_profile_id > 0
            and self.readiness_state_id > 0
        )

    def _require_configured(self) -> None:
        if not self.configured:
            raise EtsyConfigurationError(
                "Etsy api key/secret, access token, shop id, shipping profile id, "
                "and readiness state id must be configured for physical POD listings"
            )

    @property
    def headers(self) -> dict[str, str]:
        self._require_configured()
        return {
            "x-api-key": f"{self.api_key}:{self.api_secret}",
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/x-www-form-urlencoded",
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
        headers = {
            "x-api-key": f"{self.api_key}:{self.api_secret}",
            "Authorization": f"Bearer {self.access_token}",
        }
        async with httpx.AsyncClient(headers=headers) as client:
            response = await client.post(
                f"{self.BASE_URL}/shops/{self.shop_id}/listings/{int(listing_id)}/images",
                files={"image": ("image.png", image_bytes, "image/png")},
                data={"rank": str(int(rank))},
            )
            response.raise_for_status()
            body = response.json()
        if not body.get("listing_image_id"):
            raise EtsyValidationError("Etsy image upload returned no listing_image_id")
        return body

    async def create_pod_draft_listing(
        self,
        *,
        title: str,
        description: str,
        price: float,
        quantity: int,
        taxonomy_id: int,
        tags: list[str],
        who_made: str = "i_did",
        when_made: str = "made_to_order",
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
            "price": f"{float(price):.2f}",
            "who_made": who_made,
            "when_made": when_made,
            "taxonomy_id": int(taxonomy_id),
            "shipping_profile_id": self.shipping_profile_id,
            "readiness_state_id": self.readiness_state_id,
            "should_auto_renew": str(bool(should_auto_renew)).lower(),
            "is_supply": "false",
            "type": "physical",
        }
        if tags:
            payload["tags"] = ",".join(str(tag)[:20] for tag in tags[:13])

        async with httpx.AsyncClient(headers=self.headers) as client:
            response = await client.post(
                f"{self.BASE_URL}/shops/{self.shop_id}/listings",
                params={"legacy": "false"},
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
            body = response.json()
        if str(body.get("state", "")).lower() != "active":
            raise EtsyValidationError("Etsy publish did not return an active listing")
        return body


etsy_service = EtsyService()
