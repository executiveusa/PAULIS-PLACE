import httpx
from typing import Optional
from config import SETTINGS
import hashlib
import base64


class EtsyService:
    """Etsy Open API v3 integration"""

    BASE_URL = "https://openapi.etsy.com/v3/application"

    def __init__(self):
        self.api_key = SETTINGS.etsy_api_key
        self.access_token = SETTINGS.etsy_access_token
        self.headers = {
            "x-api-key": self.api_key,
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    async def upload_image(self, image_bytes: bytes, listing_id: int = None) -> dict:
        """Upload image to Etsy"""
        # Etsy requires multipart form upload
        async with httpx.AsyncClient(headers={
            "x-api-key": self.api_key,
            "Authorization": f"Bearer {self.access_token}"
        }) as client:
            files = {
                "image": ("image.png", image_bytes, "image/png")
            }
            if listing_id:
                url = f"{self.BASE_URL}/listings/{listing_id}/images"
            else:
                url = f"{self.BASE_URL}/listings/images"

            response = await client.post(url, files=files)
            response.raise_for_status()
            return response.json()

    async def create_listing(
        self,
        title: str,
        description: str,
        price: float,
        tags: list,
        category_id: int,
        image_ids: list = None
    ) -> dict:
        """Create a draft listing on Etsy"""
        payload = {
            "title": title[:140],  # Etsy limit
            "description": description,
            "price": price,
            "quantity": 999,  # Digital = unlimited
            "tags": tags[:13],  # Etsy limit
            "category_id": category_id,
            "who_made": "i_made",
            "is_supply": False,
            "when_made": "2020_2024",
            "item_weight_units": "oz",
            "item_weight": 0,
            "item_length_units": "in",
            "item_length": 1,
            "item_width_units": "in",
            "item_width": 1,
            "item_height_units": "in",
            "item_height": 1,
            "is_digital": True,
            "file_data": "",  # Would need actual file for digital
            "should_auto_renew": True,
            "is_private": False,
            "state": "draft",  # Always draft first for human review
        }

        async with httpx.AsyncClient(headers=self.headers) as client:
            response = await client.post(
                f"{self.BASE_URL}/listings",
                json=payload
            )
            response.raise_for_status()
            return response.json()

    async def publish_listing(self, listing_id: int) -> dict:
        """Publish a draft listing"""
        async with httpx.AsyncClient(headers=self.headers) as client:
            response = await client.put(
                f"{self.BASE_URL}/listings/{listing_id}/state",
                json={"state": "active"}
            )
            return response.json()

    async def get_listing_inventory(self, listing_id: int) -> dict:
        """Get listing details"""
        async with httpx.AsyncClient(headers=self.headers) as client:
            response = await client.get(f"{self.BASE_URL}/listings/{listing_id}")
            return response.json()


etsy_service = EtsyService()
