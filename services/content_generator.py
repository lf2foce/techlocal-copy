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


#    5. `tone`: Giọng văn gợi ý (VD: “êm dịu”, “gần gũi”, “chuyên nghiệp”)
#     6. `emotion`: Cảm xúc chủ đạo của chiến lược (VD: “Đồng cảm”, “Say mê”, “Khao khát”)
#     7. `keywords`: Các từ khóa chính gợi ý cho nội dung
#     8. `strategy_mix`: Các hướng triển khai nội dung (VD: ["Inspire", "Educate"])
#     9. `angle_mix`: Cách thể hiện bài viết (VD: ["Story", "How-to", "Listicle"])
#     10. `hook_suggestions`: Các câu mở đầu bài viết gợi cảm xúc

class ThemeGenerate(BaseModel):
    themes: List[ThemeBase]

async def generate_single_theme(client, description: str, insight: str, target_customer: str, post_num: int, content_type: str = "Auto", used_strategies: set = None) -> ThemeBase:
    """Generate a single theme using Gemini API"""
    # Định nghĩa danh sách format mặc định khi content_type là Auto
   

    # Định nghĩa danh sách chiến lược
    strategy_list = [
        "Đồng cảm (Empathy): Kết nối sâu sắc với nỗi đau hoặc trải nghiệm người dùng.",
        "Khao khát (Desire): Gợi mở điều người đọc muốn đạt tới, nâng cấp cuộc sống.",
        "Hào hứng (Excitement): Tạo sự tò mò, năng lượng cao, truyền động lực hành động.",
        "Say mê / Truyền cảm hứng (Inspiration): Gợi lên khát vọng sống ý nghĩa, vượt qua giới hạn.",
        "Lo sợ / Urgency: Gây cảm giác cần thay đổi ngay, nhấn mạnh hậu quả hoặc mất mát."
    ]
    
    
    # Lọc ra các chiến lược chưa được sử dụng
    available_strategies = strategy_list.copy()
    if used_strategies:
        available_strategies = [s for s in strategy_list if s not in used_strategies]
    
    # Nếu đã hết chiến lược mới, reset lại danh sách
    if not available_strategies:
        available_strategies = strategy_list.copy()
    
    # Chọn ngẫu nhiên một chiến lược từ các chiến lược còn lại
    selected_strategy = random.choice(available_strategies)
    
    # Thêm chiến lược đã chọn vào set đã sử dụng
    if used_strategies is not None:
        used_strategies.add(selected_strategy)

    # Content type mapping dictionary for cleaner code
    content_type_map = {
        "Auto": "Let the AI model choose the appropriate format based on context",
        "Casestudy": "Longer-form, detailed, with a clear conclusion",
        "Storytelling": """ Viết theo phong cách kể chuyện: có nhân vật cụ thể, cảm xúc, hoàn cảnh và cao trào
        Tránh dùng ngôn ngữ quảng cáo hay khuyến mãi (ví dụ: 'ưu đãi', 'mua ngay', 'tháng này')
        Tập trung vào hành trình thay đổi, sự gắn kết cảm xúc và thông điệp nhân văn""",
        
        "Tips & Advice": "Practical, short, high-value tips",
        "Trend Spotting": "Covers current or upcoming fashion trends",
        "SEO Blog Posts": "Longer-form for website traffic or blog use",
        "Shopee Product Descriptions": "Optimized product copy"
    }
    
    # Get format instruction from mapping
    format_instruction = content_type_map.get(content_type, f'Định dạng bài viết phải là "{content_type}"')
    
    # Format-specific rule nếu là Storytelling
    storytelling_note = ""
    if content_type == "Storytelling":
        storytelling_note = """
       ❗Lưu ý cực kỳ quan trọng:
        - Không được dùng từ như: ưu đãi, giveaway, miễn phí, thử thách, biến hình, bí kíp, sản phẩm, khuyến mãi ở tiêu đề của content_plan
        - Không được đề cập thương hiệu ở tiêu đề (nếu không có vai trò cảm xúc).
        - Chỉ dùng tên người, thời gian, sự kiện, ký ức, hành trình, hoặc mối quan hệ (cha-con, mẹ-con, vợ-chồng...).
        - Chỉ thể hiện sản phẩm qua *tình huống* hoặc *hành động ý nghĩa*, không được miêu tả công dụng trực tiếp.
        """
    print(f"============== {content_type}: ",format_instruction)
    
    system_prompt = f"""
    Nhiệm vụ của bạn là tạo một **strategy (chiến lược nội dung cảm xúc từ thương hiệu/nhãn hiệu/cậu chuyện/kế hoạch)** để triển khai thành nhiều bài viết trên mạng xã hội với cá tính riêng.
    Nếu người dùng có sẵn thương hiệu rồi thì chỉ cần viết các tiêu đề gợi cảm xúc và đối tượng mục tiêu. (Ví dụ nếu sản phẩm sữa rửa mặt mặt nam thì title có thể là 'Nam Tính Mới' đại diện cho một hướng đi chiến lược)
    Chú ý các từ khoá dưới đây để tạo nên title và story hấp dẫn
    `focus`: Chủ đề nội dung trung tâm (VD: "Chăm sóc giấc ngủ với thảo mộc")
    `core_promise`: Thông điệp cốt lõi giúp người đọc thấy giá trị thực (VD: "Một giấc ngủ sâu bắt đầu từ một tách trà êm dịu")

    **Cảm xúc chủ đạo được chọn là: {selected_strategy}**
    Định dạng bài viết là: {content_type} – {format_instruction} {storytelling_note}.
    Đây là cảm xúc trung tâm sẽ chi phối toàn bộ cách kể chuyện, title, story, tone bài viết và kế hoạch nội dung.
    
    Hãy tạo kết quả gồm 3 phần sau:

    1. **title**: Tên nhãn hiệu (ví dụ chuối ngon 37, Awesome Banana) gợi cảm xúc – đi kèm với lời hứa thương hiệu thường là brand variant hoặc cụm từ dễ nhớ (VD: "ZenDream", "Slow Start")
    2. **story**: câu chuyện thương hiệu hoặc lời hứa cốt lõi, Một đoạn kể cảm xúc thể hiện lời hứa thương hiệu – chính là brand manifesto hoặc gợi ý cảm xúc {selected_strategy}
    3. **content_plan**: Kế hoạch cho {post_num} bài viết theo định dạng {content_type}. Mỗi bài gồm:
   - `goal`: Mục tiêu nội dung (ví dụ: gợi nhắc ký ức, truyền cảm hứng, tri ân cha mẹ,...)
   - `title`: Tiêu đề gợi cảm xúc, thu hút, gây tò mò **không được mang tính quảng cáo**, không dùng từ như "ưu đãi", "miễn phí", "khuyến mãi", "thử thách", "bí kíp", v.v. Nếu là storytelling, phải là một dòng kể chuyện hoặc mở đầu cảm xúc.
   - `format`: Luôn là {content_type}
   - `content_idea`: 
        Mô tả nội dung triển khai. Nếu là storytelling, **tuyệt đối không được mô tả công dụng trực tiếp của sản phẩm**, chỉ được thể hiện sản phẩm qua hành động, tình huống, hoặc mối quan hệ.
        Truyền tải một vài giá trị về kiến thức/thông tin độc đáo/cảm xúc (1 câu nói kinh điển, 1 câu thơ kinh điển, 1 thành ngữ kinh điển nói về tình cảm gia đình, ...)
    Yêu cầu:
    - Kết nối cảm xúc với thương hiệu
    - Trình bày rõ ràng, dễ hiểu, tạo cảm giác chân thật
    - Tránh từ ngữ bán hàng nếu là storytelling
        * Xây dựng câu chuyện có cốt truyện rõ ràng
        * Tạo hình ảnh phong cách sống hấp dẫn
        * Sử dụng ngôn ngữ giàu hình ảnh và cảm xúc
    - Viết bằng tiếng Việt nếu input chủ yếu là tiếng Việt. Nếu phần lớn là tiếng Anh, bạn có thể trả bằng tiếng Anh.
      
"""
    
    response = await client.aio.models.generate_content(
        model='gemini-2.0-flash',
        contents=f""" 
        Dưới đây là thông tin từ người dùng:

        - Mô tả chung: {description}
        - Insight người dùng: {insight}   
        - `format`: Định dạng bài viết cần dựa trên {content_type} đề xuất 
        - Đối tượng mục tiêu: {target_customer}
        Dựa trên các dữ liệu trên, hãy tạo một chiến lược nội dung cảm xúc hoàn chỉnh theo cấu trúc đã định nghĩa.
        
        """,
        config=types.GenerateContentConfig(
            response_mime_type='application/json',
            response_schema=ThemeBase,
            system_instruction=types.Part.from_text(text=system_prompt),

            temperature=1,      # Sáng tạo cao
            # top_p=0.90,           # Cho phép đa dạng từ ngữ (có thể bỏ nếu chỉ dùng temp)
            # top_k=40,             # Lựa chọn thay thế cho top_p (thường bỏ trống)
            # candidate_count=3,    # Lấy nhiều lựa chọn để A/B test
            # seed=None,            # Không cần seed để có sự ngẫu nhiên
            # max_output_tokens=100, # Giới hạn độ dài cho quảng cáo
            # stop_sequences=[],    # Thường không cần
            # presence_penalty=0.5, # Phạt nhẹ sự lặp lại chung
            frequency_penalty=0.5, # Phạt nhẹ sự lặp lại từ cụ thể

        ),
    )
    
    content = json.loads(response.text)
    return ThemeBase(**content)

async def generate_theme_title_and_story(campaign_title: str, insight: str, description: str, target_customer: str, post_num: int, content_type: str):
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    # Tạo set để theo dõi các chiến lược đã sử dụng
    used_strategies = set()
    
    # Generate 3 themes concurrently với các chiến lược khác nhau
    tasks = [
        generate_single_theme(client, description, insight, target_customer, post_num, content_type, used_strategies)
        for _ in range(3)
    ]
    
    themes = await asyncio.gather(*tasks)
    print("Generated 3 themes concurrently with different strategies based on user prompt.")
    
    return [
        {
            "title": theme.title,
            "story": theme.story,
            "content_plan": theme.content_plan.model_dump()
        }
        for theme in themes
    ]

from schemas import PostMetadata
class BlogPost(BaseModel):
    title: str
    content: str

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

async def generate_post_content(theme_title: str, theme_story: str, campaign_desc: str, content_plan: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a post content using Google Gemini API asynchronously."""
    print(f"🔄 Starting generation of post with title: '{content_plan.get('title')}' for theme: '{theme_title}'")
    start_time = time.time()
    try:
        # Initialize the client
        
        
        # Extract content plan metadata
        goal = content_plan.get('goal')
        format_type = content_plan.get('format')
        content_idea = content_plan.get('content_idea')
        print("==========content_idea",content_idea)
        post_title = content_plan.get('title')
        print("==========campaign desc",campaign_desc)
        prompt = (
                f"Hãy tạo một bài viết bằng tiếng Việt về '{theme_title}' kết hợp giữa tính năng sản phẩm và triết lý sống, tạo sự đồng điệu với người đọc.\n\n"
                f"--- TÊN THƯƠNG HIỆU ---\n{theme_title}\n\n"
                f"--- TRIẾT LÝ & GIÁ TRỊ ---\n{theme_story}\n\n"
                f"--- MỤC TIÊU BÀI VIẾT ---\n{goal}\n\n"
                f"--- TIÊU ĐỀ BÀI VIẾT ---\n{post_title}\n\n"
                f"--- Ý TƯỞNG NỘI DUNG ---\n{content_idea}\n\n"
            )

        # System prompt for content generation
        system_prompt = f"""
        Bạn là trợ lý AI chuyên tạo nội dung kết nối sản phẩm với giá trị sống. Nhiệm vụ:
            1. Phân tích sâu tính năng sản phẩm và liên hệ với triết lý sống phù hợp.
            2. Tạo nội dung chân thực, tập trung vào giá trị thay vì quảng cáo thuần túy.
            3. Viết bài bằng tiếng Việt với giọng văn đồng cảm, khơi gợi suy ngẫm và thú vị theo định dạng {format_type}.
            4. Kết hợp khéo léo giữa thông tin sản phẩm và bài học cuộc sống.
            6. Dựa vào mô tả {campaign_desc}
            
            Xuất ra ĐÚNG ĐỊNH DẠNG JSON theo yêu cầu, không thêm text hay markdown.

            Ngôn ngữ: Tiếng Việt là chính
        """
        
        # Generate response using Gemini API
        # response = client.models.generate_content(
        response = await client.aio.models.generate_content(
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
            "content": f"This post is based on theme: '{theme_title}'\n\n{theme_story}\n\nGenerated with description: '{campaign_desc}'.",
            "post_metadata": None
        }

async def create_default_content_plan(theme_title: str, theme_story: str, num_posts=5) -> Dict[str, Any]:
    """Tạo content plan mặc định khi không có plan được cung cấp"""
    
    prompt = f"""
    Tạo kế hoạch nội dung cho chủ đề '{theme_title}' với {num_posts} bài viết.
    Mô tả chủ đề: {theme_story}
    Mỗi bài viết cần có:
    - goal: Mục tiêu nội dung
    - title: Tiêu đề bài viết 
    - format: Định dạng (bài viết/infographic/video)
    - content_idea: Ý tưởng nội dung ngắn
    """
    
    response = await client.aio.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt,
        config={
            'response_mime_type': 'application/json',
            'response_schema': Plan
        }
    )
    
    content = json.loads(response.text)
    return content #.model_dump()

async def process_with_semaphore(theme_title: str, theme_story: str, campaign_desc: str, content_plan: Optional[Dict[str, Any]] = None):
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
                    campaign_desc,
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
            print('campaign_data existed')
            brand_voice = campaign_data.get('brandVoice', '')
            key_messages = campaign_data.get('keyMessages', [])
            content_guidelines = campaign_data.get('contentGuidelines', '')
            
            enriched_story = f"{theme.story}\n\nBrand Voice: {brand_voice}\n"
            print("============ enriched_story",enriched_story)
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
        campaign.description,
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
