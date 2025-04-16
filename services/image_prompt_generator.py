from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel
from typing import List, Tuple
import json
import os

load_dotenv()

class ImagePrompt(BaseModel):
    part: str
    english_prompt: str
    vietnamese_explanation: str

class ImagePromptGenerate(BaseModel):
    story_prompts: List[ImagePrompt]

def generate_image_prompts(text: str, style: str = "realistic", num_prompts: int = 2) -> List[Tuple[str, str, str]]:
    """Generate image prompts from post content using Gemini API.

    Args:
        text (str): The post content to generate prompts from

    Returns:
        List[Tuple[str, str, str]]: List of tuples containing (part, english_prompt, vietnamese_explanation)
    """
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    system_prompt = f"""
    Với vai trò là chuyên gia visual storytelling, hãy phân tích bài đăng tiếng Việt dưới đây.
    Dựa trên tên thương hiệu, mô tả kênh và nội dung bài đăng, tạo ra **{num_prompts} cặp prompt ảnh** minh họa các phần chính/cảm xúc quan trọng.
    Mỗi cặp prompt gồm:
    1. **`part` (string)**: Nhãn tiếng Việt ngắn gọn xác định phần minh họa (VD: 'Mở đầu', 'Nỗi trăn trở', 'Điểm sáng', 'Thông điệp chính', 'Lời kết nối', 'Hành động').
    2. **`english_prompt` (string)**: Prompt **tiếng Anh** chi tiết (chủ thể, hành động, bối cảnh, ánh sáng, màu sắc, mood) theo phong cách {style}.
    3. **`vietnamese_explanation` (string)**: Giải thích **tiếng Việt** ngắn gọn lý do prompt phù hợp.


    Yêu cầu Output:
    - english_prompt phải theo phong cách {style} đã chỉ định
    - try to remove sensitive word for gemini imagen3 generation such as young girl, etc.
    - Return ONLY a valid JSON object (no surrounding text/markdown) with a single key 'story_prompts'.
    - Value của 'story_prompts' là list chứa {num_prompts} objects.
    - Mỗi object có 3 string keys: 'part', 'english_prompt', 'vietnamese_explanation', đều không rỗng.
    """

    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=f"Trả thông tin cho nội dung sau đây: {text}",
        config=types.GenerateContentConfig(
            response_mime_type='application/json',
            response_schema=ImagePromptGenerate,
            system_instruction=types.Part.from_text(text=system_prompt),
        ),
    )
    
    content = json.loads(response.text)
    prompts = ImagePromptGenerate(**content)
    
    return [(prompt.part, prompt.english_prompt, prompt.vietnamese_explanation) 
            for prompt in prompts.story_prompts]