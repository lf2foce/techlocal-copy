import os
import asyncio
import requests
from dotenv import load_dotenv

load_dotenv()

async def generate_and_upload_ideogram(
    prompt: str, 
    aspect_ratio: str = "ASPECT_9_16"
):
    try:
        url = "https://api.ideogram.ai/generate"
        headers = {
            "Api-Key": os.getenv("IDEO_API_KEY"),
            "Content-Type": "application/json"
        }
        
        payload = {
            "image_request": {
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "model": "V_2_TURBO",
                "magic_prompt_option": "AUTO"
            }
        }

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        response_data = response.json()
        
        # Handle direct image URL response
        if 'data' in response_data and isinstance(response_data['data'], list):
            for item in response_data['data']:
                if item.get('url'):
                    return item['url']
        
        raise ValueError(f"No image URL found in response: {response_data}")

    except Exception as e:
        print(f"Error generating image: {str(e)}")
        return None
