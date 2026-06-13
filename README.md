# Evolving Agent Platform (EAP)

> **나를 기억하고, 쓸수록 나에게 맞게 진화하는 AI 동반자.**
> `evolving_companion`은 사용자의 대화 스타일·데이터 포맷·작업 습관을 장기 기억에 축적하고,
> 매 작업마다 자기비평을 거쳐 더 잘 맞게 진화합니다. 큰 작업은 *필요할 때* 하위 에이전트를 꾸려 처리합니다.

**핵심은 "축적되고 진화하는 사용자 맥락"입니다.** — 멀티 LLM 시대에 서비스마다 끊기는 맥락을, 사용자에게 귀속된 기억으로 이어 붙이는 게 목표입니다. (상위 비전: UCOS / Universal Context Layer)

---

## 🎯 무엇을 해결하나

| 문제 | EAP의 해법 |
|---|---|
| **기억의 단절** — 세션·서비스가 바뀌면 내 스타일·맥락이 매번 초기화됨 | `.agents/user_profile.md`에 사용자 스타일·포맷·습관을 **장기 기억**으로 축적. 다음에도, 다른 작업에서도 그대로 이어짐 |
| **고정된 도구** — 쓸수록 나아지지 않고 늘 똑같음 | 매 작업 종료 시 **자기비평 → 진화**. `Current Evolved Standards` 갱신 + `Evolution Log` 기록으로 점점 더 나에게 맞춰짐 |
| **개인화의 깊이** — 단순 설정값이 아니라 "나를 아는" 수준 | 누적된 맥락이 곧 해자(moat). 흉내 낼 수 없는 건 기능이 아니라 **그 사용자에 대해 쌓인 기억** |

> 하위 에이전트 스폰(오케스트레이션)은 이 기억을 *활용하는* 부수 능력이지, 핵심이 아닙니다. 누구나 만들 수 있는 건 차별점이 못 됩니다.

---

## ⚙️ 어떻게 돌아가나 (동작 원리)

중심은 **기억 → 정렬 → 작업 → 자기비평 → 진화**의 루프입니다.

```
                  ┌──────────────────────────────────────────────┐
                  │           .agents/user_profile.md            │
                  │   (장기 기억: 스타일 · 포맷 · 습관 · 표준)     │
                  └───────▲──────────────────────────┬───────────┘
                  ④ 진화   │                          │ ① 읽고 정렬
                  (자기비평)│                          ▼
    사용자 ─────►  ┌───────┴──────────────────────────────────┐
     태스크       │           evolving_companion              │
                  │  ② 기억에 맞춰 작업 수행                   │
                  │  ③ (대형 작업 한정) 하위 에이전트 구성     │  ← 부수 능력
                  │       scraper_agent / parser_agent ...    │
                  └───────────────────┬──────────────────────┘
                                      ▼
                              사용자에게 보고
```

**처리 흐름**

1. **기억 정렬 (핵심)** — 작업 시작 시 `.agents/user_profile.md`를 읽어(없으면 생성) 사용자의 언어·톤·출력 포맷·코딩 스타일에 자신을 맞춤. *매번 다시 설명할 필요가 없음.*
2. **맞춤 수행** — 기억에 정렬된 상태로 작업을 처리.
3. **(대형 작업 한정) 하위 팀 구성** — 작업이 클 때만 `define_subagent`/`invoke_subagent`로 전용 하위 에이전트를 꾸려 협업. 작은 작업은 직접 처리.
4. **자가 진화 (핵심)** — 작업 종료 시 자기비평: 이번 산출이 과거보다 나아졌나? `## Current Evolved Standards`를 갱신하고 `## Evolution Log`에 날짜·근거를 append. **쓸수록 더 잘 맞아짐.**
5. **관측 (선택)** — 진행·상태·비용을 백엔드 write-back 엔드포인트로 기록하면 Next.js 대시보드에 반영.

---

## 💡 실제 사용 시 이점

- **나를 기억한다** — 스타일·포맷·습관을 다시 설명할 필요가 없음. 세션·작업이 바뀌어도 맥락이 이어짐.
- **쓸수록 좋아진다** — 자기비평·진화 루프로 산출물이 점점 내 취향에 수렴. 고정된 도구가 아니라 *자라는* 동반자.
- **맥락이 내게 귀속된다** — 기억은 `user_profile.md`라는 사용자 소유 파일에 쌓임. 특정 서비스에 갇히지 않음.
- **필요할 때만 똑똑하게 분업** — 큰 작업은 하위 팀을 꾸려 처리하되, 그 판단도 *나를 아는* 상태에서 이뤄짐.
- **투명·재현 가능** — 진화 이력(Evolution Log)과 에이전트 정의가 모두 파일로 남아 추적·재현 가능.

### 적용 예시
- 내 코딩 스타일/데이터 포맷을 기억해 일관된 산출물을 계속 생성
- 반복 업무에서 피드백을 학습해 점점 더 손이 덜 가게 만듦
- 다단계 작업(수집→정제→리포트)을 *내 기준에 맞춰* 하위 팀이 처리

---

## 🧱 기술 스택

| 영역 | 스택 |
|---|---|
| **기억 / 진화 (핵심)** | `.agents/user_profile.md` — 장기 기억 + 자기비평 진화 루프 |
| **Companion 에이전트** | Antigravity `evolving_companion` (개인화 + 자가진화) |
| 보조 능력 (오케스트레이션) | `define_subagent` / `invoke_subagent` / `manage_subagents` |
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0, SQLite — 영속·관측 계층 (LLM 미호출) |
| Frontend | Next.js (App Router), TypeScript, TailwindCSS |

---

## 🚀 사용 방법

### 1. Companion 로드 (Antigravity)

서브에이전트 정의는 재시작 시 소실되므로, 새 세션마다 레포의 정의를 다시 등록합니다.

```
이 레포의 antigravity/agents/evolving_companion/agent.json 정의로
evolving_companion 서브에이전트를 define_subagent로 등록하고,
작업 시작 시 .agents/user_profile.md를 읽어 내 스타일에 맞추고,
작업이 끝나면 자기비평으로 그 기억을 갱신하도록 해.
```

자세한 동작/로드 설명은 [`antigravity/README.md`](antigravity/README.md) 참고.

### 2. (선택) 관측 백엔드 — FastAPI

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload      # http://localhost:8000 (docs: /docs)
```

### 3. (선택) 대시보드 — Next.js

```bash
cd frontend
npm install
npm run dev                    # http://localhost:3000
```

---

## 📡 API 엔드포인트 (관측 계층)

| Method | Path | 설명 |
|---|---|---|
| `GET` | `/api/settings` | 시스템 설정 조회 |
| `POST` | `/api/settings` | 시스템/학습 ON·OFF 토글 |
| `POST` | `/api/tasks` | 새 Task 생성 (companion에 위임, `delegated`) |
| `GET` | `/api/tasks/{id}` | Task 상태 조회 |
| `POST` | `/api/tasks/{id}/resume` | 일시정지/실패 Task 재처리 위임 |
| `GET` | `/api/tasks/{id}/logs` · `/costs` | 로그 · 비용 조회 |
| `POST` | `/api/tasks/{id}/status` · `/logs` · `/costs` | **(write-back)** 에이전트가 진행상황 보고 |

---

## 🗺️ 로드맵

- [x] **자가 진화 기억 루프** — `user_profile.md` 기반 개인화 + 자기비평 진화 (핵심)
- [x] **기억·에이전트 정의 버전 관리** — `antigravity/`에 체크인해 재시작 소실 방지
- [x] **보조 능력: 자율 오케스트레이션** — 대형 작업 시 하위 에이전트 스폰
- [x] **관측 write-back 엔드포인트** — 진행상황을 대시보드에 반영
- [ ] **기억의 구조화·벡터화** — 빈도 기반 강화 / decay / 의미 검색 (`chromadb` 준비됨)
- [ ] **서비스 간 맥락 이동** — `user_profile.md`를 다른 AI 도구로 이식 (UCL 비전)
- [ ] **Stage B 제품화** — 기억·진화 로직을 백엔드로 흡수해 Antigravity 비의존 독립 제품화

---

## 📂 프로젝트 구조

```
evolving-agent-platform/
├── antigravity/                          # 🧠 기억 · 진화 · companion (핵심)
│   ├── agents/evolving_companion/
│   │   └── agent.json                    # companion 정의 (개인화+자가진화, 오케스트레이션은 보조)
│   ├── user_profile.template.md          # 장기기억 템플릿
│   └── README.md                         # 동작 설명
├── backend/                              # 영속·관측 계층 (Stage B 후보)
│   ├── main.py · orchestrator.py · models.py · schemas.py · database.py
│   └── requirements.txt
├── frontend/                             # EvoAgent Console 대시보드
│   └── src/app/page.tsx · src/lib/api.ts
├── docs/cursor_tasks/                    # 감독관-워커 작업 지시서
├── CLAUDE.md                             # Claude Code 개발 규칙
└── EAP_CONTEXT.md                        # 아키텍처 인수인계 문서
```

자세한 결정 이력은 [`EAP_CONTEXT.md`](EAP_CONTEXT.md), companion 상세는 [`antigravity/README.md`](antigravity/README.md) 참고.
