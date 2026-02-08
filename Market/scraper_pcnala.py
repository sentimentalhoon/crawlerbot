
import requests
import re
import json
import logging

class PCNalaScraper:
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        # Suppress SSL warnings
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def parse_detail(self, url):
        """
        Fetches the page and extracts the 'trade' object from Next.js serialized data.
        Returns a dict mapped to the API structure.
        """
        try:
            print(f"Fetching {url}...")
            resp = self.session.get(url, headers=self.headers, verify=False)
            resp.encoding = 'utf-8' # Force utf-8
            resp.raise_for_status()
            html = resp.text

            # Regex to find the trade object in the Next.js script stream
            # Pattern: "trade":{ ... }
            
            # The structure is complex: ["...", {"trade": ... }]
            # Let's try to capture the block starting with \"trade\":
            # and matching balanced braces is hard with regex.
            
            # Better approach: Extract the full script lines and parse the array.
            
            # Robust parsing of Next.js hydration chunks
            # self.__next_f.push([ ... ])
            # We must find start of push([ and find matching ]) respecting quotes.
            
            search_str = 'self.__next_f.push(['
            start_pos = 0
            
            # Accumulate string data by chunk ID (usually 1)
            # chunks[id] = "concatenated string"
            chunks = {}
            
            while True:
                idx = html.find(search_str, start_pos)
                if idx == -1:
                    break
                
                content_start = idx + len(search_str)
                
                stack = 1
                in_quote = False
                escape = False
                extract_end = -1
                
                for i in range(content_start, len(html)):
                    char = html[i]
                    
                    if escape:
                        escape = False
                        continue
                    if char == '\\':
                        escape = True
                        continue
                        
                    if char == '"':
                        in_quote = not in_quote
                    
                    if not in_quote:
                        if char == '[':
                            stack += 1
                        elif char == ']':
                            stack -= 1
                            if stack == 0:
                                extract_end = i
                                break
                
                if extract_end != -1:
                    raw_content = html[content_start:extract_end]
                    
                    # Wrap in brackets to make it valid JSON array
                    json_candidate = f"[{raw_content}]"
                    
                    try:
                        chunk = json.loads(json_candidate)
                        # chunk is [id, "data", ...]
                        if isinstance(chunk, list) and len(chunk) >= 2:
                            chunk_id = chunk[0]
                            chunk_data = chunk[1]
                            
                            if isinstance(chunk_data, str):
                                if chunk_id not in chunks:
                                    chunks[chunk_id] = ""
                                chunks[chunk_id] += chunk_data
                    except json.JSONDecodeError:
                        pass
                
                start_pos = idx + 1

            # Process accumulated chunks
            for chunk_id, full_data in chunks.items():
                lines = full_data.split('\n')
                for line in lines:
                    if not line.strip(): continue
                    
                    if '"trade":' in line or '\\"trade\\":' in line:
                        try:
                            # Strip Next.js format prefix (hex_id:)
                            json_str = line
                            if ':' in line[:5]:
                                parts = line.split(':', 1)
                                if len(parts) > 1:
                                    possible_json = parts[1]
                                    if possible_json.startswith(('[', '{', '"')):
                                        json_str = possible_json
                            
                            data = json.loads(json_str)
                            
                            if isinstance(data, dict) or isinstance(data, list):
                                trade_data = self.find_key(data, 'trade')
                                if trade_data:
                                    return self.map_to_api(trade_data)
                        except json.JSONDecodeError:
                            pass

            print("Could not find 'trade' data in scripts.")
            return None

            print("Could not find 'trade' data in scripts.")
            return None

        except Exception as e:
            print(f"Error parsing {url}: {e}")
            return None

    def map_to_api(self, raw):
        """
        Maps raw PCNala data to the structure required by psmo_community Market API.
        """
        # API requires:
        # title, description, price (calc from deposit+rights), category="PC_BUSINESS"
        # realEstate: { ... }
        
        # Raw fields (from analysis):
        # region, sub_region, area_size (pyeong), floor, deposit, monthly_rent, premium, facilities, move_in_date, contact, trade_images
        
        real_estate = {
            "locationCity": raw.get("region", "") or "",
            "locationDistrict": raw.get("sub_region", "") or "정보없음",
            "pcCount": 0, # Not explicit in raw fields, might be in facilities
            "deposit": int(raw.get("deposit") or 0),
            "monthlyRent": int(raw.get("monthly_rent") or 0),
            "managementFee": 0, # Missing
            "averageMonthlyRevenue": 0, # Missing
            "rightsMoney": int(raw.get("premium") or 0),
            "floor": int(raw.get("floor") or 0),
            "areaPyeong": float(raw.get("area_size") or 0),
            "areaMeters": float(raw.get("area_size") or 0) * 3.3058,
            "facilities": raw.get("facilities", ""),
            "moveInDate": raw.get("move_in_date", "즉시 가능"),
            "permitStatus": "허가 완료" if raw.get("has_license") else "확인 필요",
            "adminActionHistory": "없음", # Default
            "contactNumber": raw.get("contact", ""),
        }
        
        # Extract PC count from facilities if possible
        facilities = real_estate["facilities"]
        if facilities:
            pc_match = re.search(r'PC\s*(\d+)', facilities, re.IGNORECASE)
            if pc_match:
                real_estate["pcCount"] = int(pc_match.group(1))

        # Images
        images = []
        raw_images = raw.get("trade_images", [])
        if raw_images:
            # Sort by display_order
            raw_images.sort(key=lambda x: x.get("display_order", 0))
            for img in raw_images:
                if img.get("image_url"):
                    images.append(img["image_url"])

        return {
            "title": raw.get("title", ""),
            "description": raw.get("content", ""),
            "realEstate": real_estate,
            "images": images
        }

    def find_key(self, obj, key):
        if isinstance(obj, dict):
            if key in obj:
                return obj[key]
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    res = self.find_key(v, key)
                    if res: return res
        elif isinstance(obj, list):
            for item in obj:
                res = self.find_key(item, key)
                if res: return res
        return None

if __name__ == "__main__":
    # Test with the sample URL
    scraper = PCNalaScraper()
    url = "https://pcnala.com/trade/12f137ca-fe3c-4fdb-959e-91cf23fcab55"
    data = scraper.parse_detail(url)
    import json
    print(json.dumps(data, indent=2, ensure_ascii=False))
