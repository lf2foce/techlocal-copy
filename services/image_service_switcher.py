import os
import logging
from typing import Optional

from services.gemini_image_handler import generate_and_upload_async as generate_gemini
from services.ideogram_handler import generate_and_upload_ideogram as generate_ideogram
from services.flux_image_handler import generate_and_upload_flux as generate_flux
from services.locaith_handler import generate_and_upload_locaith as generate_locaith

async def generate_image(prompt: str, service: str = "gemini", post_id: Optional[int] = None) -> str:
    """Generate image using specified service.
    
    Args:
        prompt (str): The image generation prompt
        service (str): The service to use ("gemini", "ideogram", or "flux")
        post_id (Optional[int]): Post ID for Gemini storage path (only used with Gemini)
        
    Returns:
        str: The URL of the generated image or placeholder on failure
    """
    try:
        service = service.lower()
        if service == "gemini":
            return await generate_gemini(prompt, post_id)
        elif service == "ideogram":
            result = await generate_ideogram(prompt)
            return result if result else "/placeholder.png"
        elif service == "flux":
            result = await generate_flux(prompt)
            return result if result else "/placeholder.png"
        elif service == "locaith":
            result = await generate_locaith(prompt)
            return result if result else "/placeholder.png"
        else:
            raise ValueError(f"Unsupported image service: {service}")
    except Exception as e:
        logging.error(f"❌ Error generating image with {service}: {e}")
        return "/placeholder.png"