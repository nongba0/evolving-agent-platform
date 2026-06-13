# Evolving Agent Platform (EAP)

> 사용자의 작업 패턴을 학습하며 스스로 진화하는 **자율 멀티 에이전트 플랫폼**.
> 큰 작업이 들어오면 **Antigravity의 `evolving_companion` 에이전트가 스스로 오케스트레이터가 되어**
> 하위 서브에이전트를 동적으로 생성·지시하고, 결과를 취합해 보고하며, 그 과정을 기억해 진화합니다.

**핵심 원칙: 오케스트레이션은 외부 LLM API 호출이 아니라 Antigravity 내부 서브에이전트 협업으로 동작합니다.**

---

## 🎯 무엇을 해결하나

LLM 에이전트를 실제 업무에 쓸 때 반복적으로 부딪히는 문제를 정면으로 다룹니다.

| 문제 | EAP의 해법 |
|---|---|
| **맥락 단절** — 세션이 바뀌면 사용자 스타일·선호가 초기화됨 | `evolving_companion`이 `.agents/user_profile.md`에 사용자 스타일·포맷·습관을 **장기 기억**하고 매 작업 후 **자가 진화** |
| **단일 에이전트 한계** — 복잡한 작업을 한 번에 처리하다 품질 저하 | 작업을 분해해 전용 하위 에이전트(`scraper_agent`, `parser_agent` 등)를 **동적 스폰**해 협업 처리 |
| **불투명성** — 에이전트가 내부에서 뭘 하는지 안 보임 | 어떤 서브에이전트를 스폰했고 무엇을 산출했는지 보고 + 백엔드 Task/Log/Cost 대시보드로 가시화 |

---

## ⚙️ 어떻게 돌아가나 (동작 원리)

오케스트레이션 두뇌는 **Antigravity의 `evolving_companion`** 입니다. ([`antigravity/`](antigravity/) 참고)

```
              ┌────────────────────────────────────────────────────────────┐
  사용자 ────►│            evolving_companion  (자율 오케스트레이터)         │
   대형       │                                                            │
   태스크     │  ① user_profile.md 읽기 → 사용자 스타일/포맷에 정렬         │
             │  ② 태스크 분해 → 하위 서브에이전트 동적 정의·호출           │
             │       define_subagent + invoke_subagent                    │
             │          ├──► scraper_agent  (수집)                         │
             │          └──► parser_agent   (정제/표준화)                  │
             │  ③ 결과 취합·검증 → 사용자에게 보고                         │
             │  ④ 자기비평 → user_profile.md 갱신 (자가 진화)              │
             └───────────────────────────┬────────────────────────────────┘
                                         │  (선택) run_command로 진행상황 보고
                                         ▼
        ┌──────────────┐   write-back    ┌────────────────────────────────┐
        │   Next.js    │ ◄── polling ───  │   FastAPI Backend (영속·관측)   │
        │  Dashboard   │                  │   Task / Log / Cost / Checkpoint │
        └──────────────┘                  └────────────────────────────────┘
```

**처리 흐름**

1. **기억 정렬** — 작업 시작 시 `evolving_companion`이 `.agents/user_profile.md`를 읽어(없으면 생성) 사용자의 언어·톤·출력 포맷·코딩 스타일에 자신을 맞춤.
2. **자율 분해 & 스폰** — 대형 태스크를 독립적인 하위 작업으로 쪼개고, 각 작업마다 `define_subagent`로 전용 하위 에이전트를 정의한 뒤 `invoke_subagent`로 실행. (외부 LLM API로 계획하지 않음 — 에이전트 내부 판단)
3. **취합 & 검증** — 하위 에이전트들의 산출물을 모아 검증하고 최종 결과를 직접 컴파일.
4. **보고** — 어떤 서브에이전트를 스폰했고 각각 무엇을 했는지 구조화된 마크다운으로 보고.
5. **자가 진화** — 작업 종료 시 자기비평을 거쳐 `## Current Evolved Standards`를 갱신하고 `## Evolution Log`에 날짜·근거를 append.
6. **관측 (선택)** — 진행상황·비용·상태를 백엔드 write-back 엔드포인트로 기록하면 Next.js 대시보드에 실시간 반영.

---

## 💡 실제 사용 시 이점

- **세션이 바뀌어도 나를 기억한다** — `user_profile.md` 장기 기억 덕분에 매번 스타일·포맷을 다시 설명할 필요 없음. 쓸수록 더 잘 맞음(자가 진화).
- **복잡한 일을 알아서 쪼개 처리** — 사용자는 대형 태스크만 던지면, 에이전트가 스스로 하위 팀을 구성해 협업 처리하고 결과만 보고.
- **외부 API 의존·과금 없이 내부에서 동작** — 오케스트레이션을 별도 LLM API 호출로 돌리지 않고 Antigravity 에이전트 시스템 안에서 수행.
- **블랙박스가 아니다** — 어떤 서브에이전트가 무엇을 했는지 보고 + 백엔드 로그/비용 대시보드로 투명하게 추적.
- **재현 가능** — 에이전트 정의가 레포에 체크인돼 있어 재시작에도 소실되지 않고 어디서나 동일하게 로드.

### 적용 예시
- 다단계 데이터 파이프라인(수집 → 정제 → 요약 → 리포트)을 하위 에이전트 협업으로 자동 처리
- 사용자별 코딩 스타일/데이터 포맷을 기억해 일관되게 산출물 생성
- 작업 패턴을 학습해 반복 업무를 점점 더 맞춤화

---

## 🧱 기술 스택

| 영역 | 스택 |
|---|---|
| **Orchestration** | Antigravity `evolving_companion` 서브에이전트 (`define_subagent` / `invoke_subagent` / `manage_subagents`) |
| **메모리** | `.agents/user_profile.md` (장기 기억 + Evolution Log) |
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0, SQLite — **영속·관측 계층 (LLM 미호출)** |
| Frontend | Next.js (App Router), TypeScript, TailwindCSS |
| 테마 | EvoAgent Console — Slate 950 배경 + Amber 500 액센트 |

**데이터 모델** — `settings`, `tasks`, `checkpoints`, `token_costs`, `logs` (5개 테이블, `backend/models.py`)

---

## 🚀 사용 방법

### 1. 오케스트레이터 로드 (Antigravity)

서브에이전트 정의는 재시작 시 소실되므로, 새 세션마다 레포의 정의를 다시 등록합니다.

```
이 레포의 antigravity/agents/evolving_companion/agent.json 정의로
evolving_companion 서브에이전트를 define_subagent로 등록하고,
이후 대형 태스크는 모두 evolving_companion에게 위임해줘.
```

자세한 로드/동작 설명은 [`antigravity/README.md`](antigravity/README.md) 참고.

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

백엔드 주소 변경: `frontend/.env.local`에 `NEXT_PUBLIC_API_URL=http://localhost:8000/api`.

---

## 📡 API 엔드포인트 (관측 계층)

| Method | Path | 설명 |
|---|---|---|
| `GET` | `/api/settings` | 시스템 설정 조회 |
| `POST` | `/api/settings` | 시스템/학습 ON·OFF 토글 |
| `POST` | `/api/tasks` | 새 Task 생성 (오케스트레이터에 위임, `delegated`) |
| `GET` | `/api/tasks/{id}` | Task 상태 조회 |
| `POST` | `/api/tasks/{id}/resume` | 일시정지/실패 Task 재처리 위임 |
| `GET` | `/api/tasks/{id}/logs` | 노드별 실행 로그 조회 |
| `GET` | `/api/tasks/{id}/costs` | 노드별 토큰·비용 조회 |
| `POST` | `/api/tasks/{id}/status` | **(write-back)** 에이전트가 Task 상태 보고 |
| `POST` | `/api/tasks/{id}/logs` | **(write-back)** 에이전트가 로그 보고 |
| `POST` | `/api/tasks/{id}/costs` | **(write-back)** 에이전트가 비용 보고 |

---

## 🗺️ 로드맵

- [x] **자율 오케스트레이션** — Antigravity `evolving_companion`이 `define/invoke_subagent`로 하위 에이전트를 스폰·지시 *(외부 API 오케스트레이션 제거)*
- [x] **에이전트 정의 버전 관리** — `antigravity/`에 체크인해 재시작 소실 방지
- [x] **관측 write-back 엔드포인트** — 에이전트가 logs/costs/status를 백엔드에 보고 → 대시보드 반영
- [ ] **세션 부트스트랩 자동화** — 세션 시작 시 정의 자동 재등록 스크립트
- [ ] **Stage B 제품화** — 오케스트레이션 로직을 백엔드로 흡수해 Antigravity 비의존 독립 제품화
- [ ] **벡터 메모리** — 작업 패턴 학습용 임베딩 저장 (`chromadb` 준비됨)

---

## 📂 프로젝트 구조

```
evolving-agent-platform/
├── antigravity/                          # 🧠 오케스트레이션 두뇌 (Stage A)
│   ├── agents/evolving_companion/
│   │   └── agent.json                    # 자율 오케스트레이터 정의 (정규본)
│   ├── user_profile.template.md          # 장기기억 템플릿
│   └── README.md                         # 로드/동작 설명
├── backend/                              # 영속·관측 계층 (Stage B 후보)
│   ├── main.py           # FastAPI 앱 + REST 라우터 (write-back 포함)
│   ├── orchestrator.py   # 위임 coordinator (LLM 호출 없음)
│   ├── models.py         # SQLAlchemy ORM
│   ├── schemas.py        # Pydantic 스키마
│   ├── database.py       # DB 설정
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── app/page.tsx  # EvoAgent Console 대시보드
│       └── lib/api.ts    # API 클라이언트
├── docs/cursor_tasks/    # 감독관-워커 작업 지시서
├── CLAUDE.md             # Claude Code 개발 규칙
└── EAP_CONTEXT.md        # 아키텍처 인수인계 문서
```

자세한 아키텍처 결정 이력은 [`EAP_CONTEXT.md`](EAP_CONTEXT.md), 오케스트레이션 상세는 [`antigravity/README.md`](antigravity/README.md)를 참고하세요.
