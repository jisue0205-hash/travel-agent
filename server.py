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
<html lang="ko" class="scroll-smooth">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI 여행 플래너</title>
  <link href="https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <style>
    * { font-family: 'Pretendard', 'Segoe UI', system-ui, sans-serif; }

    body { background: #0f172a; min-height: 100vh; }

    /* Gradient hero */
    .hero-bg {
      background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #0f2942 100%);
      position: relative;
      overflow: hidden;
    }
    .hero-bg::before {
      content: '';
      position: absolute;
      width: 600px; height: 600px;
      background: radial-gradient(circle, rgba(56,189,248,0.12) 0%, transparent 70%);
      top: -200px; right: -100px;
      border-radius: 50%;
    }
    .hero-bg::after {
      content: '';
      position: absolute;
      width: 400px; height: 400px;
      background: radial-gradient(circle, rgba(99,102,241,0.1) 0%, transparent 70%);
      bottom: -100px; left: -100px;
      border-radius: 50%;
    }

    /* Animated gradient button */
    .btn-gradient {
      background: linear-gradient(135deg, #0ea5e9, #6366f1);
      background-size: 200% 200%;
      animation: gradientShift 3s ease infinite;
      transition: all 0.3s ease;
      box-shadow: 0 4px 24px rgba(14,165,233,0.35);
    }
    .btn-gradient:hover {
      box-shadow: 0 6px 32px rgba(14,165,233,0.5);
      transform: translateY(-1px);
    }
    .btn-gradient:disabled {
      opacity: 0.6;
      transform: none;
      animation: none;
      cursor: not-allowed;
    }
    @keyframes gradientShift {
      0%   { background-position: 0% 50%; }
      50%  { background-position: 100% 50%; }
      100% { background-position: 0% 50%; }
    }

    /* Glass card */
    .glass {
      background: rgba(255,255,255,0.04);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(255,255,255,0.08);
    }
    .glass-light {
      background: rgba(255,255,255,0.97);
      border: 1px solid rgba(0,0,0,0.06);
    }

    /* Textarea focus glow */
    .input-glow:focus {
      outline: none;
      border-color: #0ea5e9;
      box-shadow: 0 0 0 3px rgba(14,165,233,0.15);
    }

    /* Example cards */
    .example-card {
      cursor: pointer;
      transition: all 0.2s ease;
      border: 1px solid rgba(255,255,255,0.08);
      background: rgba(255,255,255,0.04);
    }
    .example-card:hover {
      background: rgba(14,165,233,0.12);
      border-color: rgba(14,165,233,0.4);
      transform: translateY(-2px);
    }

    /* Step items */
    .step-item { transition: all 0.3s ease; }

    /* Progress bar */
    .progress-bar {
      height: 3px;
      background: linear-gradient(90deg, #0ea5e9, #6366f1);
      border-radius: 2px;
      transition: width 0.4s ease;
    }

    /* Spinner */
    .spinner { animation: spin 0.8s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }

    /* Fade animations */
    @keyframes fadeUp {
      from { opacity: 0; transform: translateY(16px); }
      to   { opacity: 1; transform: translateY(0); }
    }
    .fade-up { animation: fadeUp 0.4s ease forwards; }

    @keyframes pulse-dot {
      0%, 100% { opacity: 1; }
      50%       { opacity: 0.4; }
    }

    /* Result markdown */
    .result-content { color: #1f2937; }
    .result-content h1 { font-size: 1.4rem; font-weight: 800; margin: 1.5rem 0 0.6rem; color: #0f172a;
      padding-bottom: 0.4rem; border-bottom: 2px solid #e0f2fe; }
    .result-content h2 { font-size: 1.15rem; font-weight: 700; margin: 1.25rem 0 0.4rem; color: #0369a1; }
    .result-content h3 { font-size: 1rem; font-weight: 600; margin: 1rem 0 0.3rem; color: #374151; }
    .result-content p  { margin-bottom: 0.7rem; line-height: 1.75; font-size: 0.9rem; }
    .result-content ul, .result-content ol { margin: 0.25rem 0 0.75rem 1.5rem; }
    .result-content li { margin-bottom: 0.35rem; line-height: 1.65; font-size: 0.9rem; }
    .result-content strong { font-weight: 700; color: #0f172a; }
    .result-content table { border-collapse: collapse; width: 100%; margin-bottom: 1rem; font-size: 0.85rem; border-radius: 8px; overflow: hidden; }
    .result-content th { background: #0369a1; color: white; font-weight: 600; padding: 0.6rem 0.85rem; text-align: left; }
    .result-content td { border-bottom: 1px solid #e5e7eb; padding: 0.55rem 0.85rem; }
    .result-content tr:last-child td { border-bottom: none; }
    .result-content tr:nth-child(even) td { background: #f8fafc; }
    .result-content hr { border: none; border-top: 2px solid #e0f2fe; margin: 1.5rem 0; }
    .result-content blockquote { background: #f0f9ff; border-left: 4px solid #0ea5e9; padding: 0.75rem 1rem; border-radius: 0 8px 8px 0; margin: 0.75rem 0; color: #0369a1; font-size: 0.9rem; }
    .result-content code { background: #f1f5f9; padding: 0.15rem 0.4rem; border-radius: 4px; font-size: 0.82em; color: #0369a1; }
  </style>
</head>
<body>

  <!-- Hero Header -->
  <div class="hero-bg px-4 pt-14 pb-12 text-center relative z-10">
    <div class="inline-flex items-center gap-2 bg-white/10 text-sky-300 text-xs font-medium px-3 py-1.5 rounded-full mb-6 border border-white/10">
      <span class="w-1.5 h-1.5 bg-emerald-400 rounded-full" style="animation: pulse-dot 2s ease infinite"></span>
      Claude AI 기반 · 실시간 여행 계획
    </div>
    <h1 class="text-4xl font-extrabold text-white mb-3 tracking-tight">
      AI 여행 플래너
    </h1>
    <p class="text-slate-400 text-sm max-w-md mx-auto leading-relaxed">
      목적지, 날짜, 예산만 말해주세요.<br>
      항공편부터 맛집까지 완벽한 여행 계획을 만들어 드립니다.
    </p>

    <!-- Feature pills -->
    <div class="flex flex-wrap justify-center gap-2 mt-6">
      <span class="text-xs text-slate-400 bg-white/5 border border-white/8 px-3 py-1 rounded-full">✈️ 항공편</span>
      <span class="text-xs text-slate-400 bg-white/5 border border-white/8 px-3 py-1 rounded-full">🏨 숙소</span>
      <span class="text-xs text-slate-400 bg-white/5 border border-white/8 px-3 py-1 rounded-full">🗺️ 일정</span>
      <span class="text-xs text-slate-400 bg-white/5 border border-white/8 px-3 py-1 rounded-full">🌤️ 날씨</span>
      <span class="text-xs text-slate-400 bg-white/5 border border-white/8 px-3 py-1 rounded-full">💰 예산</span>
    </div>
  </div>

  <!-- Main Content -->
  <div class="max-w-2xl mx-auto px-4 pb-16 -mt-2 relative z-10">

    <!-- Input Card -->
    <div class="glass-light rounded-2xl shadow-2xl p-6 mb-4">

      <!-- Destination Examples -->
      <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-3">인기 여행지</p>
      <div class="grid grid-cols-2 gap-2 mb-5">
        <button onclick="setExample(0)" class="example-card rounded-xl p-3 text-left group">
          <div class="flex items-center gap-2.5">
            <span class="text-2xl">🗼</span>
            <div>
              <p class="text-sm font-bold text-white">도쿄</p>
              <p class="text-xs text-slate-400">3박 4일 · 맛집 위주</p>
            </div>
          </div>
        </button>
        <button onclick="setExample(1)" class="example-card rounded-xl p-3 text-left group">
          <div class="flex items-center gap-2.5">
            <span class="text-2xl">🌴</span>
            <div>
              <p class="text-sm font-bold text-white">방콕</p>
              <p class="text-xs text-slate-400">7일 · 혼자 여행</p>
            </div>
          </div>
        </button>
        <button onclick="setExample(2)" class="example-card rounded-xl p-3 text-left group">
          <div class="flex items-center gap-2.5">
            <span class="text-2xl">🗽</span>
            <div>
              <p class="text-sm font-bold text-white">파리</p>
              <p class="text-xs text-slate-400">5일 · 커플 여행</p>
            </div>
          </div>
        </button>
        <button onclick="setExample(3)" class="example-card rounded-xl p-3 text-left group">
          <div class="flex items-center gap-2.5">
            <span class="text-2xl">🏝️</span>
            <div>
              <p class="text-sm font-bold text-white">발리</p>
              <p class="text-xs text-slate-400">5일 · 휴양 위주</p>
            </div>
          </div>
        </button>
      </div>

      <!-- Textarea -->
      <div class="relative">
        <label class="block text-xs font-semibold text-slate-500 uppercase tracking-widest mb-2">직접 입력</label>
        <textarea
          id="request"
          class="input-glow w-full border border-slate-200 rounded-xl px-4 py-3.5 text-slate-800 bg-slate-50 resize-none text-sm leading-relaxed placeholder:text-slate-400 transition-all"
          rows="3"
          placeholder="예: 서울에서 오사카 4박 5일, 11월, 예산 200만원, 온천과 음식 위주로 계획해줘"
        ></textarea>
      </div>

      <button
        id="submit-btn"
        onclick="planTrip()"
        class="btn-gradient mt-4 w-full text-white font-bold py-3.5 px-6 rounded-xl text-sm tracking-wide"
      >
        나만의 여행 계획 만들기 →
      </button>
    </div>

    <!-- Progress Card -->
    <div id="progress-section" class="hidden glass-light rounded-2xl shadow-xl p-6 mb-4 fade-up">
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-2.5">
          <svg id="loading-icon" class="spinner w-4 h-4 text-sky-500 flex-shrink-0" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
          </svg>
          <span id="status-text" class="text-sm font-semibold text-slate-700">준비 중...</span>
        </div>
        <span id="step-counter" class="text-xs text-slate-400 font-medium">0 / 7</span>
      </div>
      <!-- Progress bar -->
      <div class="bg-slate-100 rounded-full mb-4 overflow-hidden">
        <div id="progress-bar" class="progress-bar" style="width: 0%"></div>
      </div>
      <div id="steps" class="space-y-2"></div>
    </div>

    <!-- Result Card -->
    <div id="result-section" class="hidden glass-light rounded-2xl shadow-xl overflow-hidden fade-up">
      <div class="bg-gradient-to-r from-sky-600 to-indigo-600 px-6 py-4 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="text-lg">📋</span>
          <h2 class="text-sm font-bold text-white">여행 계획서 완성</h2>
        </div>
        <button onclick="copyResult()" class="text-xs text-white/70 hover:text-white border border-white/20 hover:border-white/50 px-3 py-1 rounded-full transition">
          복사하기
        </button>
      </div>
      <div class="p-6">
        <div id="result-content" class="result-content leading-relaxed"></div>
      </div>
    </div>

  </div>

  <script>
    const EXAMPLES = [
      "서울에서 도쿄 3박 4일 여행 계획 세워줘. 10월 여행이고 예산은 150만원이야. 스시, 라멘 같은 맛집과 시부야, 아사쿠사 관광 위주로 부탁해.",
      "방콕 7일 혼자 여행 계획. 7월 출발, 예산 100만원. 왓포 사원, 야시장, 팟타이 같은 현지 음식 위주로 알려줘.",
      "파리 5일 커플 여행 계획. 내년 4월, 예산 $6000. 루브르 미술관, 에펠탑, 로맨틱한 카페 위주로.",
      "발리 5일 휴양 여행. 8월, 예산 150만원. 우붓 라이스테라스, 스파, 선셋 위주로."
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

    let completedSteps = 0;
    const TOTAL_STEPS = 7;

    function setExample(idx) {
      document.getElementById('request').value = EXAMPLES[idx];
      document.getElementById('request').focus();
    }

    function copyResult() {
      const text = document.getElementById('result-content').innerText;
      navigator.clipboard.writeText(text).then(() => {
        const btn = event.target;
        btn.textContent = '복사됨 ✓';
        setTimeout(() => btn.textContent = '복사하기', 2000);
      });
    }

    async function planTrip() {
      const request = document.getElementById('request').value.trim();
      if (!request) {
        document.getElementById('request').focus();
        document.getElementById('request').classList.add('border-red-400');
        setTimeout(() => document.getElementById('request').classList.remove('border-red-400'), 2000);
        return;
      }

      const submitBtn   = document.getElementById('submit-btn');
      const progressSec = document.getElementById('progress-section');
      const resultSec   = document.getElementById('result-section');
      const steps       = document.getElementById('steps');
      const statusText  = document.getElementById('status-text');
      const loadingIcon = document.getElementById('loading-icon');
      const progressBar = document.getElementById('progress-bar');
      const stepCounter = document.getElementById('step-counter');

      completedSteps = 0;
      submitBtn.disabled = true;
      submitBtn.textContent = '계획 수립 중...';
      progressSec.classList.remove('hidden');
      resultSec.classList.add('hidden');
      steps.innerHTML = '';
      loadingIcon.classList.remove('hidden');
      statusText.textContent = '분석 시작...';
      progressBar.style.width = '0%';
      stepCounter.textContent = '0 / ' + TOTAL_STEPS;

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
              handleEvent(ev, steps, statusText, loadingIcon, resultSec, progressBar, stepCounter);
            } catch (_) {}
          }
        }
      } catch (err) {
        statusText.textContent = '오류: ' + err.message;
        loadingIcon.classList.add('hidden');
      }

      submitBtn.disabled = false;
      submitBtn.textContent = '나만의 여행 계획 만들기 →';
    }

    function handleEvent(ev, steps, statusText, loadingIcon, resultSec, progressBar, stepCounter) {
      if (ev.type === 'start') {
        statusText.textContent = ev.message;

      } else if (ev.type === 'tool_start') {
        const icon = STEP_ICONS[ev.tool] || '•';
        const el = document.createElement('div');
        el.id = 'step-' + ev.tool;
        el.className = 'flex items-center gap-3 py-1.5 step-item';
        el.innerHTML = `
          <div class="w-6 h-6 flex items-center justify-center flex-shrink-0">
            <svg class="spinner w-4 h-4 text-sky-500" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
            </svg>
          </div>
          <span class="text-xs font-medium text-slate-600">${icon} ${ev.label}</span>
          <span class="ml-auto text-xs text-sky-500 font-medium">진행중</span>
        `;
        steps.appendChild(el);
        statusText.textContent = ev.label + '...';

      } else if (ev.type === 'tool_done') {
        completedSteps++;
        const pct = Math.round((completedSteps / TOTAL_STEPS) * 100);
        progressBar.style.width = pct + '%';
        stepCounter.textContent = completedSteps + ' / ' + TOTAL_STEPS;

        const icon = STEP_ICONS[ev.tool] || '•';
        const el = document.getElementById('step-' + ev.tool);
        if (el) {
          el.innerHTML = `
            <div class="w-6 h-6 flex items-center justify-center bg-emerald-100 rounded-full flex-shrink-0">
              <svg class="w-3.5 h-3.5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
              </svg>
            </div>
            <span class="text-xs font-medium text-slate-400">${icon} ${ev.label}</span>
            <span class="ml-auto text-xs text-emerald-500 font-semibold">완료</span>
          `;
        }

      } else if (ev.type === 'result') {
        resultSec.classList.remove('hidden');
        document.getElementById('result-content').innerHTML = marked.parse(ev.content);
        resultSec.scrollIntoView({ behavior: 'smooth', block: 'start' });

      } else if (ev.type === 'done') {
        loadingIcon.classList.add('hidden');
        statusText.textContent = '✅ 여행 계획 완성!';
        progressBar.style.width = '100%';

      } else if (ev.type === 'error') {
        statusText.textContent = '오류가 발생했습니다: ' + ev.message;
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
