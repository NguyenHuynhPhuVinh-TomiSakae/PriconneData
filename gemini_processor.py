import os
import re
import json
import base64
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Tải biến môi trường từ file .env
load_dotenv()

# Khởi tạo API key từ biến môi trường
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("Vui lòng đặt biến môi trường GEMINI_API_KEY")

# Biến toàn cục để theo dõi thời gian gọi API
last_api_call_time = 0

# Cấu hình sử dụng Gemini API
USE_GEMINI_API = False  # Đặt thành False để sử dụng tên gốc, True để chuyển sang romanji

def process_character_data(character):
    """
    Xử lý dữ liệu nhân vật
    - Sử dụng Gemini API để chuyển tên tiếng Nhật sang romanji hoặc
    - Trả về tên gốc tùy theo cấu hình USE_GEMINI_API
    """
    # Nếu không sử dụng Gemini API, trả về tên gốc ngay lập tức
    if not USE_GEMINI_API:
        return {
            "romanji_name": character['name']
        }
    
    global last_api_call_time
    
    # Tạo delay để không vượt quá giới hạn 15 request/phút
    current_time = time.time()
    time_since_last_call = current_time - last_api_call_time
    
    # Nếu chưa đủ 5 giây từ lần gọi trước, đợi thêm
    if time_since_last_call < 5 and last_api_call_time > 0:
        sleep_time = 5 - time_since_last_call
        print(f"Đợi {sleep_time:.2f} giây trước khi gọi API tiếp...")
        time.sleep(sleep_time)
    
    # Cập nhật thời gian gọi API
    last_api_call_time = time.time()
    
    # Khởi tạo Gemini client
    client = genai.Client(
        api_key=GEMINI_API_KEY,
    )

    # Chuẩn bị nội dung gửi đến Gemini
    prompt = f"""
    Hãy chuyển tên nhân vật tiếng Nhật này sang dạng romanji (phiên âm La-tinh):
    
    Tên tiếng Nhật: {character['name']}
    
    Hãy trả về kết quả theo định dạng JSON:
    {{
        "romanji_name": "tên phiên âm La-tinh"
    }}
    
    Chỉ trả về JSON, không có văn bản khác.
    """

    # Cấu hình và gọi API Gemini
    model = "gemini-2.0-flash"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        top_p=0.95,
        top_k=40,
        max_output_tokens=8192,
        response_mime_type="application/json",
        safety_settings=[
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_CIVIC_INTEGRITY", threshold="BLOCK_NONE"),
        ]
    )

    # Xử lý kết quả
    try:
        # Sử dụng .generate_content thay vì stream để lấy toàn bộ phản hồi cùng lúc
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=generate_content_config,
        )
        
        # Trích xuất phần JSON từ phản hồi
        json_text = response.text.strip()
        if json_text.startswith("```json"):
            json_text = json_text.split("```json")[1].split("```")[0].strip()
        elif json_text.startswith("```"):
            json_text = json_text.split("```")[1].split("```")[0].strip()
        
        processed_data = json.loads(json_text)
        return processed_data
    except Exception as e:
        print(f"Lỗi khi xử lý dữ liệu: {e}")
        
        # Xử lý dự phòng nếu Gemini không hoạt động
        return process_data_fallback(character)

def process_data_fallback(character):
    """
    Xử lý dữ liệu mà không cần Gemini API trong trường hợp API gặp lỗi
    """
    # Giữ nguyên tên (không phiên âm)
    return {
        "romanji_name": character['name']
    } 

def translate_role(role):
    """
    Dịch vai trò từ tiếng Nhật sang tiếng Việt phù hợp với ngữ cảnh
    của game Princess Connect Re:Dive
    """
    role_mapping = {
        "攻撃型": "DPS",                # Nhân vật tấn công chính
        "攻撃支援型": "DPS Hỗ trợ",     # Nhân vật vừa DPS vừa hỗ trợ tăng sát thương
        "支援型": "Hỗ trợ",            # Nhân vật hỗ trợ thuần túy (buff, heal)
        "耐久型": "Tank",              # Nhân vật chống chịu, hứng sát thương
        "耐久支援型": "Tank Hỗ trợ",    # Nhân vật có khả năng chống chịu và hỗ trợ đồng đội
        "耐久攻撃型": "Tank DPS"        # Nhân vật vừa chống chịu vừa gây sát thương
    }
    
    return role_mapping.get(role, role)  # Trả về giá trị gốc nếu không tìm thấy bản dịch

def format_rating(rating_str):
    """
    Định dạng đánh giá từ tiếng Nhật sang tiếng Việt
    """
    if not rating_str or rating_str == "-点" or rating_str == "-" or rating_str == "点":
        return "Chưa đánh giá"
    
    # Tìm số trong chuỗi
    match = re.search(r'(\d+\.\d+|\d+)', rating_str)
    if match:
        score = match.group(1)
        
        # Kiểm tra nếu có "(仮)" - tạm thời
        if "(仮)" in rating_str:
            return f"{score} (Tạm thời)"
        else:
            return score
            
    return rating_str  # Trả về giá trị gốc nếu không xử lý được 