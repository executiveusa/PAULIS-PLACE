import httpx
from typing import Optional
from config import SETTINGS


class PrintifyService:
    """Printify API integration for POD products"""

    BASE_URL = "https://api.printify.com/v1"

    # Blueprint IDs for common products
    BLUEPRINTS = {
        "t_shirt": 6,           # Gildan 5000
        "mug": 17,              # Standard Ceramic Mug
        "phone_case": 152,      # iPhone Case
        "poster": 201,          # Posters
        "sticker": 264,         # Die-Cut Sticker
    }

    def __init__(self):
        self.token = SETTINGS.printify_token
        self.shop_id = SETTINGS.printify_shop_id
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    async def upload_image(self, image_url: str, filename: str) -> dict:
        """Upload design image to Printify"""
        async with httpx.AsyncClient(headers=self.headers) as client:
            response = await client.post(
                f"{self.BASE_URL}/uploads/images.json",
                json={
                    "file_name": filename,
                    "url": image_url
                }
            )
            response.raise_for_status()
            return response.json()

    async def create_product(
        self,
        title: str,
        description: str,
        blueprint_id: int,
        image_id: str,
        variant_ids: list,
        price: float,
        tags: list = None
    ) -> dict:
        """Create a product in Printify"""

        # Build variants with pricing
        variants = []
        for vid in variant_ids:
            variants.append({
                "id": vid,
                "price": int(price * 100),  # Printify uses cents
                "is_enabled": True
            })

        payload = {
            "title": title,
            "description": description,
            "blueprint_id": blueprint_id,
            "print_provider_id": 1,  # Will need to be determined based on blueprint
            "variants": variants,
            "print_options": [],
            "images": [{
                "id": image_id,
                "position": 1,
                "is_default": True
            }]
        }

        async with httpx.AsyncClient(headers=self.headers) as client:
            response = await client.post(
                f"{self.BASE_URL}/shops/{self.shop_id}/products.json",
                json=payload
            )
            response.raise_for_status()
            return response.json()

    async def publish_product(self, product_id: str) -> dict:
        """Publish product to sales channel"""
        async with httpx.AsyncClient(headers=self.headers) as client:
            response = await client.post(
                f"{self.BASE_URL}/shops/{self.shop_id}/products/{product_id}/publish.json",
                json={"title": True, "description": True, "images": True, "variants": True}
            )
            return response.json()

    async def get_blueprints(self) -> list:
        """Get available blueprints"""
        async with httpx.AsyncClient(headers=self.headers) as client:
            response = await client.get(f"{self.BASE_URL}/blueprints.json")
            return response.json()


printify_service = PrintifyService()
