import os
import httpx
from dotenv import load_dotenv
from services.logger import logger

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")  # Set per-user in future
API_BASE = os.getenv("API_BASE", "http://localhost:8000")
BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Initialize base URL for API endpoints
base_url = API_BASE.rstrip('/')

# Shared utility function for making API requests
async def make_api_request(endpoint: str, method: str = 'get', data: dict = None):
    url = f"{base_url}/{endpoint}"
    logger.info(f"Attempting {method.upper()} request to {url}")
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0), follow_redirects=True) as client:
        try:
            if method.lower() == 'post':
                res = await client.post(url, json=data) if data else await client.post(url)
            else:
                res = await client.get(url)
            
            logger.info(f"API Response status: {res.status_code}")
            if res.history:
                logger.info(f"Request was redirected. Final URL: {res.url}")
            res.raise_for_status()
            return res.json()
        except httpx.ConnectTimeout:
            logger.error(f"Connection timeout while connecting to {url}")
            raise
        except httpx.ReadTimeout:
            logger.error("Read timeout while making API request")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code} error: {str(e)}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise

async def send_telegram_message(text: str, chat_id: str = CHAT_ID, reply_markup: dict = None):
    if not TELEGRAM_TOKEN or not chat_id:
        logger.warning("Telegram token or chat_id not set")
        return

    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
        try:
            data = {"chat_id": chat_id}
            if isinstance(text, dict) and "text" in text and "reply_markup" in text:
                data.update(text)
            else:
                data["text"] = text
                if reply_markup:
                    data["reply_markup"] = reply_markup
            response = await client.post(
                f"{BASE_URL}/sendMessage",
                json=data
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectTimeout:
            logger.error("Telegram connection timed out")
        except httpx.ReadTimeout:
            logger.error("Telegram response timed out")
        except httpx.TimeoutException:
            logger.error("Telegram request timed out")
        except httpx.HTTPError as e:
            logger.error(f"Telegram message failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        return None

# Command implementations
def start():
    welcome_msg = """👋 Welcome to the Campaign Bot! Here's your complete workflow guide:

1️⃣ Campaign Management:
/campaigns - List all your campaigns
/create_campaign - Create a new campaign

2️⃣ Theme Management:
/generate_themes <campaign_id> - Generate 5 unique themes for your campaign
/themes <campaign_id> - View all themes for your campaign
/select_theme <theme_id> - Choose a theme and start generating posts

3️⃣ Post Management:
/posts <campaign_id> - View all posts in your campaign
/view_post <post_id> - See the full content of a specific post
/redo_post <post_id> - Not happy with a post? Regenerate it!

📝 Example Commands:

1. Create a Campaign:
/create_campaign "Tech Launch 2024" 7 "software developers" "productivity boost" "Launch campaign for new developer tools"

2. Generate & Select Themes:
/generate_themes 123
/themes 123
/select_theme 456

3. Manage Posts:
/posts 123
/view_post 789
/redo_post 789

🔍 Command Format:
/create_campaign <title> <repeat_days> "<target_customer>" "<insight>" "<description>"

✨ Your posts will be automatically scheduled and published daily after approval.
"""
    logger.info(f"Sending welcome message with command examples")
    return welcome_msg

async def create_campaign(title, repeat_days, target_customer, insight, description):
    payload = {
        "title": title,
        "repeat_every_days": repeat_days,
        "target_customer": target_customer,
        "insight": insight,
        "description": description,
        "generation_mode": "pre-batch"
    }
    try:
        campaign = await make_api_request('campaigns/', 'post', payload)
        success_msg = f"✅ Campaign created! ID: {campaign['id']}"
        example_msg = "\n\nCreate another campaign using this format:\n/create_campaign <title> <repeat_days> \"<target_customer>\" \"<insight>\" \"<description>\""
        logger.info(f"Campaign created successfully with ID: {campaign['id']}")
        return success_msg + example_msg
    except Exception as e:
        error_msg = str(e)
        if isinstance(e, httpx.ConnectTimeout):
            return "❌ Failed to create campaign: Connection timeout. Please try again."
        elif isinstance(e, httpx.ReadTimeout):
            return "❌ Failed to create campaign: Server took too long to respond. Please try again."
        elif isinstance(e, httpx.HTTPStatusError):
            return f"❌ Failed to create campaign: Server returned {e.response.status_code} error. Please try again later."
        elif isinstance(e, httpx.RequestError):
            return "❌ Failed to create campaign: Network or connection error. Please check your connection."
        else:
            return "❌ Failed to create campaign: An unexpected error occurred. Please try again later."

async def list_campaigns():
    try:
        campaigns = await make_api_request('campaigns/')
        if not campaigns:
            return "📋 No campaigns found. Create one using /create_campaign"
        return "📋 Campaigns:\n" + "\n".join([f"{c['id']}: {c['title']}" for c in campaigns])
    except Exception as e:
        if isinstance(e, httpx.ConnectTimeout):
            return "❌ Failed to connect to campaigns API: Connection timeout. Please check if the API server is running."
        elif isinstance(e, httpx.ReadTimeout):
            return "❌ Failed to fetch campaigns: Server took too long to respond. Please try again."
        elif isinstance(e, httpx.HTTPStatusError):
            return f"❌ Failed to fetch campaigns: Server returned {e.response.status_code} error. Please try again later."
        elif isinstance(e, httpx.RequestError):
            return "❌ Failed to fetch campaigns: Network or connection error. Please check your connection."
        else:
            return "❌ Failed to fetch campaigns: An unexpected error occurred. Please try again later."

async def generate_themes(campaign_id):
    try:
        await make_api_request(f'themes/campaigns/{campaign_id}/generate_themes/', 'post')
        return f"🎯 5 themes generated for campaign {campaign_id}"
    except Exception as e:
        if isinstance(e, httpx.ConnectTimeout):
            return "❌ Failed to generate themes: Connection timeout. Please try again."
        elif isinstance(e, httpx.ReadTimeout):
            return "❌ Failed to generate themes: Server took too long to respond. Please try again."
        elif isinstance(e, httpx.HTTPStatusError):
            return f"❌ Failed to generate themes: Server returned {e.response.status_code} error. Please try again later."
        elif isinstance(e, httpx.RequestError):
            return "❌ Failed to generate themes: Network or connection error. Please check your connection."
        else:
            return "❌ Failed to generate themes: An unexpected error occurred. Please try again later."

async def list_themes(campaign_id):
    try:
        # First check if campaign exists
        try:
            await make_api_request(f'campaigns/{campaign_id}')
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return "⚠️ Campaign not found. Please check if the campaign ID exists."
            raise

        themes = await make_api_request(f'themes/campaigns/{campaign_id}/')
        if not themes:
            return "📋 No themes found. Use /generate_themes to create new themes."
        
        # Create inline keyboard markup with clear status indicators
        keyboard = {
            "inline_keyboard": [
                [{
                    "text": f"{t['title']} {'✅' if t.get('status') == 'selected' else '🔘'}",
                    "callback_data": f"select_theme_{t['id']}" if t.get('status') != 'selected' else 'theme_already_selected',
                }] for t in themes
            ]
        }
        
        return {
            "text": "📚 Choose a theme by clicking the button below:",
            "reply_markup": keyboard
        }
    except Exception as e:
        if isinstance(e, httpx.ConnectTimeout):
            return "❌ Failed to fetch themes: Connection timeout. Please try again."
        elif isinstance(e, httpx.ReadTimeout):
            return "❌ Failed to fetch themes: Server took too long to respond. Please try again."
        elif isinstance(e, httpx.HTTPStatusError):
            return f"❌ Failed to fetch themes: Server returned {e.response.status_code} error. Please try again later."
        elif isinstance(e, httpx.RequestError):
            return "❌ Failed to fetch themes: Network or connection error. Please check your connection."
        else:
            return "❌ Failed to fetch themes: An unexpected error occurred. Please try again later."

async def select_theme(theme_id):
    try:
        # First check if theme exists and get its details
        try:
            theme = await make_api_request(f'themes/{theme_id}/')
            if not theme:
                logger.error(f"Theme {theme_id} returned empty response")
                return "⚠️ Theme not found or invalid. Please check the theme ID and try again."
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error accessing theme {theme_id}: {e.response.status_code}")
            if e.response.status_code == 404:
                return "⚠️ Theme not found. Please check if the theme ID exists and try again."
            return f"⚠️ Server error: {e.response.status_code}. Please try again later."
        except Exception as e:
            logger.error(f"Unexpected error accessing theme {theme_id}: {e}")
            return "⚠️ Server error. Please try again later."
            
        # Get and validate campaign ID
        campaign_id = theme.get('campaign_id')
        if not campaign_id:
            logger.error(f"Theme {theme_id} has no campaign_id")
            return "⚠️ Invalid theme data. Campaign ID not found."
            
        # Check if any theme is already selected for this campaign
        try:
            campaign_themes = await make_api_request(f'themes/campaigns/{campaign_id}/')
            if not campaign_themes:
                logger.error(f"No themes found for campaign {campaign_id}")
                return "⚠️ No themes found for this campaign."
                
            for t in campaign_themes:
                if t.get('status') == 'selected':
                    logger.info(f"Theme {t.get('id')} is already selected for campaign {campaign_id}")
                    return f"⚠️ Theme is commited for this campaign, please generate new campaign"
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error checking campaign themes: {e}")
            return f"⚠️ Error checking campaign themes. Please try again later."
        except Exception as e:
            logger.error(f"Error checking campaign themes: {e}")
            return "⚠️ Unexpected error. Please try again later."
            
        # Check if this specific theme is already selected
        if theme.get('status') == 'selected':
            logger.info(f"Theme {theme_id} is already selected")
            return f"⚠️ Theme '{theme.get('title', 'Unknown')}' has already been selected."
            
        try:
            await make_api_request(f'themes/{theme_id}/select/', 'post')
            logger.info(f"Successfully selected theme {theme_id}")
            return f"✅ Theme '{theme.get('title', 'Unknown')}' has been selected successfully."
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error selecting theme {theme_id}: {e}")
            return f"⚠️ Failed to select theme. Please try again later."
        except Exception as e:
            logger.error(f"Error selecting theme {theme_id}: {e}")
            return "⚠️ Unexpected error selecting theme. Please try again later."
    except Exception as e:
        if isinstance(e, httpx.ConnectTimeout):
            return "❌ Failed to select theme: Connection timeout. Please try again."
        elif isinstance(e, httpx.ReadTimeout):
            return "❌ Failed to select theme: Server took too long to respond. Please try again."
        elif isinstance(e, httpx.HTTPStatusError):
            return f"❌ Failed to select theme: Server returned {e.response.status_code} error. Please try again later."
        elif isinstance(e, httpx.RequestError):
            return "❌ Failed to select theme: Network or connection error. Please check your connection."
        else:
            return "❌ Failed to select theme: An unexpected error occurred. Please try again later."

async def list_posts(campaign_id):
    try:
        posts = await make_api_request(f'content/campaigns/{campaign_id}/posts')
        if not posts:
            return "📋 No posts found yet. They will be generated after theme selection."
        return "📝 Posts:\n" + "\n".join([f"{p['id']}: {p['title']} ({p['status']})" for p in posts])
    except Exception as e:
        if isinstance(e, httpx.ConnectTimeout):
            return "❌ Failed to fetch posts: Connection timeout. Please try again."
        elif isinstance(e, httpx.ReadTimeout):
            return "❌ Failed to fetch posts: Server took too long to respond. Please try again."
        elif isinstance(e, httpx.HTTPStatusError):
            return f"❌ Failed to fetch posts: Server returned {e.response.status_code} error. Please try again later."
        elif isinstance(e, httpx.RequestError):
            return "❌ Failed to fetch posts: Network or connection error. Please check your connection."
        else:
            return "❌ Failed to fetch posts: An unexpected error occurred. Please try again later."

async def view_post(post_id):
    try:
        post = await make_api_request(f'content/posts/{post_id}')
        return f"📄 Post {post['id']}:\n{post['content']}\n\nStatus: {post['status']}"
    except Exception as e:
        if isinstance(e, httpx.ConnectTimeout):
            return "❌ Failed to fetch post: Connection timeout. Please try again."
        elif isinstance(e, httpx.ReadTimeout):
            return "❌ Failed to fetch post: Server took too long to respond. Please try again."
        elif isinstance(e, httpx.HTTPStatusError):
            return f"❌ Failed to fetch post: Server returned {e.response.status_code} error. Please try again later."
        elif isinstance(e, httpx.RequestError):
            return "❌ Failed to fetch post: Network or connection error. Please check your connection."
        else:
            return "❌ Failed to fetch post: An unexpected error occurred. Please try again later."

async def redo_post(post_id):
    try:
        await make_api_request(f'content/{post_id}/redo', 'post')
        # After successful regeneration, fetch and return the updated post content
        updated_post = await view_post(post_id)
        return f"🔁 Post {post_id} regenerated.\n\nUpdated content:\n{updated_post}"
    except Exception as e:
        if isinstance(e, httpx.ConnectTimeout):
            return "❌ Failed to regenerate post: Connection timeout. Please try again."
        elif isinstance(e, httpx.ReadTimeout):
            return "❌ Failed to regenerate post: Server took too long to respond. Please try again."
        elif isinstance(e, httpx.HTTPStatusError):
            return f"❌ Failed to regenerate post: Server returned {e.response.status_code} error. Please try again later."
        elif isinstance(e, httpx.RequestError):
            return "❌ Failed to regenerate post: Network or connection error. Please check your connection."
        else:
            return "❌ Failed to regenerate post: An unexpected error occurred. Please try again later."
