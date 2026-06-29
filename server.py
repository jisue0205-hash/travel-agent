#!/usr/bin/env python3
"""
여행 계획 에이전트 웹 서버
실행: python3 server.py
접속: http://localhost:8000
"""

import json
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from travel_agent import (
    plan_trip, STEPS,
    extract_trip_details, search_flights, search_hotels,
    get_attractions, get_weather_info, estimate_budget, synthesize_plan
)

app = FastAPI(title="AI Travel Planning Agent")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class TravelRequest(BaseModel):
    request: str


def sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def stream_plan(user_request: str):
    """단계별로 SSE 이벤트를 yield하며 여행 계획을 생성합니다."""
    yield sse({"type": "start", "message": "여행 계획 수립을 시작합니다..."})

    try:
        steps_label = dict(STEPS)

        # 콜백으로 SSE 이벤트 전송 불가 → 직접 단계별 실행
        yield sse({"type": "tool_start", "tool": "extract", "label": steps_label["extract"]})
        details = extract_trip_details(user_request)
        yield sse({"type": "tool_done",  "tool": "extract", "label": steps_label["extract"]})

        yield sse({"type": "tool_start", "tool": "flights", "label": steps_label["flights"]})
        flights = search_flights(details)
        yield sse({"type": "tool_done",  "tool": "flights", "label": steps_label["flights"]})

        yield sse({"type": "tool_start", "tool": "hotels", "label": steps_label["hotels"]})
        hotels = search_hotels(details)
        yield sse({"type": "tool_done",  "tool": "hotels", "label": steps_label["hotels"]})

        yield sse({"type": "tool_start", "tool": "attractions", "label": steps_label["attractions"]})
        attractions = get_attractions(details)
        yield sse({"type": "tool_done",  "tool": "attractions", "label": steps_label["attractions"]})

        yield sse({"type": "tool_start", "tool": "weather", "label": steps_label["weather"]})
        weather = get_weather_info(details)
        yield sse({"type": "tool_done",  "tool": "weather", "label": steps_label["weather"]})

        yield sse({"type": "tool_start", "tool": "budget", "label": steps_label["budget"]})
        budget = estimate_budget(details, flights, hotels)
        yield sse({"type": "tool_done",  "tool": "budget", "label": steps_label["budget"]})

        yield sse({"type": "tool_start", "tool": "synthesize", "label": steps_label["synthesize"]})
        plan = synthesize_plan(details, flights, hotels, attractions, weather, budget)
        yield sse({"type": "tool_done",  "tool": "synthesize", "label": steps_label["synthesize"]})

        yield sse({"type": "result", "content": plan})
        yield sse({"type": "done"})

    except Exception as e:
        yield sse({"type": "error", "message": str(e)})


@app.post("/api/plan/stream")
def plan_stream(body: TravelRequest):
    return StreamingResponse(
        stream_plan(body.request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI 여행 계획 에이전트</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <style>
    body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; }
    .spinner { animation: spin 1s linear infinite; }
    @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
    .fade-in { animation: fadeIn 0.35s ease; }
    .result-content h1 { font-size: 1.5rem; font-weight: 700; margin: 1.25rem 0 0.5rem; color: #111827; }
    .result-content h2 { font-size: 1.2rem; font-weight: 600; margin: 1.25rem 0 0.4rem; color: #1f2937; }
    .result-content h3 { font-size: 1.05rem; font-weight: 600; margin: 1rem 0 0.3rem; color: #374151; }
    .result-content p { margin-bottom: 0.75rem; line-height: 1.7; }
    .result-content ul, .result-content ol { margin: 0.25rem 0 0.75rem 1.5rem; }
    .result-content li { margin-bottom: 0.3rem; line-height: 1.6; }
    .result-content strong { font-weight: 600; color: #111827; }
    .result-content table { border-collapse: collapse; width: 100%; margin-bottom: 1rem; font-size: 0.9rem; }
    .result-content th, .result-content td { border: 1px solid #e5e7eb; padding: 0.5rem 0.75rem; }
    .result-content th { background: #f9fafb; font-weight: 600; }
    .result-content hr { border: none; border-top: 1px solid #e5e7eb; margin: 1.25rem 0; }
    .result-content blockquote { border-left: 3px solid #3b82f6; padding-left: 1rem; color: #4b5563; margin: 0.75rem 0; }
    .result-content code { background: #f3f4f6; padding: 0.1rem 0.35rem; border-radius: 4px; font-size: 0.875em; }
  </style>
</head>
<body class="bg-gray-50 min-h-screen">
  <div class="max-w-2xl mx-auto px-4 py-10">

    <div class="text-center mb-10">
      <div class="text-5xl mb-3">✈️</div>
      <h1 class="text-3xl font-bold text-gray-800 mb-2">AI 여행 계획 에이전트</h1>
      <p class="text-gray-500 text-sm">Claude AI가 항공편 · 숙소 · 일정 · 날씨 · 예산을 한 번에 계획합니다</p>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-5">
      <label class="block text-sm font-medium text-gray-700 mb-2">여행 요청</label>
      <textarea
        id="request"
        class="w-full border border-gray-200 rounded-xl px-4 py-3 text-gray-800 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition text-sm"
        rows="3"
        placeholder="예: 서울에서 도쿄 3박 4일, 10월, 예산 150만원, 맛집과 관광지 위주로..."
      ></textarea>

      <div class="mt-3 flex flex-wrap gap-2 items-center">
        <span class="text-xs text-gray-400">예시</span>
        <button onclick="setExample(0)" class="text-xs bg-blue-50 text-blue-600 hover:bg-blue-100 px-3 py-1.5 rounded-full transition">🗼 도쿄 3박 4일</button>
        <button onclick="setExample(1)" class="text-xs bg-blue-50 text-blue-600 hover:bg-blue-100 px-3 py-1.5 rounded-full transition">🌴 방콕 7일 혼자</button>
        <button onclick="setExample(2)" class="text-xs bg-blue-50 text-blue-600 hover:bg-blue-100 px-3 py-1.5 rounded-full transition">🗼 파리 커플 5일</button>
      </div>

      <button
        id="submit-btn"
        onclick="planTrip()"
        class="mt-4 w-full bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-semibold py-3 px-6 rounded-xl transition disabled:opacity-50 disabled:cursor-not-allowed text-sm"
      >
        여행 계획 세우기
      </button>
    </div>

    <div id="progress-section" class="hidden bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-5 fade-in">
      <div class="flex items-center gap-3 mb-4">
        <svg id="loading-icon" class="spinner w-4 h-4 text-blue-500 flex-shrink-0" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
        <span id="status-text" class="text-sm font-medium text-gray-700">준비 중...</span>
      </div>
      <div id="steps" class="space-y-2 pl-1"></div>
    </div>

    <div id="result-section" class="hidden bg-white rounded-2xl shadow-sm border border-gray-100 p-6 fade-in">
      <div class="flex items-center gap-2 mb-5 pb-4 border-b border-gray-100">
        <span class="text-xl">📋</span>
        <h2 class="text-base font-semibold text-gray-800">여행 계획서</h2>
      </div>
      <div id="result-content" class="result-content text-gray-700 text-sm leading-relaxed"></div>
    </div>

  </div>

  <script>
    const EXAMPLES = [
      "서울에서 도쿄 3박 4일 여행 계획 세워줘. 10월 여행이고 예산은 150만원이야. 맛집과 관광지 위주로 부탁해.",
      "방콕 7일 혼자 여행 계획. 7월 출발, 예산 100만원. 사원, 야시장, 현지 음식 위주로 알려줘.",
      "파리 5일 커플 여행 계획. 내년 4월, 예산 $6000. 미술관, 로맨틱 스팟 위주로."
    ];

    const STEP_ICONS = {
      'extract':     '🔍',
      'flights':     '✈️',
      'hotels':      '🏨',
      'attractions': '🗺️',
      'weather':     '🌤️',
      'budget':      '💰',
      'synthesize':  '📝'
    };

    function setExample(idx) {
      document.getElementById('request').value = EXAMPLES[idx];
      document.getElementById('request').focus();
    }

    async function planTrip() {
      const request = document.getElementById('request').value.trim();
      if (!request) { alert('여행 요청을 입력해주세요.'); return; }

      const submitBtn   = document.getElementById('submit-btn');
      const progressSec = document.getElementById('progress-section');
      const resultSec   = document.getElementById('result-section');
      const steps       = document.getElementById('steps');
      const statusText  = document.getElementById('status-text');
      const loadingIcon = document.getElementById('loading-icon');

      submitBtn.disabled = true;
      submitBtn.textContent = '계획 수립 중...';
      progressSec.classList.remove('hidden');
      resultSec.classList.add('hidden');
      steps.innerHTML = '';
      loadingIcon.classList.remove('hidden');
      statusText.textContent = '시작 중...';

      try {
        const res = await fetch('/api/plan/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ request })
        });

        const reader  = res.body.getReader();
        const decoder = new TextDecoder();
        let   buffer  = '';

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\\n');
          buffer = lines.pop();
          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            try {
              const ev = JSON.parse(line.slice(6));
              handleEvent(ev, steps, statusText, loadingIcon, resultSec);
            } catch (_) {}
          }
        }
      } catch (err) {
        statusText.textContent = '오류: ' + err.message;
        loadingIcon.classList.add('hidden');
      }

      submitBtn.disabled = false;
      submitBtn.textContent = '여행 계획 세우기';
    }

    function handleEvent(ev, steps, statusText, loadingIcon, resultSec) {
      if (ev.type === 'start') {
        statusText.textContent = ev.message;

      } else if (ev.type === 'tool_start') {
        const icon  = STEP_ICONS[ev.tool] || '•';
        const el = document.createElement('div');
        el.id = 'step-' + ev.tool;
        el.className = 'flex items-center gap-2 text-xs text-gray-500';
        el.innerHTML = `
          <svg class="spinner w-3.5 h-3.5 text-blue-400 flex-shrink-0" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
          </svg>
          <span>${icon} ${ev.label}</span>
        `;
        steps.appendChild(el);
        statusText.textContent = ev.label + '...';

      } else if (ev.type === 'tool_done') {
        const icon = STEP_ICONS[ev.tool] || '•';
        const el = document.getElementById('step-' + ev.tool);
        if (el) {
          el.innerHTML = `
            <span class="text-green-500 text-sm flex-shrink-0">✓</span>
            <span class="text-gray-400">${icon} ${ev.label}</span>
          `;
        }

      } else if (ev.type === 'result') {
        resultSec.classList.remove('hidden');
        document.getElementById('result-content').innerHTML = marked.parse(ev.content);

      } else if (ev.type === 'done') {
        loadingIcon.classList.add('hidden');
        statusText.textContent = '✅ 여행 계획 완성!';

      } else if (ev.type === 'error') {
        statusText.textContent = '오류: ' + ev.message;
        loadingIcon.classList.add('hidden');
      }
    }
  </script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML


if __name__ == "__main__":
    import uvicorn, os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
