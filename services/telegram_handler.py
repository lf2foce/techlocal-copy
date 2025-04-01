import os
import httpx
from dotenv import load_dotenv
from services.logger import logger

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")  # Set per-user in future
API_BASE = os.getenv("API_BASE", "http://localhost:8000")

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


async def send_telegram_message(text: str, chat_id: str = CHAT_ID):
    if not TELEGRAM_TOKEN or not chat_id:
        logger.warning("Telegram token or chat_id not set")
        return

    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
        try:
            response = await client.post(
                f"{BASE_URL}/sendMessage",
                data={"chat_id": chat_id, "text": text}
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
    base_url = API_BASE.rstrip('/')
    endpoint = f"{base_url}/campaigns/"
    logger.info(f"Attempting to create campaign at {endpoint}")
    
    payload = {
        "title": title,
        "repeat_every_days": repeat_days,
        "target_customer": target_customer,
        "insight": insight,
        "description": description,
        "generation_mode": "pre-batch"
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0), follow_redirects=True) as client:
        try:
            res = await client.post(endpoint, json=payload)
            logger.info(f"API Response status: {res.status_code}")
            if res.history:
                logger.info(f"Request was redirected. Final URL: {res.url}")
            res.raise_for_status()
            campaign = res.json()
            success_msg = f"✅ Campaign created! ID: {campaign['id']}"
            example_msg = "\n\nCreate another campaign using this format:\n/create_campaign <title> <repeat_days> \"<target_customer>\" \"<insight>\" \"<description>\""
            logger.info(f"Campaign created successfully with ID: {campaign['id']}")
            return success_msg + example_msg
        except httpx.ConnectTimeout:
            logger.error(f"Connection timeout while connecting to {endpoint}")
            return "❌ Failed to create campaign: Connection timeout. Please try again."
        except httpx.ReadTimeout:
            logger.error("Read timeout while creating campaign")
            return "❌ Failed to create campaign: Server took too long to respond. Please try again."
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code} error while creating campaign: {str(e)}")
            return f"❌ Failed to create campaign: Server returned {e.response.status_code} error. Please try again later."
        except httpx.RequestError as e:
            logger.error(f"Request failed while creating campaign: {str(e)}")
            return "❌ Failed to create campaign: Network or connection error. Please check your connection."
        except Exception as e:
            logger.error(f"Unexpected error while creating campaign: {str(e)}")
            return "❌ Failed to create campaign: An unexpected error occurred. Please try again later."

async def list_campaigns():
    if not API_BASE:
        logger.error("API_BASE environment variable is not set")
        return "❌ Failed to fetch campaigns: API endpoint not configured. Please set API_BASE environment variable."

    # Ensure API_BASE doesn't end with a slash
    base_url = API_BASE.rstrip('/')
    endpoint = f"{base_url}/campaigns/"
    logger.info(f"Attempting to fetch campaigns from {endpoint}")

    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0), follow_redirects=True) as client:
        try:
            res = await client.get(endpoint)
            logger.info(f"API Response status: {res.status_code}")
            if res.history:
                logger.info(f"Request was redirected. Final URL: {res.url}")
            res.raise_for_status()
            campaigns = res.json()
            if not campaigns:
                return "📋 No campaigns found. Create one using /create_campaign"
            return "📋 Campaigns:\n" + "\n".join([f"{c['id']}: {c['title']}" for c in campaigns])
        except httpx.ConnectTimeout:
            logger.error(f"Connection timeout while connecting to {API_BASE}/campaigns")
            return "❌ Failed to connect to campaigns API: Connection timeout. Please check if the API server is running."
        except httpx.ReadTimeout:
            logger.error("Read timeout while fetching campaigns data")
            return "❌ Failed to fetch campaigns: Server took too long to respond. Please try again."
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code} error while fetching campaigns: {str(e)}")
            return f"❌ Failed to fetch campaigns: Server returned {e.response.status_code} error. Please try again later."
        except httpx.RequestError as e:
            logger.error(f"Request failed while fetching campaigns: {str(e)}")
            return "❌ Failed to fetch campaigns: Network or connection error. Please check your connection."
        except Exception as e:
            logger.error(f"Unexpected error while fetching campaigns: {str(e)}")
            return "❌ Failed to fetch campaigns: An unexpected error occurred. Please try again later."

async def generate_themes(campaign_id):
    base_url = API_BASE.rstrip('/')
    endpoint = f"{base_url}/themes/campaigns/{campaign_id}/generate_themes/"
    logger.info(f"Attempting to generate themes at {endpoint}")
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0), follow_redirects=True) as client:
        try:
            res = await client.post(endpoint)
            logger.info(f"API Response status: {res.status_code}")
            if res.history:
                logger.info(f"Request was redirected. Final URL: {res.url}")
            res.raise_for_status()
            return f"🎯 5 themes generated for campaign {campaign_id}"
        except httpx.ConnectTimeout:
            logger.error(f"Connection timeout while connecting to {endpoint}")
            return "❌ Failed to generate themes: Connection timeout. Please try again."
        except httpx.ReadTimeout:
            logger.error("Read timeout while generating themes")
            return "❌ Failed to generate themes: Server took too long to respond. Please try again."
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code} error while generating themes: {str(e)}")
            return f"❌ Failed to generate themes: Server returned {e.response.status_code} error. Please try again later."
        except httpx.RequestError as e:
            logger.error(f"Request failed while generating themes: {str(e)}")
            return "❌ Failed to generate themes: Network or connection error. Please check your connection."
        except Exception as e:
            logger.error(f"Unexpected error while generating themes: {str(e)}")
            return "❌ Failed to generate themes: An unexpected error occurred. Please try again later."

async def list_themes(campaign_id):
    base_url = API_BASE.rstrip('/')
    endpoint = f"{base_url}/themes/campaigns/{campaign_id}/"
    logger.info(f"Attempting to fetch themes from {endpoint}")
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0), follow_redirects=True) as client:
        try:
            res = await client.get(endpoint)
            logger.info(f"API Response status: {res.status_code}")
            if res.history:
                logger.info(f"Request was redirected. Final URL: {res.url}")
            res.raise_for_status()
            themes = res.json()
            if not themes:
                return "📋 No themes found. Generate some using /generate_themes"
            return "📚 Themes:\n" + "\n".join([f"{t['id']}: {t['title']}" for t in themes])
        except httpx.ConnectTimeout:
            logger.error(f"Connection timeout while connecting to {endpoint}")
            return "❌ Failed to fetch themes: Connection timeout. Please try again."
        except httpx.ReadTimeout:
            logger.error("Read timeout while fetching themes")
            return "❌ Failed to fetch themes: Server took too long to respond. Please try again."
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code} error while fetching themes: {str(e)}")
            return f"❌ Failed to fetch themes: Server returned {e.response.status_code} error. Please try again later."
        except httpx.RequestError as e:
            logger.error(f"Request failed while fetching themes: {str(e)}")
            return "❌ Failed to fetch themes: Network or connection error. Please check your connection."
        except Exception as e:
            logger.error(f"Unexpected error while fetching themes: {str(e)}")
            return "❌ Failed to fetch themes: An unexpected error occurred. Please try again later."

async def select_theme(theme_id):
    base_url = API_BASE.rstrip('/')
    endpoint = f"{base_url}/themes/{theme_id}/select/"
    logger.info(f"Attempting to select theme at {endpoint}")
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0), follow_redirects=True) as client:
        try:
            res = await client.post(endpoint)
            logger.info(f"API Response status: {res.status_code}")
            if res.history:
                logger.info(f"Request was redirected. Final URL: {res.url}")
            res.raise_for_status()
            return f"✅ Theme {theme_id} selected and posts are being generated."
        except httpx.ConnectTimeout:
            logger.error(f"Connection timeout while connecting to {endpoint}")
            return "❌ Failed to select theme: Connection timeout. Please try again."
        except httpx.ReadTimeout:
            logger.error("Read timeout while selecting theme")
            return "❌ Failed to select theme: Server took too long to respond. Please try again."
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code} error while selecting theme: {str(e)}")
            return f"❌ Failed to select theme: Server returned {e.response.status_code} error. Please try again later."
        except httpx.RequestError as e:
            logger.error(f"Request failed while selecting theme: {str(e)}")
            return "❌ Failed to select theme: Network or connection error. Please check your connection."
        except Exception as e:
            logger.error(f"Unexpected error while selecting theme: {str(e)}")
            return "❌ Failed to select theme: An unexpected error occurred. Please try again later."

async def list_posts(campaign_id):
    base_url = API_BASE.rstrip('/')
    endpoint = f"{base_url}/content/campaigns/{campaign_id}/posts"
    logger.info(f"Attempting to fetch posts from {endpoint}")
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0), follow_redirects=True) as client:
        try:
            res = await client.get(endpoint)
            logger.info(f"API Response status: {res.status_code}")
            if res.history:
                logger.info(f"Request was redirected. Final URL: {res.url}")
            res.raise_for_status()
            posts = res.json()
            if not posts:
                return "📋 No posts found yet. They will be generated after theme selection."
            return "📝 Posts:\n" + "\n".join([f"{p['id']}: {p['title']} ({p['status']})" for p in posts])
        except httpx.ConnectTimeout:
            logger.error(f"Connection timeout while connecting to {endpoint}")
            return "❌ Failed to fetch posts: Connection timeout. Please try again."
        except httpx.ReadTimeout:
            logger.error("Read timeout while fetching posts")
            return "❌ Failed to fetch posts: Server took too long to respond. Please try again."
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code} error while fetching posts: {str(e)}")
            return f"❌ Failed to fetch posts: Server returned {e.response.status_code} error. Please try again later."
        except httpx.RequestError as e:
            logger.error(f"Request failed while fetching posts: {str(e)}")
            return "❌ Failed to fetch posts: Network or connection error. Please check your connection."
        except Exception as e:
            logger.error(f"Unexpected error while fetching posts: {str(e)}")
            return "❌ Failed to fetch posts: An unexpected error occurred. Please try again later."

async def view_post(post_id):
    base_url = API_BASE.rstrip('/')
    endpoint = f"{base_url}/content/posts/{post_id}"
    logger.info(f"Attempting to fetch post from {endpoint}")
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0), follow_redirects=True) as client:
        try:
            res = await client.get(endpoint)
            logger.info(f"API Response status: {res.status_code}")
            if res.history:
                logger.info(f"Request was redirected. Final URL: {res.url}")
            res.raise_for_status()
            post = res.json()
            return f"📄 Post {post['id']}:\n{post['content']}\n\nStatus: {post['status']}"
        except httpx.ConnectTimeout:
            logger.error(f"Connection timeout while connecting to {endpoint}")
            return "❌ Failed to fetch post: Connection timeout. Please try again."
        except httpx.ReadTimeout:
            logger.error("Read timeout while fetching post data")
            return "❌ Failed to fetch post: Server took too long to respond. Please try again."
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code} error while fetching post: {str(e)}")
            return f"❌ Failed to fetch post: Server returned {e.response.status_code} error. Please try again later."
        except httpx.RequestError as e:
            logger.error(f"Request failed while fetching post: {str(e)}")
            return "❌ Failed to fetch post: Network or connection error. Please check your connection."
        except Exception as e:
            logger.error(f"Unexpected error while fetching post: {str(e)}")
            return "❌ Failed to fetch post: An unexpected error occurred. Please try again later."

async def redo_post(post_id):
    base_url = API_BASE.rstrip('/')
    endpoint = f"{base_url}/content/{post_id}/redo"
    logger.info(f"Attempting to regenerate post at {endpoint}")
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0), follow_redirects=True) as client:
        try:
            res = await client.post(endpoint)
            logger.info(f"API Response status: {res.status_code}")
            if res.history:
                logger.info(f"Request was redirected. Final URL: {res.url}")
            res.raise_for_status()
            return f"🔁 Post {post_id} regenerated."
        except httpx.ConnectTimeout:
            logger.error(f"Connection timeout while connecting to {endpoint}")
            return "❌ Failed to regenerate post: Connection timeout. Please try again."
        except httpx.ReadTimeout:
            logger.error("Read timeout while regenerating post")
            return "❌ Failed to regenerate post: Server took too long to respond. Please try again."
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code} error while regenerating post: {str(e)}")
            return f"❌ Failed to regenerate post: Server returned {e.response.status_code} error. Please try again later."
        except httpx.RequestError as e:
            logger.error(f"Request failed while regenerating post: {str(e)}")
            return "❌ Failed to regenerate post: Network or connection error. Please check your connection."
        except Exception as e:
            logger.error(f"Unexpected error while regenerating post: {str(e)}")
            return "❌ Failed to regenerate post: An unexpected error occurred. Please try again later."
