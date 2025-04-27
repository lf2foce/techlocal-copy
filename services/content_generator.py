import random
from sqlalchemy.orm import Session
from database.models import ContentPost, Campaign, Theme as DBTheme
from datetime import datetime, timedelta
from typing import Dict, Any, List
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

class Theme(BaseModel):
    title: str
    story: str

class ThemeGenerate(BaseModel):
    themes: List[Theme]

def generate_theme_title_and_story(campaign_title: str, insight: str, description: str, target_customer:str) -> List[tuple[str, str]]:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    # Generate response using Gemini API (synchronous version)
    response = client.models.generate_content(
        model='gemini-2.0-flash',  # Updated to newer model version
        contents=f"Tạo 5 thương hiệu cho pages với các thông tin {insight} {target_customer}. Mỗi thương hiệu phải có title và story khác nhau, trong story ngoài câu chuyện thương hiệu hãy thêm nội dung kế hoạch cho 5 tiêu đề của 5 bài viết. Viết bằng tiếng việt",
        config=types.GenerateContentConfig(
            response_mime_type='application/json',
            response_schema=ThemeGenerate,
            system_instruction=types.Part.from_text(text=f"{description}, kết quả trả ra bằng tiếng việt"),
        ),
    )
    
    # Extract the response
    print("Generated 5 themes based on user prompt.")
    content = json.loads(response.text)
    
    # Validate and parse the response using Pydantic
    themes_data = ThemeGenerate(**content)
    
    # Convert list of themes to list of tuples using dot notation for Pydantic model attributes
    return [(theme.title, theme.story) for theme in themes_data.themes]

class BlogPost(BaseModel):
    title: str
    content: str

async def generate_post_content(theme_title: str, theme_story: str, campaign_title: str, post_number: int) -> Dict[str, str]:
    """Generate a post content using Google Gemini API asynchronously."""
    print(f"🔄 Starting generation of post {post_number} for theme: '{theme_title}'")
    start_time = time.time()
    try:
        # Initialize the client
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        
        # Create the prompt with theme context
        # prompt = f"Write a blog post based on this theme: '{theme_title}'. Theme story: {theme_story}. This is post {post_number} in the campaign '{campaign_title}'."
        
        prompt = (
                f"Dựa vào tên thương hiệu '{theme_title}', mô tả kênh, và yêu cầu cụ thể cho ngày hôm nay, hãy viết một bài đăng dạng kể chuyện (storytelling post) bằng tiếng Việt.\n\n"
                f"--- TÊN THƯƠNG HIỆU ---\n{theme_title}\n\n"
                f"--- MÔ TẢ KÊNH (Từ người dùng) ---\n{theme_story}\n--- KẾT THÚC MÔ TẢ ---\n\n"              
        
                f"- Mục tiêu: Kết nối sâu sắc, chia sẻ góc nhìn/kinh nghiệm/giải pháp liên quan đến insight.\n"
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
            5. Generating EXACTLY {num_images} relevant ENGLISH image prompts AND brief VIETNAMESE explanations for them, suitable for text-to-image AI, aligned with the flow of a given post's content and the overall campaign knowledge.
            6. Generating ENGLISH image prompts for a social media avatar and cover photo, based on a brand name and campaign concept, along with brief VIETNAMESE explanations for each.
            CRITICAL: Always use the provided CAMPAIGN KNOWLEDGE/CONTEXT when generating content.
            Adhere strictly to the JSON output format when requested (names, schedule, evaluation, post, image prompts+explanation, avatar/cover prompts).
            Output ONLY the valid JSON object without surrounding text or markdown.
            Language: Primarily Vietnamese, except for the English image prompt.
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
        
      
        
        elapsed_time = time.time() - start_time
        print(f"✅ Completed post {post_number} in {elapsed_time:.2f} seconds. Title: '{blog_post.title}'")
        
        return {
            "title": blog_post.title,
            "content": blog_post.content
        }
    except Exception as e:
        # Log the error but don't raise it to allow other posts to be generated
        elapsed_time = time.time() - start_time
        print(f"❌ Error generating post {post_number} after {elapsed_time:.2f} seconds: {str(e)}")
        return {
            "title": f"Post {post_number} - {theme_title}",
            "content": f"This post is based on theme: '{theme_title}'\n\n{theme_story}\n\nGenerated item {post_number} in the campaign '{campaign_title}'."
        }

async def process_with_semaphore(theme_title: str, theme_story: str, campaign_title: str, num_posts: int):
    # Increase concurrency with higher semaphore limit for parallel processing
    semaphore = asyncio.Semaphore(10)  # Increased from 5 to 10 for more concurrent tasks
    
    async def bounded_generate(post_number):
        async with semaphore:
            try:
                return await generate_post_content(
                    theme_title,
                    theme_story,
                    campaign_title,
                    post_number
                )
            except Exception as e:
                print(f"Error generating post {post_number}: {str(e)}")
                return None
    
    # Create all tasks at once for maximum concurrency
    all_tasks = [bounded_generate(i) for i in range(num_posts)]
    
    # Run all tasks concurrently
    print(f"🚀 Generating {num_posts} posts concurrently...")
    results = await asyncio.gather(*all_tasks)
    
    # Filter out None results from failed generations
    valid_results = [r for r in results if r is not None]
    print(f"✅ Successfully generated {len(valid_results)} out of {num_posts} posts")
    
    return valid_results

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
            image_status="pending"
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

async def generate_posts_from_theme(theme: DBTheme, db: Session) -> int:
    print(f"🚀 Starting post generation for theme ID: {theme.id}")
    
    campaign = db.query(Campaign).filter(Campaign.id == theme.campaign_id).first()
    if not campaign:
        print(f"❌ Campaign not found for theme ID: {theme.id}")
        return 0

    num_posts = campaign.repeat_every_days
    print(f"📊 Generating {num_posts} posts for campaign: '{campaign.title}'")
    
    try:
        # Generate posts concurrently in batches
        posts = await process_with_semaphore(
            theme.title,
            theme.story,
            campaign.title,
            num_posts
        )
        
        if not posts:
            return 0
            
        # Save posts in batches
        batch_size = 10
        for i in range(0, len(posts), batch_size):
            batch = posts[i:i + batch_size]
            for post_data in batch:
                post = ContentPost(
                    campaign_id=campaign.id,
                    theme_id=theme.id,
                    title=post_data["title"],
                    content=post_data["content"],
                    image_status="pending"
                )
                db.add(post)
            db.commit()
            print(f"✅ Saved batch {i//batch_size + 1} of {(len(posts) + batch_size - 1)//batch_size}")
        
        return len(posts)
        
    except Exception as e:
        print(f"Error generating posts: {str(e)}")
        return 0


def approve_post(post_id: int, db: Session) -> ContentPost:
    post = db.query(ContentPost).filter(ContentPost.id == post_id).first()
    if not post:
        raise ValueError("Post not found")

    post.status = "approved" #"scheduled" "posted"
    db.commit()
    return post
