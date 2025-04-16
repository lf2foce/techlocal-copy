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

def generate_image_prompts(text: str, style: str = "realistic", num_prompts: int = 1) -> List[Tuple[str, str, str]]:
    """Generate image prompts from post content using Gemini API.

    Args:
        text (str): The post content to generate prompts from

    Returns:
        List[Tuple[str, str, str]]: List of tuples containing (part, english_prompt, vietnamese_explanation)
    """
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    system_prompt = f"""
    Với vai trò là chuyên gia visual storytelling, hãy phân tích bài đăng tiếng Việt dưới đây.
    Dựa trên nội dung bài đăng, tạo ra **{num_prompts} prompt ảnh** minh họa các phần chính/cảm xúc quan trọng.

    Mỗi nhóm prompt gồm:
    1. **`part` (string)**: Nhãn tiếng Việt ngắn gọn xác định phần minh họa (VD: 'Mở đầu', 'Nỗi trăn trở', 'Điểm sáng', 'Thông điệp chính', 'Lời kết nối', 'Hành động').
    2. **`english_prompt` (string)**: Prompt **tiếng Anh** chi tiết theo phong cách {style}, bao gồm:
       - Chủ thể chính và hành động (không sử dụng từ nhạy cảm như young/girl/boy/child)
       - Bối cảnh và không gian
       - Góc máy và khoảng cách (close-up, medium shot, wide shot)
       - Ánh sáng và màu sắc chủ đạo
       - Cảm xúc/mood tổng thể
       - Tỷ lệ khung hình: 1:1 hoặc 16:9
       - Độ phân giải: HD (1920x1080) hoặc 4K
    3. **`vietnamese_explanation` (string)**: Giải thích **tiếng Việt** ngắn gọn về cách prompt này thể hiện nội dung và cảm xúc của phần tương ứng.

    Yêu cầu Output:
    - english_prompt phải tuân thủ phong cách {style} và giới hạn 75-100 từ
    - TRÁNH các từ nhạy cảm: young, girl, boy, child, baby, kid, teen, người trẻ
    - Sử dụng các từ thay thế: person, individual, professional, character
    - Return ONLY a valid JSON object với key 'story_prompts'
    - Value của 'story_prompts' là list chứa {num_prompts} objects
    - Mỗi object có 3 string keys: 'part', 'english_prompt', 'vietnamese_explanation', đều không rỗng

    Ví dụ prompt tốt:
    "A determined professional in business attire stands confidently at a modern office desk, bathed in warm sunlight streaming through floor-to-ceiling windows. Shot from a medium angle, the scene captures their purposeful expression and positive body language. The color palette emphasizes blues and warm golden tones, creating an inspiring and optimistic atmosphere. 16:9 aspect ratio, 4K resolution."
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