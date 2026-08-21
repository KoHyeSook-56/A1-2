# Travel Planner

LLM API(OpenAI)와 지도/장소 검색 API(Kakao Local)를 활용하여 날짜 기반 국내 여행지를 추천하고 맛집 정보를 포함한 여행 리포트를 자동 생성하는 CLI 기반 Python 프로그램입니다.

## 주요 기능
- **여행지 추천**: 입력한 날짜에 가기 좋은 국내 여행지를 추천합니다 (날씨, 축제 정보 포함).
- **맛집 검색**: 추천된 여행지 주변의 맛집 5곳을 자동 검색합니다.
- **여행 리포트 생성**: Markdown 형식으로 최종 여행 일정 리포트를 작성합니다.
- **결과 캐싱**: 동일한 날짜로 재실행 시 기존 검색 데이터를 재사용하여 API 호출 비용을 절감합니다.

## 실행 방법

### 1. 패키지 설치
Python 3.10 이상 환경에서 다음 명령어를 실행하여 필요한 패키지를 설치합니다.
```bash
pip install -r requirements.txt
```

### 2. API 키 설정 (보안 주의)
프로그램 실행을 위해 API 키가 필요합니다. 코드를 수정하지 않고 환경변수를 통해 안전하게 키를 관리합니다.

프로젝트 루트 디렉토리에 `.env` 파일을 생성하고 다음 내용을 작성하세요:
```env
OPENAI_API_KEY=your_openai_api_key_here
KAKAO_REST_API_KEY=your_kakao_rest_api_key_here
```
> [!WARNING]
> `.env` 파일은 절대 Git이나 외부로 유출되지 않도록 주의하세요! (이미 `.gitignore`에 포함되어 있습니다.)

### 3. 프로그램 실행
다음 명령어를 통해 프로그램을 실행합니다. `-date` 옵션은 필수입니다.
```bash
python travel_planner.py --date "2026-10-15"
```

## 결과 확인
실행이 완료되면 `results/` 폴더 내에 두 개의 파일이 생성됩니다.
1. `YYYY-MM-DD_data.json`: LLM 추천 및 맛집 검색 API 호출 결과 (원본 데이터)
2. `YYYY-MM-DD_travel_plan.md`: 최종 생성된 마크다운 여행 리포트

> [!TIP]
> API 장애(네트워크 오류 등)나 검색 결과가 없더라도 프로그램은 중단되지 않으며, 마크다운 리포트 하단에 오류 내용이 기재되어 생성됩니다.
