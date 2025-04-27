import os
import gc
import uuid
import time
import logging
import asyncio
from io import BytesIO

from google import genai
from google.genai import types
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()
# Constants
PLACEHOLDER_ERROR_IMAGE = "/placeholder.png"
rate_limit_delay = 2  # seconds between calls
semaphore = asyncio.Semaphore(1)  # sequential rate-limited calls


def generate_image_gemini(prompt: str):
    """Generate image from Gemini (sync) with optimized memory handling"""
    max_retries = 3
    retry_delay = 1
    client_gemini = None

    try:
        client_gemini = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        for attempt in range(max_retries):
            try:
                logging.info(f"🎨 Gemini generation attempt {attempt + 1}: {prompt}")
                response = client_gemini.models.generate_images(
                    model="imagen-3.0-generate-002",
                    prompt=prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        aspect_ratio="9:16",
                        personGeneration="ALLOW_ADULT"
                    )
                )
                
                if response and response.generated_images:
                    image_bytes = response.generated_images[0].image.image_bytes
                    del response  # Clean up response object
                    return image_bytes
                
                logging.warning("⚠️ Empty response from Gemini.")
            except Exception as e:
                logging.warning(f"❌ Gemini error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    wait = retry_delay * (2 ** attempt)
                    logging.info(f"⏳ Retrying in {wait} seconds...")
                    time.sleep(wait)
                continue
            
        logging.error("❌ Failed after all Gemini retries.")
        return None
    finally:
        if client_gemini:
            del client_gemini  # Ensure client is cleaned up


async def generate_image_gemini_async(prompt: str):
    """Async wrapper for Gemini image generation."""
    async with semaphore:
        await asyncio.sleep(rate_limit_delay)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: generate_image_gemini(prompt))


async def upload_image_gg_storage_async(image_bytes: bytes, bucket_name: str, prefix: str):
    """Upload image bytes to GCS and return public URL using optimized chunked streaming."""
    if not image_bytes:
        return PLACEHOLDER_ERROR_IMAGE

    client = None
    stream = None
    try:
        loop = asyncio.get_running_loop()
        client = storage.Client()
        bucket = client.bucket(bucket_name)

        if not await loop.run_in_executor(None, bucket.exists):
            logging.error(f"Bucket {bucket_name} does not exist.")
            return PLACEHOLDER_ERROR_IMAGE

        filename = f"{prefix}{uuid.uuid4()}.png"
        blob = bucket.blob(filename)

        # Optimize chunk size for better memory usage
        chunk_size = 2 * 1024 * 1024  # 2MB chunks for better throughput
        blob.chunk_size = chunk_size

        # Create a bytes stream from the image data with context management
        stream = BytesIO(image_bytes)
        del image_bytes  # Free original image bytes immediately

        # Upload with optimized settings
        await loop.run_in_executor(
            None,
            lambda: blob.upload_from_file(
                stream,
                content_type="image/png",
                size=stream.getbuffer().nbytes,
                num_retries=3,
                timeout=120  # Increased timeout for large files
            )
        )

        return blob.public_url
    except Exception as e:
        logging.error(f"❌ Upload error: {e}", exc_info=True)
        return PLACEHOLDER_ERROR_IMAGE
    finally:
        # Ensure all resources are properly cleaned up
        if stream:
            stream.close()
        if client:
            client.close()  # Close client connection
        # Force garbage collection for large objects
        gc.collect()


async def generate_and_upload_async(prompt: str, post_id: int, prefix: str = "gemini_image_", bucket_name: str = "bucket_nextcopy") -> str:
    """
    Generates an image from a prompt, uploads it to GCS, and returns the public URL.
    Returns a placeholder if generation or upload fails.
    """
    try:
        # Generate image with memory optimization
        image_bytes = await generate_image_gemini_async(prompt)
        if not image_bytes:
            logging.warning(f"⚠️ No image generated for prompt: {prompt}")
            return PLACEHOLDER_ERROR_IMAGE

        # Construct storage prefix
        storage_prefix = f"posts/{post_id}/gemini_image_"
        
        # Upload and get URL
        url = await upload_image_gg_storage_async(image_bytes, bucket_name, storage_prefix)
        del image_bytes  # Clean up image bytes after upload
        
        if url != PLACEHOLDER_ERROR_IMAGE:
            logging.info(f"✅ Image uploaded: {url}")
        return url
    except Exception as e:
        logging.error(f"❌ Error in generate_and_upload_async: {e}", exc_info=True)
        return PLACEHOLDER_ERROR_IMAGE
    finally:
        # Force cleanup of any remaining resources
        gc.collect()
