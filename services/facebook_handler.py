from typing import Optional
import requests
import os
from dotenv import load_dotenv
from fastapi import HTTPException
from services.telegram_handler import send_telegram_message

load_dotenv()

def post_to_facebook(content: str, campaign_title: Optional[str] = None) -> bool:
    """
    Posts content to Facebook page
    
    Args:
        content: The post content to publish
        campaign_title: Optional campaign title for error messages
    
    Returns:
        bool: True if post succeeded, False otherwise
    """
    try:
        PAGE_ID = os.getenv('FACEBOOK_PAGE_ID')
        PAGE_ACCESS_TOKEN = os.getenv('FACEBOOK_PAGE_ACCESS_TOKEN')
        if not PAGE_ID or not PAGE_ACCESS_TOKEN:
            raise ValueError("Facebook credentials not configured")
        
        url = f'https://graph.facebook.com/v18.0/{PAGE_ID}/feed'
        payload = {
            'message': content,
            'access_token': PAGE_ACCESS_TOKEN
        }
        
        response = requests.post(url, data=payload)
        
        if response.status_code == 200:
            if campaign_title:
                send_telegram_message(
                    f"📢 Post from campaign '{campaign_title}' sent to Facebook!\n\n{content}"
                )
            return True
        else:
            error_msg = f"❌ Failed to post to Facebook"
            if campaign_title:
                error_msg += f" for campaign '{campaign_title}'"
            error_msg += f": {response.text}"
            send_telegram_message(error_msg)
            return False
    except Exception as e:
        error_msg = f"❌ Error posting to Facebook"
        if campaign_title:
            error_msg += f" for campaign '{campaign_title}'"
        error_msg += f": {str(e)}"
        send_telegram_message(error_msg)
        return False