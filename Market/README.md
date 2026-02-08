# Dool.co.kr Crawler Setup Manual

이 문서는 다른 컴퓨터에서 `dool.co.kr` 크롤러를 실행하기 위한 설정 방법을 안내합니다.

## 1. 필수 조건 (Prerequisites)
*   **Python 3.8 이상**이 설치되어 있어야 합니다.
*   **Google Chrome** 브라우저가 설치되어 있어야 합니다.

## 2. 설치 (Installation)

1.  이 폴더(`dool.co.kr`)를 통째로 복사합니다.
2.  명령 프롬프트(CMD) 또는 터미널을 열고 해당 폴더로 이동합니다.
    ```bash
    cd path/to/dool.co.kr
    ```
3.  필요한 라이브러리를 설치합니다.
    ```bash
    pip install -r requirements.txt
    ```

## 3. 환경 설정 (Configuration)

이 크롤러는 **Google Gemini API**를 사용하여 데이터를 분석하므로, API 키 설정이 필수입니다.

1.  폴더 내에 `.env` 파일을 생성합니다. (이미 있다면 수정합니다)
2.  `.env` 파일을 메모장으로 열고 다음과 같이 작성합니다:
    ```env
    GEMINI_API_KEY=Your_Gemini_API_Key_Here
    ```
    *(위 키는 예시입니다. 본인의 실제 키를 입력하세요)*

## 4. 실행 (Usage)

크롤러를 실행하려면 다음 명령어를 입력합니다.

```bash
python main.py
```

*   `main.py`는 `scraper_a.py`를 호출하여 데이터를 수집하고, `poster_b.py`를 통해 지정된 사이트에 게시글을 등록합니다.
*   **주의:** 자동화를 위해 브라우저 창이 뜨거나 백그라운드에서 작업이 수행될 수 있습니다.

## 5. 트러블슈팅 (Troubleshooting)

*   **API Quota Error (429):** 무료 사용량을 초과한 경우입니다. 잠시 기다렸다가 다시 실행하세요.
*   **Chrome Driver Error:** 크롬 브라우저 버전이 너무 구형이거나 최신이어서 드라이버와 맞지 않는 경우, `webdriver-manager`가 자동으로 업데이트를 시도하지만, 실패 시 크롬을 최신 버전으로 업데이트하세요.
