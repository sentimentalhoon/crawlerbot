import json
from google import genai
import config
import regions

class AIOptimizer:
    def __init__(self):
        self.api_key = config.GEMINI_API_KEY
        self.client = None
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
                print("Gemini AI Client Initialized.")
            except Exception as e:
                print(f"Failed to initialize Gemini Client: {e}")
        else:
            print("Warning: GEMINI_API_KEY not found in config.")

    def optimize_content(self, title, content):
        """
        Uses Gemini to extract fields:
        title, damage_content, features, location_city, location_district
        """
        if not self.client:
            print("AI Client not ready. Returning original content.")
            return {
                'title': title, 
                'damage_content': content,
                'category': 'OTHER',
                'features': 'AI 처리 실패',
                'location_city': '',
                'location_district': '',
                'images': []
            }

        prompt = f"""
        You are a professional content editor for a bulletin board blacklist/warning system.
        
        Task:
        Extract the following fields from the input text:
        1. **category**: Classify the incident into exactly ONE of these keys:
           - "NON_PAYMENT" (먹튀: 미결제 도주)
           - "VANDALISM" (기물파손: 모니터, 키보드 등 파손)
           - "THEFT" (절도: 물품 훔침)
           - "DISTURBANCE" (행패/소란: 욕설, 고성방가, 영업방해)
           - "MINOR_ISSUE" (미성년자/신분증: 미성년자 야간출입, 신분증 도용)
           - "SYSTEM_ABUSE" (시스템악용: VPN, 핵, 관리툴 조작)
           - "OTHER" (기타: 위 항목에 해당하지 않음)
           * If unsure, use "OTHER".
        2. **location_city**: City/Province (must be one of the top-level keys in Valid Regions). e.g. "서울특별시". If not found, use "".
        3. **location_district**: District (must be a value in Valid Regions for the selected city). e.g. "강남구". If not found, use "".
        4. **features**: Characteristics of the suspect (e.g. appearance, age, glasses, height). Summarize in one line. If not found, use "정보 없음".
        5. **damage_content**: The full content, rewritten professionally. Include all details like Name, Phone, Account, Money, etc. here.
        6. **title**: A short summary title (e.g. "지역 - 이름/특징 - 피해내용").
        
        **CRITICAL INSTRUCTION**: 
        - Remove the specific Telegram ID "@pc3_6_5" from ALL fields (title, content, features). 
        - Remove any other promotional Telegram IDs or links if found.
        - Do NOT include "@pc3_6_5" in the output.
        
        Valid Regions Pattern (Reference only):
        {list(regions.KOREA_REGIONS.keys())}
        
        Output Format: JSON ONLY with keys: "category", "location_city", "location_district", "features", "damage_content", "title".
        **CRITICAL: Output terms MUST be in KOREAN.**
        
        Input Title: {title}
        Input Content:
        {content}
        """

        try:
            response = self.client.models.generate_content(
                model='gemini-2.0-flash',
                # contents=prompt # Correct argument is contents not prompt for some libs, but sticking to previous usage
                contents=prompt
            )
            
            json_str = response.text.strip()
            # Clean markdown if present
            if json_str.startswith('```json'):
                json_str = json_str[7:]
            if json_str.startswith('```'):
                json_str = json_str[3:]
            if json_str.endswith('```'):
                json_str = json_str[:-3]
            
            # Post-processing Safety Check
            json_str = json_str.replace("@pc3_6_5", "")
                
            parsed = json.loads(json_str)
            return parsed
            
        except Exception as e:
            print(f"AI Optimization failed: {e}")
            return {
                'title': title, 
                'damage_content': content, 
                'category': 'OTHER',
                'features': 'AI 처리 실패',
                'location_city': '',
                'location_district': ''
            }

if __name__ == "__main__":
    # Test
    opt = AIOptimizer()
    res = opt.optimize_content("나쁜놈 신고합니다", "이사람 돈떼먹고 도망갓어요 010-0000-0000 서울 강남구에서 발생")
    print(res)
