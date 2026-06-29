#!/usr/bin/env python3
"""
AI 여행 계획 에이전트
- 로컬: ANTHROPIC_API_KEY 환경변수 또는 .env 파일
- 배포: Render 환경변수로 설정
"""

import json
import os
from dotenv import load_dotenv
load_dotenv()

import anthropic

client = anthropic.Anthropic()
MODEL = "claude-opus-4-8"


def call_claude(prompt: str) -> str:
    """Claude API를 호출하고 텍스트 응답을 반환합니다."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


# ─── 개별 도구 함수 ──────────────────────────────────────────────

def extract_trip_details(request: str) -> dict:
    response = call_claude(f"""
다음 여행 요청에서 정보를 추출해서 JSON으로만 응답하세요. 마크다운 없이.

요청: "{request}"

형식:
{{
  "origin": "출발 도시 (없으면 '서울')",
  "destination": "목적지 도시",
  "destination_en": "목적지 영문 이름",
  "departure_date": "YYYY-MM-DD (없으면 2개월 후)",
  "return_date": "YYYY-MM-DD (없으면 departure_date + duration_days)",
  "duration_days": 숫자,
  "nights": 숫자,
  "passengers": 숫자,
  "budget_krw": 숫자 또는 null,
  "budget_usd": 숫자 또는 null,
  "interests": ["관심사1", "관심사2"],
  "travel_month": "월 이름 (예: 10월)"
}}
""")
    try:
        text = response.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return {
            "origin": "서울", "destination": "도쿄", "destination_en": "Tokyo",
            "departure_date": "2026-09-01", "return_date": "2026-09-04",
            "duration_days": 4, "nights": 3, "passengers": 1,
            "budget_krw": 1500000, "budget_usd": None,
            "interests": ["관광", "음식"], "travel_month": "9월"
        }


def search_flights(details: dict) -> str:
    budget_info = ""
    if details.get("budget_krw"):
        budget_info = f"총 예산 {details['budget_krw']:,}원 중 항공료 포함"
    elif details.get("budget_usd"):
        budget_info = f"총 예산 ${details['budget_usd']} 중 항공료 포함"

    return call_claude(f"""
{details['origin']}에서 {details['destination']}까지 항공편 3가지 옵션을 제안해주세요.
- 출발일: {details['departure_date']}
- 귀국일: {details['return_date']}
- 인원: {details['passengers']}명
- {budget_info}

현실적인 항공사, 편명, 시간, 가격을 포함하여 표 형식으로 정리해주세요.
""")


def search_hotels(details: dict) -> str:
    return call_claude(f"""
{details['destination']}에서 {details['nights']}박 숙소 3가지를 추천해주세요.
- 체크인: {details['departure_date']}
- 체크아웃: {details['return_date']}
- 인원: {details['passengers']}명
- 여행 성격: {', '.join(details.get('interests', ['일반 관광']))}

각 숙소의 이름, 위치, 특징, 1박 가격(원화 포함)을 알려주세요.
""")


def get_attractions(details: dict) -> str:
    interests = ', '.join(details.get('interests', ['일반 관광']))
    return call_claude(f"""
{details['destination']} {details['duration_days']}일 일정을 계획해주세요.
- 관심사: {interests}
- 인원: {details['passengers']}명

일별 상세 일정 (오전/오후/저녁), 추천 맛집, 쇼핑 장소, 실용적인 팁을 포함해주세요.
""")


def get_weather_info(details: dict) -> str:
    return call_claude(f"""
{details['destination']}의 {details['travel_month']} 날씨를 알려주세요.
평균 기온, 강수량, 옷차림 추천, 여행 시 주의사항을 포함해주세요.
""")


def estimate_budget(details: dict, flights_info: str, hotels_info: str) -> str:
    budget_str = ""
    if details.get("budget_krw"):
        budget_str = f"총 예산: {details['budget_krw']:,}원"
    elif details.get("budget_usd"):
        budget_str = f"총 예산: ${details['budget_usd']}"

    return call_claude(f"""
다음 여행의 예산을 분석해주세요:
- 목적지: {details['destination']}
- 기간: {details['nights']}박 {details['duration_days']}일
- 인원: {details['passengers']}명
- {budget_str}

항공 정보: {flights_info[:300]}...
숙소 정보: {hotels_info[:300]}...

항목별 예상 비용 (항공료, 숙박비, 식비, 관광/입장료, 교통비, 기타)과
총 예산 대비 평가를 원화와 달러로 정리해주세요.
""")


def synthesize_plan(details: dict, flights: str, hotels: str,
                    attractions: str, weather: str, budget: str) -> str:
    return call_claude(f"""
다음 정보를 바탕으로 완성도 높은 여행 계획서를 마크다운 형식으로 작성해주세요.

## 여행 기본 정보
- 출발지: {details['origin']} → 목적지: {details['destination']}
- 기간: {details['departure_date']} ~ {details['return_date']} ({details['nights']}박 {details['duration_days']}일)
- 인원: {details['passengers']}명

## 수집된 정보

### 항공편
{flights}

### 숙소
{hotels}

### 관광 일정
{attractions}

### 날씨
{weather}

### 예산
{budget}

위 정보를 바탕으로 추천 항공편, 추천 숙소, 일별 상세 일정, 예산 요약, 여행 팁을 포함한
실용적이고 완성도 높은 여행 계획서를 작성해주세요.
""")


# ─── 메인 에이전트 루프 ───────────────────────────────────────────

STEPS = [
    ("extract",     "여행 정보 분석 중"),
    ("flights",     "항공편 검색 중"),
    ("hotels",      "숙소 검색 중"),
    ("attractions", "관광 일정 계획 중"),
    ("weather",     "날씨 정보 수집 중"),
    ("budget",      "예산 계산 중"),
    ("synthesize",  "여행 계획서 작성 중"),
]


def plan_trip(user_request: str, on_step=None):
    def notify(step_id, status):
        if on_step:
            on_step(step_id, status)

    notify("extract", "start")
    details = extract_trip_details(user_request)
    notify("extract", "done")

    notify("flights", "start")
    flights = search_flights(details)
    notify("flights", "done")

    notify("hotels", "start")
    hotels = search_hotels(details)
    notify("hotels", "done")

    notify("attractions", "start")
    attractions = get_attractions(details)
    notify("attractions", "done")

    notify("weather", "start")
    weather = get_weather_info(details)
    notify("weather", "done")

    notify("budget", "start")
    budget = estimate_budget(details, flights, hotels)
    notify("budget", "done")

    notify("synthesize", "start")
    plan = synthesize_plan(details, flights, hotels, attractions, weather, budget)
    notify("synthesize", "done")

    return plan


def main():
    print("=" * 60)
    print("  AI 여행 계획 에이전트")
    print("=" * 60)
    user_input = input("여행 요청을 입력하세요: ").strip()
    if not user_input:
        user_input = "서울에서 도쿄 3박 4일 여행 계획 세워줘. 10월이고 예산 150만원, 맛집 위주로."

    steps_label = dict(STEPS)

    def on_step(step_id, status):
        label = steps_label.get(step_id, step_id)
        print(f"  [{label}] {'...' if status == 'start' else '완료'}", end="" if status == "start" else "\n", flush=True)

    result = plan_trip(user_input, on_step=on_step)
    print("\n" + "=" * 60)
    print(result)


if __name__ == "__main__":
    main()
