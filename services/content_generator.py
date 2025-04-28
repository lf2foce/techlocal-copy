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

def generate_theme_title_and_story(campaign_title: str, insight: str, description: str, target_customer:str):
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    # Generate response using Gemini API (synchronous version)
    response = client.models.generate_content(
        model='gemini-2.0-flash',  # Updated to newer model version
        contents=f"""
        f"Tạo 3 thương hiệu cho pages với các thông tin sau: \n\n"
            f"- Insight khách hàng: {insight}\n"
            f"- Đối tượng mục tiêu: {target_customer}\n\n"
            f"Yêu cầu cho mỗi thương hiệu:\n"
            f"- `title`: Tên thương hiệu.\n"
            f"- `story`: Câu chuyện thương hiệu (không quá dài).\n"
            f"- `content_plan`: Một kế hoạch nội dung gồm 4 danh sách:\n"
            f"  - `goals`: 5 mục tiêu nội dung.\n"
            f"  - `titles`: 5 tiêu đề bài viết.\n"
            f"  - `formats`: 5 định dạng nội dung (ví dụ: bài viết, infographic, video, v.v.).\n"
            f"  - `content_ideas`: 5 ý tưởng nội dung ngắn gọn.\n\n"
            f"Lưu ý:\n"
            f"- Mỗi danh sách (`goals`, `titles`, `formats`, `content_ideas`) phải có đúng **5 phần tử**, và phải tương ứng theo thứ tự.\n"
            f"- Các trường phải xuất ra đúng cấu trúc JSON.\n"
            f"- Viết toàn bộ nội dung bằng tiếng Việt.\n"
        """,
        config=types.GenerateContentConfig(
            response_mime_type='application/json',
            response_schema=ThemeGenerate,
            system_instruction=types.Part.from_text(text=f"{description}, kết quả trả ra bằng tiếng việt"),
        ),
    )
    
    # Extract the response
    print("Generated 5 themes with content plans based on user prompt.")
    
    # Extract the response
    print("Generated 5 themes based on user prompt.")
    content = json.loads(response.text)
    
    # Validate and parse the response using Pydantic
    themes_data = ThemeGenerate(**content)
    print(themes_data)
    # Convert list of themes to list of tuples using dot notation for Pydantic model attributes

    return [
        {
            "title": theme.title,
            "story": theme.story,
            "content_plan": theme.content_plan.model_dump()  # Return dict for database
        }
        for theme in themes_data.themes
    ]

class BlogPost(BaseModel):
    title: str
    content: str

async def generate_post_content(theme_title: str, theme_story: str, campaign_title: str, post_title: str) -> Dict[str, str]:
    """Generate a post content using Google Gemini API asynchronously."""
    print(f"🔄 Starting generation of post with title: '{post_title}' for theme: '{theme_title}'")
    start_time = time.time()
    try:
        # Initialize the client
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        
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
        print(f"✅ Completed post in {elapsed_time:.2f} seconds. Title: '{post_title}'")
        
        return {
            "title": post_title,
            "content": blog_post.content
        }
    except Exception as e:
        # Log the error but don't raise it to allow other posts to be generated
        elapsed_time = time.time() - start_time
        print(f"❌ Error generating post after {elapsed_time:.2f} seconds: {str(e)}")
        return {
            "title": post_title,
            "content": f"This post is based on theme: '{theme_title}'\n\n{theme_story}\n\nGenerated for campaign '{campaign_title}'."
        }

async def process_with_semaphore(theme_title: str, theme_story: str, campaign_title: str, content_plan: List[str]):
    # Increase concurrency with higher semaphore limit for parallel processing
    semaphore = asyncio.Semaphore(10)  # Increased from 5 to 10 for more concurrent tasks
    
    async def bounded_generate(post_title):
        async with semaphore:
            try:
                return await generate_post_content(
                    theme_title,
                    theme_story,
                    campaign_title,
                    post_title
                )
            except Exception as e:
                print(f"Error generating post with title '{post_title}': {str(e)}")
                return None
    
    # Create all tasks at once for maximum concurrency
    all_tasks = [bounded_generate(title) for title in content_plan]
    
    # Run all tasks concurrently
    print(f"🚀 Generating {len(content_plan)} posts concurrently...")
    results = await asyncio.gather(*all_tasks)
    
    # Filter out None results from failed generations
    valid_results = [r for r in results if r is not None]
    print(f"✅ Successfully generated {len(valid_results)} out of {len(content_plan)} posts")
    
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

async def generate_posts_from_theme(theme: DBTheme, db: Session, campaign_data: Dict[str, Any] = None) -> int:
    print(f"🚀 Bắt đầu tạo bài đăng cho chủ đề ID: {theme.id}")
    print('4')
    campaign = db.query(Campaign).filter(Campaign.id == theme.campaign_id).first()
    if not campaign:
        print(f"❌ Không tìm thấy chiến dịch cho chủ đề ID: {theme.id}")
        return 0

    try:
        # Enrich theme story with campaign data for better context
        enriched_story = theme.story
        print(type(enriched_story))
        
        # Chuyển đổi campaign_data từ chuỗi sang từ điển nếu cần
        if isinstance(campaign_data, str):
            try:
                campaign_data = json.loads(campaign_data)
            except json.JSONDecodeError:
                print(f"❌ Không thể phân tích cú pháp campaign_data")
                campaign_data = {}
        
        if campaign_data:
            print(5, type(campaign_data))
            brand_voice = campaign_data.get('brandVoice', '')
            key_messages = campaign_data.get('keyMessages', [])
            content_guidelines = campaign_data.get('contentGuidelines', '')
            
            # Append campaign data to theme story for richer context
            enriched_story = f"{theme.story}\n\nBrand Voice: {brand_voice}\n"
            if key_messages:
                enriched_story += f"Key Messages:\n" + "\n".join([f"- {msg}" for msg in key_messages]) + "\n"
            if content_guidelines:
                enriched_story += f"\nContent Guidelines:\n{content_guidelines}"
        
        # Xử lý content_plan
        content_plan = theme.content_plan
        if isinstance(content_plan, str):
            try:
                content_plan = json.loads(content_plan)
            except json.JSONDecodeError:
                print(f"❌ Không thể phân tích cú pháp content_plan cho chủ đề ID: {theme.id}")
                return 0
        print('3')
        # Trích xuất tiêu đề từ content_plan
        titles = content_plan.get('titles', [])
        if not titles:
            print(f"⚠️ Không có tiêu đề trong content_plan cho chủ đề ID: {theme.id}")
            return 0

        print(f"📊 Tạo {len(titles)} bài đăng cho chiến dịch: '{campaign.title}'")

        # Tạo bài đăng đồng thời bằng cách sử dụng tiêu đề từ content_plan
        posts = await process_with_semaphore(
            theme.title,
            enriched_story,
            campaign.title,
            titles
        )
        
        if not posts:
            return 0
            
        # Lưu bài đăng theo lô
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
            print(f"✅ Đã lưu lô {i//batch_size + 1} trong số {(len(posts) + batch_size - 1)//batch_size}")
        
        return len(posts)
        
    except Exception as e:
        print(f"Lỗi khi tạo bài đăng: {str(e)}")
        return 0


def approve_post(post_id: int, db: Session) -> ContentPost:
    post = db.query(ContentPost).filter(ContentPost.id == post_id).first()
    if not post:
        raise ValueError("Post not found")

    post.status = "approved" #"scheduled" "posted"
    db.commit()
    return post
