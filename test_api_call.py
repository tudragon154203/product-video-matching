#!/usr/bin/env python3
import httpx
import asyncio
import json

async def test_api_call():
    # Test the exact same call that the API makes
    query = "ergonomic pillows"
    industry_labels = ["fashion","beauty_personal_care","books","electronics","home_garden","sports_outdoors","baby_products","pet_supplies","toys_games","automotive","office_products","business_industrial","collectibles_art","jewelry_watches","other"]
    
    # Build classification prompt
    labels_csv = ",".join(industry_labels)
    cls_prompt = f"""Bạn là bộ phân loại zero-shot. 
Nhiệm vụ: Gán truy vấn sau vào đúng 1 nhãn industry trong danh sách cho trước.

YÊU CẦU BẮT BUỘC:
- Chỉ in ra đúng 1 nhãn duy nhất, không thêm chữ nào khác.
- Nếu độ chắc chắn thấp, hãy chọn "other".
- Danh sách nhãn hợp lệ: [{labels_csv}]

Truy vấn:
{query}"""
    
    try:
        async with httpx.AsyncClient() as client:
            print("Making classification request...")
            response = await client.post(
                'http://host.docker.internal:11434/api/generate',
                json={
                    'model': 'qwen3:4b-instruct',
                    'prompt': cls_prompt,
                    'stream': False,
                    'options': {'timeout': 60000}
                },
                timeout=60
            )
            print('Classification response status:', response.status_code)
            if response.status_code == 200:
                data = response.json()
                industry = data['response'].strip()
                print('Classified industry:', repr(industry))
                
                # Test generation prompt
                gen_prompt = f"""Bạn là bộ sinh từ khoá tìm kiếm đa ngôn ngữ cho TMĐT và video.

ĐẦU VÀO:
- query_goc = "{query}"
- industry = "{industry}"

YÊU CẦU ĐẦU RA:
- Chỉ in RA JSON hợp lệ theo schema:
  {{
    "product": {{ "en": [strings...] }},
    "video":   {{ "vi": [strings...], "zh": [strings...] }}
  }}

QUY TẮC:
1) "product.en": 2–4 cụm từ tiếng Anh để tìm sản phẩm/dropship.
2) "video.vi": 2–4 cụm từ tiếng Việt để tìm video.
3) "video.zh": 2–4 cụm từ tiếng Trung giản thể để tìm video.
4) Không vượt quá 5 từ khoá mỗi nhóm; không thêm chú thích ngoài JSON.
5) Giữ nghĩa cốt lõi của query_goc; không bịa thương hiệu.

BẮT ĐẦU."""
                
                print("Making generation request...")
                response = await client.post(
                    'http://host.docker.internal:11434/api/generate',
                    json={
                        'model': 'qwen3:4b-instruct',
                        'prompt': gen_prompt,
                        'stream': False,
                        'options': {'timeout': 60000, 'temperature': 0.2}
                    },
                    timeout=60
                )
                print('Generation response status:', response.status_code)
                if response.status_code == 200:
                    data = response.json()
                    print('Generated response:', repr(data['response']))
                    try:
                        queries = json.loads(data['response'])
                        print('Parsed queries:', queries)
                    except json.JSONDecodeError as e:
                        print('JSON decode error:', e)
                        print('Raw response:', data['response'])
                else:
                    print('Generation error response:', response.text)
            else:
                print('Classification error response:', response.text)
    except Exception as e:
        print('Request failed:', str(e))
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_api_call())