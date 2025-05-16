import urllib.parse
import logging
import requests
from typing import Optional

async def generate_and_upload_locaith(prompt: str, width: int = 576, height: int = 1024) -> Optional[str]:
    """Tạo và trả về URL ảnh từ Pollinations API.
    
    Args:
        prompt (str): Prompt để tạo ảnh
        
    Returns:
        Optional[str]: URL của ảnh đã tạo hoặc None nếu có lỗi
    """
    try:
        # Giới hạn độ dài prompt và mã hóa
        safe_prompt = prompt[:500]
        encoded_prompt = urllib.parse.quote(safe_prompt)

        # Tạo URL ảnh với custom dimensions
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?nologo=true&width={width}&height={height}"
        logging.info(f"🖼️ [Locaith] Ảnh đã sẵn sàng: '{safe_prompt[:60]}...'")
        logging.info(f"🔗 URL ảnh: {image_url}")
        # Shorten URL using TinyURL API
        try:
            tiny_url_api = f"http://tinyurl.com/api-create.php?url={urllib.parse.quote(image_url)}"
            response = requests.get(tiny_url_api)
            if response.status_code == 200:
                short_url = response.text
                logging.info(f"🖼️ [Locaith] Ảnh đã sẵn sàng: '{safe_prompt[:60]}...'")
                logging.info(f"🔗 URL ảnh (shortened): {short_url}")
                return short_url
            else:
                logging.warning(f"⚠️ [Locaith] Could not shorten URL, returning original")
                return image_url
        except Exception as e:
            logging.warning(f"⚠️ [Locaith] URL shortening failed: {e}, returning original")
            return image_url

    except Exception as e:
        logging.error(f"❌ [Locaith ERROR] Lỗi không xác định: {e}")
        return None