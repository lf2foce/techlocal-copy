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
       - Chủ thể chính và hành động (ưu tiên mô tả người Việt, không sử dụng từ nhạy cảm như young/girl/boy/child)
       - Bối cảnh và không gian (ưu tiên các địa điểm, kiến trúc, cảnh quan đặc trưng Việt Nam, không sử dụng chữ viết hoặc cờ)
       - Góc máy và khoảng cách (close-up, medium shot, wide shot)
       - Ánh sáng và màu sắc chủ đạo
       - Cảm xúc/mood tổng thể

    3. **`vietnamese_explanation` (string)**: Giải thích **tiếng Việt** ngắn gọn về cách prompt này thể hiện nội dung và cảm xúc của phần tương ứng.

    Yêu cầu Output:
    - english_prompt phải tuân thủ phong cách {style} và giới hạn 75-100 từ
    - TRÁNH các từ nhạy cảm: young, girl, boy, child, baby, kid, teen, người trẻ
    - Sử dụng các từ thay thế: person, individual, professional, character
    - Return ONLY a valid JSON object với key 'story_prompts'
    - Value của 'story_prompts' là list chứa {num_prompts} objects
    - Mỗi object có 3 string keys: 'part', 'english_prompt', 'vietnamese_explanation', đều không rỗng

    Ví dụ prompt tốt cho hình ảnh người Việt:
    "A Vietnamese professional in traditional ao dai stands gracefully in front of a lotus pond at dawn, with soft golden light reflecting on the water. Shot from a medium-low angle to emphasize cultural pride, the scene features subtle Vietnamese architectural elements in the background. The color palette combines emerald green from the ao dai with warm golden tones, creating a harmonious blend of tradition and modernity. 16:9 aspect ratio, 4K resolution."
    
    Ví dụ khác:
    "A group of Vietnamese farmers in conical hats work together in a vibrant green rice field under the afternoon sun. Wide shot captures the sweeping landscape with mountains in the distance, showcasing Vietnam's natural beauty. Earthy tones dominate with pops of color from the farmers' clothing, conveying a sense of community and hard work. Cinematic lighting enhances the dramatic shadows and textures. 16:9 aspect ratio, 4K resolution."
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