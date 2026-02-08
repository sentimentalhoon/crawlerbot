# CrawlerBot Project

This project contains automated crawlers for Telegram channels to fetch and post content to `dool.co.kr`.

## Project Structure
- `BlackList/`: Crawler for blacklist incidents.
- `Market/`: Crawler for PC business market listings.
- `.env`: Unified configuration file at the root.

---

## 1. Ubuntu Server Setup (Ubuntu 서버 설정)

### Python & Environment Installation
Ubuntu 서버에서 크롤러를 실행하기 위해 필요한 패키지를 설치합니다.

```bash
# Update package list
sudo apt update

# Install Python 3 and pip
sudo apt install -y python3 python3-pip python3-venv

# (Optional) Create and enable virtual environment
python3 -m venv venv
source venv/bin/activate
```

### Dependency Installation
각 폴더의 요구사항을 설치합니다.

```bash
# BlackList dependencies
pip3 install -r BlackList/requirements.txt

# Market dependencies
pip3 install -r Market/requirements.txt
```

---

## 2. Configuration (환경 설정)

프로젝트 루트의 `.env` 파일을 사용하여 설정합니다.

```env
API_ID=your_telegram_api_id
API_HASH=your_telegram_api_hash
TELEGRAM_BOT_TOKEN=your_bot_token

# BlackList Settings
BLACKLIST_TARGET_URL=http://dool.co.kr/blacklist/create
BLACKLIST_SOURCE_CHAT_ID=@pc365_112
GEMINI_API_KEY=your_gemini_key

# Market Settings
MARKET_TARGET_URL=https://dool.co.kr/api
MARKET_SOURCE_CHAT_ID=holempub_adultpc
```

---

## 3. Automation with Crontab (Crontab 자동화)

크롤러를 주기적으로 자동 실행하려면 `crontab`을 사용합니다.

### Crontab Editor 열기
```bash
crontab -e
```

### 설정 예시
매 정각마다 크롤러를 실행하도록 설정합니다. (경로는 실제 경로로 수정하세요)

```bash
# BlackList Crawler (Non-interactive mode with -y)
0 * * * * cd /home/sentimentalhoon/crawlerbot/BlackList && /home/sentimentalhoon/crawlerbot/venv/bin/python3 main.py -y >> /home/sentimentalhoon/crawlerbot/BlackList/cron.log 2>&1

# Market Crawler
30 * * * * cd /home/sentimentalhoon/crawlerbot/Market && /home/sentimentalhoon/crawlerbot/venv/bin/python3 main_market.py >> /home/sentimentalhoon/crawlerbot/Market/cron.log 2>&1
```

> **Note:** `BlackList/main.py` 실행 시 `-y` 또는 `--yes` 플래그를 추가해야 "y/n" 확인 절차 없이 자동으로 등록됩니다.

---

## 4. Manual Execution (수동 실행)

```bash
# BlackList
cd BlackList
python3 main.py    # Interactive mode
python3 main.py -y # Auto-confirm mode

# Market
cd Market
python3 main_market.py
```