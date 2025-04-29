import random
from sqlalchemy.orm import Session
from database.models import ContentPost, Campaign, Theme as DBTheme
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, ValidationError
from google import genai
from google.genai import types
import json
import time
import os
import random
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel
from schemas import Plan, ThemeBase
import asyncio

load_dotenv()

# def generate_theme_title_and_story(campaign_title: str, insight: str) -> tuple[str, str]:
#     title_templates = [
#         "The Power of {keyword}",
#         "Mastering {keyword} for Growth",
#         "Why {keyword} Matters Now",
#         "{keyword}: A New Approach",
#         "Unlocking {keyword}"
#     ]

#     insight_keywords = insight.split()
#     keyword = random.choice(insight_keywords if insight_keywords else ["change"])
#     title = random.choice(title_templates).format(keyword=keyword.capitalize())

#     story = f"This theme explores how '{keyword}' relates to {campaign_title.lower()}. We’ll break down why this is crucial and how to apply it practically."
#     return title, story



# class Theme(BaseModel):
#     title: str
#     story: str
#     content_plan: List[Plan]


class ThemeGenerate(BaseModel):
    themes: List[ThemeBase]

def generate_theme_title_and_story(campaign_title: str, insight: str, description: str, target_customer:str, post_num: int):
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    system_prompt=f""" Tạo 3 thương hiệu cho pages với các thông tin {insight} {target_customer}. 
    Mỗi thương hiệu phải có title và story khác nhau, và content_plan theo chiến lược từ {description} 
    content_plan nội dung kế hoạch cho {post_num} nội dung. 
    Viết bằng tiếng việt
        """
    # Generate response using Gemini API (synchronous version)
    response = client.models.generate_content(
        model='gemini-2.0-flash',  # Updated to newer model version
        contents=f"Viết cho tôi nội dung cho 3 thương hiệu chiến lược dựa trên {description}",
        config=types.GenerateContentConfig(
            response_mime_type='application/json',
            response_schema=ThemeGenerate,
            system_instruction=types.Part.from_text(text=system_prompt),
        ),
    )
    
    # Extract the response
    print("Generated 3 themes with content plans based on user prompt.")

    content = json.loads(response.text)
    
    # Validate and parse the response using Pydantic
    themes_data = ThemeGenerate(**content)
    print(themes_data)
    # Convert list of themes to list of tuples using dot notation for Pydantic model attributes

    return [
        {
            "title": theme.title,
            "story": theme.story,
            "content_plan": theme.content_plan.model_dump()
        }
        for theme in themes_data.themes
    ]

from schemas import PostMetadata
class BlogPost(BaseModel):
    title: str
    content: str

async def generate_post_content(theme_title: str, theme_story: str, campaign_title: str, content_plan: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a post content using Google Gemini API asynchronously."""
    print(f"🔄 Starting generation of post with title: '{content_plan.get('title')}' for theme: '{theme_title}'")
    start_time = time.time()
    try:
        # Initialize the client
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        
        # Extract content plan metadata
        goal = content_plan.get('goal')
        format_type = content_plan.get('format')
        content_idea = content_plan.get('content_idea')
        print(content_idea)
        post_title = content_plan.get('title')
        
        prompt = (
                f"Dựa vào tên thương hiệu '{theme_title}', mô tả kênh, và yêu cầu cụ thể cho ngày hôm nay, hãy viết một bài đăng dạng {format_type} bằng tiếng Việt.\n\n"
                f"--- TÊN THƯƠNG HIỆU ---\n{theme_title}\n\n"
                f"--- MÔ TẢ KÊNH ---\n{theme_story}\n\n"
                f"--- MỤC TIÊU BÀI VIẾT ---\n{goal}\n\n"
                f"--- Ý TƯỞNG NỘI DUNG ---\n{content_idea}\n\n"
                f"--- YÊU CẦU ---\n"
                f"- Giọng văn: Gần gũi, chân thật, đồng cảm, truyền cảm hứng. Có thể thêm hài hước/suy tư tùy chủ đề.\n"
                f"- Cấu trúc: Mở đầu thu hút, thân phát triển ý, kết bài ý nghĩa.\n"
                f"- Kết bài: Khuyến khích tương tác (câu hỏi mở) hoặc đưa ra lời khích lệ/hành động nhỏ.\n"
                f"- QUAN TRỌNG: Sử dụng emoji (VD: 💡🤔💪❤️🙏😢📈🤝🌟✨) phù hợp, tự nhiên để tăng biểu cảm. Đừng lạm dụng.\n\n"
                "Output: ONLY a valid JSON object with a single key 'post_content' containing the full Vietnamese post as a single string."
            )

        # System prompt for content generation
        system_prompt = """
        You are an expert AI assistant specializing in creating social media content and assets based on provided campaign knowledge and specific instructions. Your tasks include:
            1. Generating creative Vietnamese brand names relevant to the campaign context.
            2. Creating content schedules (Vietnamese topics/quotes) aligned with the campaign strategy for a specified number of days.
            3. Writing full Vietnamese storytelling posts reflecting the campaign's tone, themes, and target audience, using the provided context for a specific day.
            4. Evaluating and improving posts based on relevance, insight, value, emotion, tone, emoji use, and call to action.
            Output ONLY the valid JSON object without surrounding text or markdown.
            Language: Primarily Vietnamese
        """
        
        # Generate response using Gemini API
        response = client.models.generate_content(
            # model='gemini-2.5-flash-preview-04-17',  # Updated model version
            model='gemini-2.0-flash',  # Updated model version
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': BlogPost,
                'system_instruction': types.Part.from_text(text=system_prompt),
            },
        )
        
        # Inside generate_post_content function
        # Extract and parse the response
        content = json.loads(response.text)
        blog_post = BlogPost(**content)
       
        # Tạo metadata cho bài viết
        post_metadata = PostMetadata(
            content_type=content_plan.get('format'),
            content_ideas=content_plan.get('content_idea'),
            goals=content_plan.get('goal'),
            content_length=len(blog_post.content)
        )
        
        elapsed_time = time.time() - start_time
        print(f"✅ Completed post in {elapsed_time:.2f} seconds. Title: '{post_title}'")
        
        return {
            "title": blog_post.title,
            "content": blog_post.content,
            "post_metadata": post_metadata.model_dump()
        }
    except Exception as e:
        # Log the error but don't raise it to allow other posts to be generated
        elapsed_time = time.time() - start_time
        print(f"❌ Error generating post after {elapsed_time:.2f} seconds: {str(e)}")
        return {
            "title": content_plan.get('title'),
            "content": f"This post is based on theme: '{theme_title}'\n\n{theme_story}\n\nGenerated for campaign '{campaign_title}'.",
            "post_metadata": None
        }

async def create_default_content_plan(theme_title: str, theme_story: str, num_posts=5) -> Dict[str, Any]:
    """Tạo content plan mặc định khi không có plan được cung cấp"""
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    prompt = f"""
    Tạo kế hoạch nội dung cho chủ đề '{theme_title}' với {num_posts} bài viết.
    Mô tả chủ đề: {theme_story}
    Mỗi bài viết cần có:
    - goal: Mục tiêu nội dung
    - title: Tiêu đề bài viết 
    - format: Định dạng (bài viết/infographic/video)
    - content_idea: Ý tưởng nội dung ngắn
    """
    
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt,
        config={
            'response_mime_type': 'application/json',
            'response_schema': Plan
        }
    )
    
    content = json.loads(response.text)
    return content.model_dump()

async def process_with_semaphore(theme_title: str, theme_story: str, campaign_title: str, content_plan: Optional[Dict[str, Any]] = None):
    # Create a semaphore to limit concurrent API calls
    semaphore = asyncio.Semaphore(10)  # Limit to 10 concurrent API calls
    
    # Ensure content_plan is properly formatted
    if content_plan is None:
        print("⚠️ No content plan provided, creating default")
        content_plan = await create_default_content_plan(theme_title, theme_story)
    
    # Handle string content_plan
    if isinstance(content_plan, str):
        try:
            content_plan = json.loads(content_plan)
        except json.JSONDecodeError:
            print("❌ Could not parse content_plan JSON string")
            return []
    
    # Validate content_plan structure
    if not isinstance(content_plan, dict) or 'items' not in content_plan:
        print("❌ Invalid content plan format or missing 'items' field")
        return []
    
    content_items = content_plan['items']
    if not isinstance(content_items, list) or not content_items:
        print("❌ Content items must be a non-empty list")
        return []
    
    # Define the bounded task that will respect the semaphore
    async def bounded_task(item):
        # This critical section ensures only 10 tasks can execute this block concurrently
        async with semaphore:
            print(f"🔄 Starting generation for item: '{item.get('title')}'")
            try:
                return await generate_post_content(
                    theme_title,
                    theme_story,
                    campaign_title,
                    item
                )
            except Exception as e:
                print(f"❌ Error generating post for '{item.get('title')}': {str(e)}")
                return None
    
    # Create tasks for all content items
    tasks = [bounded_task(item) for item in content_items]
    
    # Execute all tasks concurrently with gather, this is the correct way
    print(f"🚀 Generating {len(tasks)} posts concurrently with max {semaphore._value} at a time")
    start_time = time.time()
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - start_time
    
    # Filter out failed generations and log statistics
    valid_results = [r for r in results if r is not None]
    print(f"✅ Generated {len(valid_results)}/{len(tasks)} posts in {elapsed:.2f}s")
    
    return valid_results


#func test
def save_posts_to_db(post_contents, campaign_id, theme_id, db):
    """Create posts in the database using optimized bulk insert."""
    if not post_contents:
        print("⚠️ No post contents provided to save")
        return 0
        
    now = datetime.now()
    total_posts = len(post_contents)
    print(f"🔄 Preparing to save {total_posts} posts to database")
    
    # Prepare all posts for bulk insert with minimal object creation overhead
    posts_to_insert = [
        ContentPost(
            campaign_id=campaign_id,
            theme_id=theme_id,
            title=post.get("title", f"Post {i}"),
            content=post.get("content", ""),
            status="approved",
            created_at=now + timedelta(microseconds=i),
            image_status="pending",
            post_metadata=post.get("post_metadata")
        )
        for i, post in enumerate(post_contents)
        if isinstance(post, dict) and post.get("content")
    ]
    
    if not posts_to_insert:
        print("❌ No valid posts to insert")
        return 0
    
    try:
        # Execute bulk insert and campaign update in a single transaction
        db.bulk_save_objects(posts_to_insert)
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if campaign:
            campaign.current_step = 4
        db.commit()
        
        created_count = len(posts_to_insert)
        print(f"✅ Successfully saved {created_count}/{total_posts} posts to database")
        return created_count
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error during bulk save operation: {str(e)}")
        return 0

async def generate_posts_from_theme(theme: DBTheme, db_factory, campaign_data: Dict[str, Any] = None) -> int:
    """Generate posts for a theme using concurrent processing with separate DB sessions"""
    print(f"🚀 Starting post generation for theme ID: {theme.id}")
    
    # Use a separate DB session for the main function
    with db_factory() as db:
        campaign = db.query(Campaign).filter(Campaign.id == theme.campaign_id).first()
        if not campaign:
            print(f"❌ Campaign not found for theme ID: {theme.id}")
            return 0
        
        # Create enriched story with campaign data
        enriched_story = theme.story
        
        # Parse campaign_data if needed
        if isinstance(campaign_data, str):
            try:
                campaign_data = json.loads(campaign_data)
            except json.JSONDecodeError:
                print("❌ Failed to parse campaign_data")
                campaign_data = {}
        
        # Enrich the theme story with campaign context
        if campaign_data:
            brand_voice = campaign_data.get('brandVoice', '')
            key_messages = campaign_data.get('keyMessages', [])
            content_guidelines = campaign_data.get('contentGuidelines', '')
            
            enriched_story = f"{theme.story}\n\nBrand Voice: {brand_voice}\n"
            if key_messages:
                enriched_story += f"Key Messages:\n" + "\n".join([f"- {msg}" for msg in key_messages]) + "\n"
            if content_guidelines:
                enriched_story += f"\nContent Guidelines:\n{content_guidelines}"
        
        # Process content_plan
        content_plan = theme.content_plan
        if isinstance(content_plan, str):
            try:
                content_plan = json.loads(content_plan)
            except json.JSONDecodeError:
                print(f"❌ Failed to parse content_plan JSON for theme {theme.id}")
                content_plan = None
    
    # Generate posts concurrently - note we're outside the DB session now
    posts = await process_with_semaphore(
        theme.title,
        enriched_story,
        campaign.title,
        content_plan
    )
    
    if not posts:
        print("❌ No posts were generated")
        return 0
    
    # Use a separate DB session for saving results
    with db_factory() as db:
        # Save posts in batches
        total_saved = 0
        batch_size = 10
        for i in range(0, len(posts), batch_size):
            batch = posts[i:i + batch_size]
            batch_posts = []
            
            for post_data in batch:
                post = ContentPost(
                    campaign_id=theme.campaign_id,
                    theme_id=theme.id,
                    title=post_data["title"],
                    content=post_data["content"],
                    post_metadata=post_data.get("post_metadata", ""),
                    status="approved",
                    image_status="pending"
                )
                batch_posts.append(post)
            
            try:
                # Use bulk_save_objects for efficient batch saving
                db.bulk_save_objects(batch_posts)
                db.commit()
                total_saved += len(batch_posts)
                print(f"✅ Saved batch {i//batch_size + 1}/{(len(posts) + batch_size - 1)//batch_size} ({len(batch_posts)} posts)")
            except Exception as e:
                db.rollback()
                print(f"❌ Error saving batch: {str(e)}")
        
        return total_saved


def approve_post(post_id: int, db: Session) -> ContentPost:
    post = db.query(ContentPost).filter(ContentPost.id == post_id).first()
    if not post:
        raise ValueError("Post not found")

    post.status = "approved" #"scheduled" "posted"
    db.commit()
    return post
