"""
BROWSER & VISION SERVICE
========================
1. Headless Chrome via browser-use logic for agent browsing
2. VisionClaw/OpenVision integration: GLM-5.2-Vision verifies generated
   designs look correct before saving (no text garbling, clean edges, etc.)
"""

import asyncio
import base64
import httpx
from typing import Optional, Dict, Any, List
from pathlib import Path
from services.model_router import model_router
from config import SETTINGS


class BrowserVisionService:
    """
    Combines headless browsing (for agents that need to see the web)
    with vision QA (for verifying generated designs).
    """

    def __init__(self):
        self.browser_available = False
        self._check_browser()

    def _check_browser(self):
        """Check if playwright/browser-use is available"""
        try:
            import playwright  # noqa
            self.browser_available = True
        except ImportError:
            self.browser_available = False
            print("[BrowserVision] Playwright not installed - browser features disabled")

    async def screenshot_url(self, url: str, full_page: bool = True) -> Optional[str]:
        """
        Take a screenshot of a URL using headless Chrome.
        Returns base64-encoded PNG.
        """
        if not self.browser_available:
            return await self._fallback_screenshot(url)

        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(
                    viewport={"width": 1280, "height": 720}
                )
                await page.goto(url, wait_until="networkidle", timeout=30000)
                screenshot_bytes = await page.screenshot(full_page=full_page)
                await browser.close()

                return base64.b64encode(screenshot_bytes).decode()
        except Exception as e:
            print(f"[BrowserVision] Screenshot error: {e}")
            return await self._fallback_screenshot(url)

    async def _fallback_screenshot(self, url: str) -> Optional[str]:
        """Fallback when browser isn't available - return None"""
        print(f"[BrowserVision] No browser available to screenshot: {url}")
        return None

    async def browse_and_extract(self, url: str, extraction_prompt: str) -> Dict:
        """
        Browse a URL, take a screenshot, and have GLM-5.2-Vision extract info.
        Useful for agents that need to "see" a competitor's page.
        """
        screenshot_b64 = await self.screenshot_url(url)

        if not screenshot_b64:
            return {"error": "Could not capture screenshot", "url": url}

        # Use vision to analyze the screenshot
        result = await model_router.vision_call(
            prompt=f"""Analyze this webpage screenshot and extract:

{extraction_prompt}

URL: {url}

Be specific. Quote actual text you see. Note layout, colors, pricing, calls-to-action.""",
            image_b64=screenshot_b64,
            system_prompt="You are a web analysis agent. Extract exactly what you see. Be specific.",
            task_type="vision_qa"
        )

        return {
            "url": url,
            "analysis": result["content"],
            "screenshot_captured": True
        }

    async def verify_design(
        self,
        image_b64: str,
        product_type: str,
        requirements: Optional[Dict] = None
    ) -> Dict:
        """
        Vision QA for a generated design.
        Verifies it looks like the intended product type before saving.

        Returns:
        {
            "approved": bool,
            "issues": ["issue 1", ...],
            "feedback": "what to fix",
            "quality_score": 0-100
        }
        """
        requirements = requirements or {}

        prompt = f"""You are a design quality auditor. Examine this generated image.

PRODUCT TYPE: {product_type}
REQUIREMENTS: {requirements if requirements else "Standard for this product type"}

Check:
1. Does this look like a {product_type}? (Y/N)
2. Is there any text garbling or gibberish text? (Y/N)
3. Is the background clean (especially important for stickers)? (Y/N)
4. Is the composition commercially viable (clear focal point, readable at thumbnail size)? (Y/N)
5. Are colors appropriate and appealing? (Y/N)
6. Any obvious AI artifacts (extra fingers, warped text, melted elements)? (Y/N)

Output JSON:
{{
    "approved": true/false,
    "looks_like_product": true/false,
    "text_garbling": true/false,
    "clean_background": true/false,
    "commercially_viable": true/false,
    "colors_appropriate": true/false,
    "ai_artifacts": true/false,
    "issues": ["specific issue 1", "specific issue 2"],
    "feedback": "what to fix in the prompt for regeneration",
    "quality_score": 0-100
}}"""

        result = await model_router.vision_call(
            prompt=prompt,
            image_b64=image_b64,
            system_prompt="You are a strict design QA auditor. Be honest. Bad designs waste money.",
            task_type="vision_qa"
        )

        content = result["content"]
        if isinstance(content, dict):
            return content
        # Fallback parse
        return {
            "approved": False,
            "issues": ["Could not parse vision response"],
            "feedback": str(content),
            "quality_score": 0
        }

    async def verify_and_regenerate(
        self,
        image_b64: str,
        original_prompt: str,
        product_type: str,
        regenerate_fn,
        max_retries: int = 2
    ) -> Dict:
        """
        Verify a design, and if it fails, regenerate with mutated prompt.
        Max 2 retries to save costs.
        """
        attempts = 0
        current_prompt = original_prompt
        current_image = image_b64

        while attempts <= max_retries:
            verification = await self.verify_design(current_image, product_type)

            if verification.get("approved"):
                return {
                    "approved": True,
                    "image_b64": current_image,
                    "verification": verification,
                    "attempts": attempts,
                    "final_prompt": current_prompt
                }

            # Mutate prompt based on feedback
            feedback = verification.get("feedback", "improve quality")
            issues = verification.get("issues", [])

            # Add quality modifiers based on issues
            modifiers = []
            if verification.get("text_garbling"):
                modifiers.append("no text, text-free, purely visual")
            if not verification.get("clean_background"):
                modifiers.append("clean solid background, no clutter")
            if verification.get("ai_artifacts"):
                modifiers.append("high quality, detailed, no warped elements")
            if not verification.get("commercially_viable"):
                modifiers.append("clear focal point, bold composition, readable at small size")

            if modifiers:
                current_prompt = f"{original_prompt}. {', '.join(modifiers)}"
            else:
                current_prompt = f"{original_prompt}. high quality, professional, {feedback}"

            attempts += 1
            print(f"[VisionQA] Attempt {attempts}: Regenerating with feedback: {feedback}")

            if attempts <= max_retries:
                # Regenerate using the provided function
                try:
                    current_image = await regenerate_fn(current_prompt)
                except Exception as e:
                    print(f"[VisionQA] Regeneration failed: {e}")
                    break

        # Max retries reached - return last result even if not approved
        return {
            "approved": False,
            "image_b64": current_image,
            "verification": verification,
            "attempts": attempts,
            "final_prompt": current_prompt,
            "message": "Max retries reached. Manual review recommended."
        }


# Global instance
browser_vision_service = BrowserVisionService()
