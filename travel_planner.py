import os
import sys
import argparse
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="국내 여행지 추천 프로그램"
    )
    parser.add_argument(
        "-date",
        "--date",
        required=True,
        help="여행 날짜를 YYYY-MM-DD 형식으로 입력하세요."
    )
    args = parser.parse_args()

    try:
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        parser.error("날짜 형식은 YYYY-MM-DD 형식이어야 합니다.")

    return args

def check_api_keys():
    missing_keys = []
    if not GEMINI_API_KEY:
        missing_keys.append("GEMINI_API_KEY")
    if not KAKAO_REST_API_KEY:
        missing_keys.append("KAKAO_REST_API_KEY")
    if missing_keys:
        print("오류: API 키가 설정되지 않았습니다.")
        print("누락된 키:", ", ".join(missing_keys))
        print("\n.env 파일에 API 키를 설정하세요.")
        sys.exit(1)

def get_llm_recommendation(date_str, client):
    prompt = f"""
여행 날짜: {date_str}
위 날짜에 가기 좋은 국내 여행지를 1곳 추천해주세요.
반드시 아래 JSON 형식으로만 응답해야 합니다. 다른 말은 추가하지 마세요.
{{
  "recommended_city": "도시 이름 (예: 제주, 강릉)",
  "weather": "해당 시기 일반적 날씨 요약",
  "events": ["행사/축제 후보 1", "행사/축제 후보 2"],
  "reason": "추천 근거 2~4문장"
}}
"""
    try:
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                system_instruction="You are a helpful travel assistant. Always reply with valid JSON."
            )
        )
        content = response.text
        return json.loads(content)
    except Exception as e:
        print(f"LLM 1차 추천 오류: {e}")
        return None

def get_kakao_restaurants(city):
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {
        "Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"
    }
    params = {
        "query": f"{city} 맛집",
        "size": 5
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        places = data.get("documents", [])
        
        results = []
        for p in places:
            results.append({
                "name": p.get("place_name", ""),
                "address": p.get("road_address_name", p.get("address_name", "")),
                "category": p.get("category_name", ""),
                "url": p.get("place_url", ""),
                "x": float(p.get("x", 0)),
                "y": float(p.get("y", 0))
            })
        return results, None
    except Exception as e:
        error_msg = f"HTTP {getattr(e.response, 'status_code', 'Unknown')}" if hasattr(e, 'response') else str(e)
        return [], {"step": "place_search", "type": "API_ERROR", "message": error_msg}

def generate_llm_report(date_str, recommendation, restaurants, client):
    prompt = f"""
다음 여행 정보를 바탕으로 Markdown 형식의 여행 리포트를 작성해주세요.

여행 날짜: {date_str}
추천 지역: {recommendation.get('recommended_city')}
추천 이유: {recommendation.get('reason')}
날씨: {recommendation.get('weather')}
행사/축제: {', '.join(recommendation.get('events', []))}

맛집 리스트:
"""
    if not restaurants:
        prompt += "데이터 없음 (장소 검색 결과 0건)\n"
    else:
        for r in restaurants:
            prompt += f"- {r.get('name')} ({r.get('category')}): {r.get('address')} [링크]({r.get('url')})\n"
            
    prompt += """
리포트 양식:
# YYYY-MM-DD 국내 여행 추천 리포트
## 추천 지역
## 추천 이유
## 날씨 요약
## 행사/축제
## 맛집 추천
## 1일 일정 제안 (오전/오후/저녁)
"""

    try:
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="You are a helpful travel assistant writing Markdown reports."
            )
        )
        return response.text
    except Exception as e:
        print(f"LLM 2차 리포트 생성 오류: {e}")
        return None

def main():
    args = parse_arguments()
    check_api_keys()

    os.makedirs("results", exist_ok=True)
    json_path = f"results/{args.date}_data.json"
    md_path = f"results/{args.date}_travel_plan.md"

    client = genai.Client(api_key=GEMINI_API_KEY)

    # 1. 1차 추천 및 맛집 검색 (캐싱 적용)
    data = None
    if os.path.exists(json_path):
        print(f"[알림] {json_path} 파일이 이미 존재합니다. 캐시된 데이터를 사용합니다.")
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        print("[1/3] 1차 추천 생성 중(LLM)...")
        # 실패 시 1회 재시도 로직
        recommendation = get_llm_recommendation(args.date, client)
        if not recommendation:
            print("  - 재시도 중...")
            recommendation = get_llm_recommendation(args.date, client)
            
        errors = []
        if recommendation:
            print(f"  - recommended_city: {recommendation.get('recommended_city', '알 수 없음')}")
            
            print("[2/3] 맛집 검색 중(지도/장소 API)...")
            restaurants, error = get_kakao_restaurants(recommendation.get('recommended_city'))
            if error:
                print(f"  - 검색 실패: {error['message']}")
                errors.append(error)
            elif not restaurants:
                print("  - 검색 결과 0건")
                errors.append({"step": "place_search", "type": "EMPTY_RESULT", "message": "0 results"})
            else:
                print(f"  - 맛집 {len(restaurants)}곳 검색 완료")
        else:
            print("  - 1차 추천 실패. 진행할 수 없습니다.")
            errors.append({"step": "llm_recommendation", "type": "PARSE_ERROR", "message": "Failed to parse JSON"})
            recommendation = {}
            restaurants = []

        data = {
            "recommendation": recommendation,
            "restaurants": restaurants,
            "errors": errors
        }
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # 2. 최종 리포트 생성
    if data and data.get("recommendation"):
        print("[3/3] 최종 리포트 생성 중(LLM)...")
        report = generate_llm_report(args.date, data["recommendation"], data.get("restaurants", []), client)
        
        if report:
            # 오류 내역 추가
            if data.get("errors"):
                report += "\n\n## 오류 요약(errors)\n"
                for err in data["errors"]:
                    report += f"- [{err.get('step')}] {err.get('type')}: {err.get('message')}\n"
            
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"\n완료! {md_path} 를 확인하세요.")
        else:
            print("\n최종 리포트 생성에 실패했습니다.")
    else:
        print("\n유효한 추천 데이터가 없어 리포트를 생성할 수 없습니다.")

if __name__ == "__main__":
    main()