import os
import logging
import asyncio
import random
from together import AsyncTogether
import pyshorteners

from dotenv import load_dotenv

load_dotenv()

PLACEHOLDER_ERROR_IMAGE = "/placeholder.png"
MAX_RETRIES = 3

async def generate_and_upload_flux(
    prompt: str,
    service: str = "flux",
    post_id: int = None,
    bucket_name: str = "bucket_nextcopy_content"
) -> str:
    """Generate image using FLUX model via Together API.
    Returns the image URL directly from Together API or placeholder on failure.
    """
    retry_count = 0
    
    # Initialize Together AI client
    api_key = os.environ.get("TOGETHER_API_KEY")
    if not api_key:
        logging.error("❌ TOGETHER_API_KEY environment variable not set.")
        return PLACEHOLDER_ERROR_IMAGE
    
    try:
        client = AsyncTogether(api_key=api_key)
    except Exception as e:
        logging.error(f"❌ Error initializing Together client: {str(e)}")
        return PLACEHOLDER_ERROR_IMAGE
    
    while retry_count <= MAX_RETRIES:
        try:
            if retry_count > 0:
                # Exponential backoff with jitter
                wait_time = (2 ** retry_count) + random.uniform(0, 1)
                logging.info(f"Rate limited. Retry {retry_count}/{MAX_RETRIES}. Waiting {wait_time:.2f} seconds...")
                await asyncio.sleep(wait_time)
            
            # Generate image using FLUX model
            logging.info(f"Generating image with prompt: {prompt[:50]}...")
            try:
                response = await client.images.generate(
                    prompt=prompt,
                    model="black-forest-labs/FLUX.1-schnell",
                    width=720,
                    height=1280,
                    steps=12,
                    n=1
                )
            except AttributeError as e:
                logging.error(f"❌ AttributeError in Together API: {str(e)}")
                retry_count += 1
                continue
            
            # Check if response exists and has data
            if not response:
                logging.warning("⚠️ Empty response from Together API")
                retry_count += 1
                continue
                
            if not hasattr(response, 'data') or not response.data or len(response.data) == 0:
                logging.warning(f"⚠️ No image data in response for prompt: {prompt[:50]}...")
                retry_count += 1
                continue
            
            # Get the image URL from the response
            if hasattr(response.data[0], 'url') and response.data[0].url:
                url = response.data[0].url
                logging.info(f"✅ Image generated: {url}")
                try:
                    # Try to shorten URL with TinyURL
                    shortener = pyshorteners.Shortener()
                    short_url = shortener.tinyurl.short(url)
                    logging.info(f"🔗 URL shortened: {short_url}")
                    return short_url
                except Exception as e:
                    logging.warning(f"⚠️ URL shortening failed, using original URL: {str(e)}")
                    return url
            else:
                logging.error("❌ No image URL in response")
                retry_count += 1
                continue

        except Exception as e:
            error_message = str(e)
            if "RateLimitError" in error_message or "429" in error_message:
                retry_count += 1
                if retry_count > MAX_RETRIES:
                    logging.error(f"❌ Exceeded maximum retries ({MAX_RETRIES}) due to rate limits.")
                    return PLACEHOLDER_ERROR_IMAGE
                # Retry logic will kick in at the beginning of the loop
            elif "_interpret_async_response" in error_message or "_interpret_response_line" in error_message:
                # Handle the specific error from the stack trace
                logging.error(f"❌ Together API response interpretation error: {error_message}")
                retry_count += 1
                if retry_count > MAX_RETRIES:
                    logging.error(f"❌ Exceeded maximum retries ({MAX_RETRIES}) after API response errors.")
                    return PLACEHOLDER_ERROR_IMAGE
                continue
            else:
                logging.error(f"❌ Error in flux image generation: {error_message}", exc_info=True)
                return PLACEHOLDER_ERROR_IMAGE
    
    logging.error(f"❌ Failed to generate image after {MAX_RETRIES} retries.")
    return PLACEHOLDER_ERROR_IMAGE