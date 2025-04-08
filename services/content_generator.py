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

class ThemeGenerate(BaseModel):
    title: str
    story: str
# worked
def generate_theme_title_and_story(campaign_title: str, insight: str, description: str, target_customer:str) -> tuple[str, str]:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    # Generate response using Gemini API (synchronous version)
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=f"Tạo thương hiệu cho pages với các thông tin  {insight} {target_customer}",
        config=types.GenerateContentConfig(
            response_mime_type='application/json',
            response_schema=ThemeGenerate,
            system_instruction=types.Part.from_text(text=description),
        ),
    )
    
    # Extract the response
    print("Generated post based on user prompt.")
    content = json.loads(response.text)
    
    # Validate and parse the response using Pydantic
    blog_post = ThemeGenerate(**content)
    
    return blog_post.title, blog_post.story

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
            5. Generating multiple (3-4) relevant ENGLISH image prompts AND brief VIETNAMESE explanations for them, suitable for text-to-image AI, aligned with the flow of a given post's content and the overall campaign knowledge.
            6. Generating ENGLISH image prompts for a social media avatar and cover photo, based on a brand name and campaign concept, along with brief VIETNAMESE explanations for each.
            CRITICAL: Always use the provided CAMPAIGN KNOWLEDGE/CONTEXT when generating content.
            Adhere strictly to the JSON output format when requested (names, schedule, evaluation, post, image prompts+explanation, avatar/cover prompts).
            Output ONLY the valid JSON object without surrounding text or markdown.
            Language: Primarily Vietnamese, except for the English image prompt.
        """
        
        # Generate response using Gemini API
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': BlogPost,
                'system_instruction': types.Part.from_text(text=system_prompt),
            },
        )
        
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

async def process_with_semaphore(theme_title: str, theme_story: str, campaign_title: str, num_posts: int, concurrency: int = 1):
    """Process post generation with a semaphore to limit concurrent API calls.
    Implements rate limiting protection with smaller batch sizes and delays between requests.
    """
    # Use a semaphore to control concurrency - default to 1 to avoid rate limits
    semaphore = asyncio.Semaphore(concurrency)
    print(f"🚀 Starting async generation of {num_posts} posts with concurrency limit of {concurrency}")
    
    async def bounded_generate(post_number):
        print(f"⏳ Post {post_number} waiting for semaphore slot...")
        max_retries = 3
        retry_count = 0
        base_delay = 2  # Base delay in seconds
        
        while retry_count <= max_retries:
            try:
                async with semaphore:
                    print(f"🔓 Post {post_number} acquired semaphore slot")
                    # Add a delay before making the API call to prevent rate limiting
                    await asyncio.sleep(2)  # 2-second delay between requests as requested
                    result = await generate_post_content(theme_title, theme_story, campaign_title, post_number)
                    print(f"🔒 Post {post_number} released semaphore slot")
                    return result
            except Exception as e:
                error_str = str(e)
                retry_count += 1
                
                # Check if this is a rate limit error
                if "429" in error_str and "RESOURCE_EXHAUSTED" in error_str:
                    # Calculate exponential backoff with jitter
                    retry_delay = base_delay * (2 ** retry_count) + random.uniform(0, 1)
                    print(f"⚠️ Rate limit hit for post {post_number}. Retrying in {retry_delay:.2f} seconds... (Attempt {retry_count}/{max_retries})")
                    
                    if retry_count <= max_retries:
                        await asyncio.sleep(retry_delay)
                        continue
                
                print(f"❌ Error in bounded_generate for post {post_number}: {error_str}")
                # Return a fallback post on error
                return {
                    "title": f"Post {post_number} - {theme_title} (Fallback)",
                    "content": f"This is a fallback post for theme: '{theme_title}'. The original generation failed with error: {error_str}"
                }
    
    # Create tasks with proper error handling
    tasks = [bounded_generate(i+1) for i in range(num_posts)]
    
    # Process in smaller batches if there are many posts
    batch_size = 4  # Reduced from 5 to 4 as requested
    results = []
    
    if num_posts <= batch_size:
        # For small number of posts, process all at once
        print(f"Processing all {num_posts} posts in a single batch")
        results = await asyncio.gather(*tasks, return_exceptions=False)
    else:
        # For larger numbers, process in batches
        print(f"Processing {num_posts} posts in batches of {batch_size}")
        for i in range(0, num_posts, batch_size):
            batch_end = min(i + batch_size, num_posts)
            print(f"Processing batch {i//batch_size + 1}: posts {i+1}-{batch_end}")
            batch_results = await asyncio.gather(*tasks[i:batch_end], return_exceptions=False)
            results.extend(batch_results)
            # Increased delay between batches to avoid rate limiting
            if batch_end < num_posts:
                delay_seconds = 5  # Increased from 1 to 5 seconds
                print(f"⏱️ Waiting {delay_seconds} seconds before processing next batch to avoid rate limits...")
                await asyncio.sleep(delay_seconds)
    
    # Validate results
    valid_results = []
    for i, result in enumerate(results):
        if isinstance(result, dict) and "title" in result and "content" in result:
            valid_results.append(result)
        else:
            print(f"⚠️ Invalid result for post {i+1}: {result}")
            # Add a replacement post
            valid_results.append({
                "title": f"Post {i+1} - {theme_title} (Replacement)",
                "content": f"This is a replacement post for theme: '{theme_title}'"
            })
    
    print(f"✨ Completed generation of {len(valid_results)}/{num_posts} valid posts")
    return valid_results

def save_posts_to_db(post_contents, campaign_id, theme_id, db):
    """Create posts in the database from generated content with improved batch processing."""
    if not post_contents:
        print("⚠️ No post contents provided to save")
        return 0
        
    now = datetime.now()
    created_count = 0
    batch_size = 5  # Process in smaller batches to avoid transaction issues
    total_posts = len(post_contents)
    
    print(f"🔄 Starting to save {total_posts} posts to database in batches of {batch_size}")
    
    # Process in batches
    for batch_start in range(0, total_posts, batch_size):
        batch_end = min(batch_start + batch_size, total_posts)
        current_batch = post_contents[batch_start:batch_end]
        batch_count = 0
        
        try:
            print(f"📦 Processing batch {batch_start//batch_size + 1}/{(total_posts + batch_size - 1)//batch_size}: posts {batch_start+1}-{batch_end}")
            
            # Create a fresh transaction for each batch
            for i, post_content in enumerate(current_batch):
                # Validate post content
                if not isinstance(post_content, dict) or "title" not in post_content or "content" not in post_content:
                    print(f"⚠️ Invalid post content format at index {batch_start + i}: {post_content}")
                    continue
                    
                post = ContentPost(
                    campaign_id=campaign_id,
                    theme_id=theme_id,
                    title=post_content["title"],
                    content=post_content["content"],
                    status="scheduled",
                    created_at=now + timedelta(microseconds=batch_start + i)
                )
                db.add(post)
                batch_count += 1
            
            # Commit each batch separately
            db.commit()
            created_count += batch_count
            print(f"✅ Batch {batch_start//batch_size + 1} successful: saved {batch_count} posts")
            
        except Exception as e:
            db.rollback()
            print(f"❌ Error saving batch {batch_start//batch_size + 1}: {str(e)}")
            # Continue with next batch instead of failing completely
    
    if created_count > 0:
        print(f"✅ Successfully saved {created_count}/{total_posts} posts to database")
    else:
        print(f"❌ Failed to save any posts to database out of {total_posts} attempted")
    
    return created_count

def generate_posts_from_theme(theme: DBTheme, db: Session) -> int:
    print(f"🚀 Starting post generation for theme ID: {theme.id}, title: '{theme.title}'")
    campaign = db.query(Campaign).filter(Campaign.id == theme.campaign_id).first()
    if not campaign:
        print(f"❌ Campaign not found for theme ID: {theme.id}")
        return 0

    # Ensure theme context is up-to-date
    theme = db.query(DBTheme).filter(DBTheme.id == theme.id).first()
    if not theme:
        print(f"❌ Theme ID: {theme.id} not found in database")
        return 0

    num_posts = campaign.repeat_every_days
    print(f"📊 Generating {num_posts} posts for campaign: '{campaign.title}'")
    
    # Import nest_asyncio to handle nested event loops
    try:
        import nest_asyncio
        nest_asyncio.apply()
        print("Applied nest_asyncio to handle nested event loops")
    except ImportError:
        print("nest_asyncio not available, will use alternative approach")
    
    # Async function to run the generation process
    async def run_async_generation():
        try:
            # Increase timeout for larger batches
            timeout_seconds = max(120, num_posts * 10)  # Scale timeout with number of posts
            print(f"🕒 Setting timeout to {timeout_seconds} seconds for {num_posts} posts")
            
            return await asyncio.wait_for(
                process_with_semaphore(
                    theme.title, 
                    theme.story, 
                    campaign.title, 
                    num_posts,
                    concurrency=1  # Reduced concurrency to avoid rate limits
                ),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            print(f"⏱️ Async generation timed out after {timeout_seconds} seconds")
            # Return partial results if available
            print("Generating fallback posts due to timeout")
            return [{
                "title": f"Post {i+1} - {theme.title} (Timeout Fallback)",
                "content": f"This post is based on theme: '{theme.title}'. The original generation timed out."
            } for i in range(num_posts)]
        except Exception as e:
            print(f"❌ Error in async generation: {str(e)}")
            return None
    
    # Try different approaches to run the async code
    try:
        import asyncio
        
        # First approach: Use asyncio.run() which handles the event loop properly
        try:
            # This works when there's no existing event loop
            print("Attempting to use asyncio.run()")
            post_contents = asyncio.run(run_async_generation())
            return save_posts_to_db(post_contents, campaign.id, theme.id, db)
        except RuntimeError as e:
            # There's already an event loop running (likely FastAPI)
            print(f"Could not use asyncio.run(): {str(e)}")
            
            # Second approach: Get the current event loop and create a task
            try:
                print("Using existing event loop with create_task")
                loop = asyncio.get_event_loop()
                
                # Use a more reliable approach with run_in_executor for FastAPI context
                from concurrent.futures import ThreadPoolExecutor
                
                def run_in_thread():
                    # Create a new event loop in the thread
                    thread_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(thread_loop)
                    try:
                        # Run the async function in the thread's event loop
                        return thread_loop.run_until_complete(run_async_generation())
                    finally:
                        thread_loop.close()
                
                # Run the function in a separate thread
                with ThreadPoolExecutor() as executor:
                    future = loop.run_in_executor(executor, run_in_thread)
                    try:
                        # Wait for the result with a timeout
                        post_contents = loop.run_until_complete(
                            asyncio.wait_for(future, timeout=60)
                        )
                        return save_posts_to_db(post_contents, campaign.id, theme.id, db)
                    except asyncio.TimeoutError:
                        print("Thread execution timed out")
                        return 0
                    except Exception as e:
                        print(f"Error in thread execution: {str(e)}")
                        return 0
            except Exception as e:
                print(f"Error waiting for task: {str(e)}")
                return 0
    except Exception as e:
        print(f"Error in async handling: {str(e)}")
    
    # Fallback to synchronous generation if all async approaches fail
    try:
        print("Using fallback synchronous generation")
        fallback_posts = []
        for i in range(num_posts):
            fallback_posts.append({
                "title": f"Post {i+1} - {theme.title}",
                "content": f"This post is based on theme: '{theme.title}'\n\n{theme.story}\n\nGenerated item {i+1} in the campaign '{campaign.title}'."
            })
        
        # Check if we have the expected number of posts before saving
        if len(fallback_posts) != num_posts:
            print(f"⚠️ Warning: Expected {num_posts} posts but generated {len(fallback_posts)}")
        
        # Verify posts are properly formatted before saving
        for i, post in enumerate(fallback_posts):
            if not isinstance(post, dict) or "title" not in post or "content" not in post:
                print(f"⚠️ Invalid post format at index {i}: {post}")
                fallback_posts[i] = {
                    "title": f"Post {i+1} - {theme.title} (Fixed)",
                    "content": f"This is a replacement post for theme: '{theme.title}'"
                }
        
        # Save posts to database with improved error handling
        saved_count = save_posts_to_db(fallback_posts, campaign.id, theme.id, db)
        print(f"📊 Summary: Generated {len(fallback_posts)} posts, saved {saved_count} to database")
        return saved_count
    except Exception as e:
        print(f"❌ Error in fallback generation: {str(e)}")
        return 0
    
    # This line should never be reached, but kept for backward compatibility
    return 0

def approve_post(post_id: int, db: Session) -> ContentPost:
    post = db.query(ContentPost).filter(ContentPost.id == post_id).first()
    if not post:
        raise ValueError("Post not found")

    post.status = "scheduled"
    db.commit()
    return post
