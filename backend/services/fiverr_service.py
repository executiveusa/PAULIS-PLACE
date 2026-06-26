import httpx
from typing import Optional
from config import SETTINGS


class FiverrService:
    """
    Fiverr API integration - LIMITED

    Fiverr's API is very restricted. Most operations require:
    - Human login/session
    - Manual gig creation through their UI

    This service handles what little automation is possible.
    """

    BASE_URL = "https://api.fiverr.com/v2"

    def __init__(self):
        self.access_token = SETTINGS.fiverr_access_token
        self.headers = {
            "Authorization": f"bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    async def get_gigs(self) -> list:
        """Get current user's gigs (read-only)"""
        # Note: Fiverr's public API is very limited
        # This would require their private/partner API access
        return []

    async def get_gig_analytics(self, gig_id: str) -> dict:
        """Get analytics for a gig (if accessible)"""
        # Requires seller dashboard API access
        return {}

    def generate_gig_brief(self, product_data: dict) -> dict:
        """
        Generate a brief for MANUAL gig creation.

        Since Fiverr requires human interaction, we generate
        everything needed for quick manual setup.
        """
        return {
            "title": product_data.get('title', '')[:80],  # Fiverr limit
            "category": self._map_category(product_data.get('product_type')),
            "pricing": {
                "basic": {
                    "title": product_data.get('title', ''),
                    "description": product_data.get('description', '')[:600],
                    "delivery_days": 1,
                    "revisions": 1,
                    "price": product_data.get('price', 5),
                }
            },
            "description": product_data.get('description', ''),
            "requirements": "Please describe your specific needs, preferred style, and any reference images.",
            "tags": product_data.get('tags', [])[:5],
            "faq": [
                {
                    "question": "What file formats do you provide?",
                    "answer": "PNG (transparent background), JPG, and source files upon request."
                },
                {
                    "question": "Can you make revisions?",
                    "answer": f"Yes, {1} revision is included. Additional revisions available for extra fee."
                }
            ],
            "gallery_images": product_data.get('variation_paths', []),
            "action_required": "MANUAL: Copy this data to Fiverr gig creation form"
        }

    def _map_category(self, product_type: str) -> dict:
        """Map product types to Fiverr categories"""
        mapping = {
            "thumbnail": {
                "category": "Graphics & Design",
                "subcategory": "Web & App Design",
                "nested_subcategory": "Thumbnail Design"
            },
            "template": {
                "category": "Graphics & Design",
                "subcategory": "Creative Design",
                "nested_subcategory": "Templates"
            },
            "digital_download": {
                "category": "Graphics & Design",
                "subcategory": "Creative Design",
                "nested_subcategory": "Other"
            }
        }
        return mapping.get(product_type, {
            "category": "Graphics & Design",
            "subcategory": "Creative Design",
            "nested_subcategory": "Other"
        })


fiverr_service = FiverrService()
