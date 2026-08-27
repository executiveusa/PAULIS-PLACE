import httpx
from dataclasses import dataclass
from typing import Any, Optional
from config import SETTINGS


class PrintifyConfigurationError(RuntimeError):
    pass


class PrintifyValidationError(RuntimeError):
    pass


@dataclass(frozen=True)
class PrintifyVariant:
    id: int
    title: str
    options: dict[str, Any]


class PrintifyService:
    """Governed Printify API integration for POD products.

    The service fails closed when credentials/shop metadata are missing and
    verifies providers/variants against Printify before product creation.
    """

    BASE_URL = "https://api.printify.com/v1"

    def __init__(self):
        self.token = SETTINGS.printify_token
        self.shop_id = SETTINGS.printify_shop_id

    @property
    def configured(self) -> bool:
        return bool(self.token and self.shop_id)

    def _require_configured(self) -> None:
        if not self.configured:
            raise PrintifyConfigurationError("Printify token/shop id are not configured")

    @property
    def headers(self) -> dict[str, str]:
        self._require_configured()
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    async def get_shops(self) -> list[dict[str, Any]]:
        self._require_configured()
        async with httpx.AsyncClient(headers=self.headers) as client:
            response = await client.get(f"{self.BASE_URL}/shops.json")
            response.raise_for_status()
            return response.json()

    async def verify_shop(self) -> dict[str, Any]:
        shops = await self.get_shops()
        for shop in shops:
            if str(shop.get("id")) == str(self.shop_id):
                return shop
        raise PrintifyValidationError(f"Configured Printify shop_id {self.shop_id} was not returned by Printify")

    async def upload_image(self, image_url: str, filename: str) -> dict[str, Any]:
        self._require_configured()
        if not image_url or not filename:
            raise PrintifyValidationError("image_url and filename are required")
        async with httpx.AsyncClient(headers=self.headers) as client:
            response = await client.post(
                f"{self.BASE_URL}/uploads/images.json",
                json={"file_name": filename, "url": image_url},
            )
            response.raise_for_status()
            body = response.json()
        if not body.get("id"):
            raise PrintifyValidationError("Printify upload returned no image id")
        return body

    async def get_blueprints(self) -> list[dict[str, Any]]:
        self._require_configured()
        async with httpx.AsyncClient(headers=self.headers) as client:
            response = await client.get(f"{self.BASE_URL}/catalog/blueprints.json")
            response.raise_for_status()
            return response.json()

    async def get_print_providers(self, blueprint_id: int) -> list[dict[str, Any]]:
        self._require_configured()
        async with httpx.AsyncClient(headers=self.headers) as client:
            response = await client.get(f"{self.BASE_URL}/catalog/blueprints/{int(blueprint_id)}/print_providers.json")
            response.raise_for_status()
            return response.json()

    async def get_variants(self, blueprint_id: int, print_provider_id: int) -> dict[str, Any]:
        self._require_configured()
        async with httpx.AsyncClient(headers=self.headers) as client:
            response = await client.get(
                f"{self.BASE_URL}/catalog/blueprints/{int(blueprint_id)}/print_providers/{int(print_provider_id)}/variants.json"
            )
            response.raise_for_status()
            return response.json()

    async def validate_catalog_selection(
        self,
        *,
        blueprint_id: int,
        print_provider_id: int,
        variant_ids: list[int],
    ) -> dict[str, Any]:
        if not variant_ids:
            raise PrintifyValidationError("At least one Printify variant is required")
        providers = await self.get_print_providers(blueprint_id)
        if int(print_provider_id) not in {int(p.get("id")) for p in providers if p.get("id") is not None}:
            raise PrintifyValidationError(
                f"Print provider {print_provider_id} is not valid for blueprint {blueprint_id}"
            )
        variant_payload = await self.get_variants(blueprint_id, print_provider_id)
        available = {int(v.get("id")) for v in variant_payload.get("variants", []) if v.get("id") is not None}
        missing = [int(v) for v in variant_ids if int(v) not in available]
        if missing:
            raise PrintifyValidationError(f"Invalid Printify variants for selected provider: {missing}")
        return {"providers": providers, "variants": variant_payload}

    async def create_product(
        self,
        *,
        title: str,
        description: str,
        blueprint_id: int,
        print_provider_id: int,
        image_id: str,
        variant_ids: list[int],
        price_cents: int,
        print_area_placeholders: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        self._require_configured()
        if not title.strip() or not description.strip():
            raise PrintifyValidationError("title and description are required")
        if not image_id:
            raise PrintifyValidationError("A verified Printify image id is required")
        if price_cents <= 0:
            raise PrintifyValidationError("price_cents must be positive")

        await self.verify_shop()
        await self.validate_catalog_selection(
            blueprint_id=blueprint_id,
            print_provider_id=print_provider_id,
            variant_ids=variant_ids,
        )

        placeholders = print_area_placeholders or [
            {
                "position": "front",
                "images": [{"id": image_id, "x": 0.5, "y": 0.5, "scale": 1, "angle": 0}],
            }
        ]
        payload = {
            "title": title,
            "description": description,
            "blueprint_id": int(blueprint_id),
            "print_provider_id": int(print_provider_id),
            "variants": [
                {"id": int(variant_id), "price": int(price_cents), "is_enabled": True}
                for variant_id in variant_ids
            ],
            "print_areas": [{"variant_ids": [int(v) for v in variant_ids], "placeholders": placeholders}],
        }

        async with httpx.AsyncClient(headers=self.headers) as client:
            response = await client.post(
                f"{self.BASE_URL}/shops/{self.shop_id}/products.json",
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
        if not body.get("id"):
            raise PrintifyValidationError("Printify create product returned no product id")
        return body

    async def get_product(self, product_id: str) -> dict[str, Any]:
        self._require_configured()
        async with httpx.AsyncClient(headers=self.headers) as client:
            response = await client.get(f"{self.BASE_URL}/shops/{self.shop_id}/products/{product_id}.json")
            response.raise_for_status()
            return response.json()

    async def publish_product(self, product_id: str) -> dict[str, Any]:
        self._require_configured()
        if not product_id:
            raise PrintifyValidationError("product_id is required")
        async with httpx.AsyncClient(headers=self.headers) as client:
            response = await client.post(
                f"{self.BASE_URL}/shops/{self.shop_id}/products/{product_id}/publish.json",
                json={"title": True, "description": True, "images": True, "variants": True, "tags": True},
            )
            response.raise_for_status()
            return response.json()


printify_service = PrintifyService()
