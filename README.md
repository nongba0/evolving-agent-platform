# Evolving Agent Platform (EAP)

> 사용자의 작업 패턴을 학습하며 스스로 진화하는 **자율 멀티 에이전트 플랫폼**.
> 큰 작업이 들어오면 오케스트레이터가 하위 워커 에이전트로 분할(DAG)하고, **비용을 추적·통제**하면서 **체크포인트 기반으로 안전하게** 협업 처리합니다.

FastAPI 백엔드 + Next.js 대시보드로 구성된 풀스택 MVP입니다.

---

## 🎯 무엇을 해결하나

LLM 에이전트를 실제 업무에 쓸 때 반복적으로 부딪히는 3가지 문제를 정면으로 다룹니다.

| 문제 | EAP의 해법 |
|---|---|
| **비용 폭주** — 에이전트가 토큰을 얼마나 쓰는지 모른 채 과금됨 | 모든 LLM 호출을 단일 게이트(`call_gemini_with_cost`)로 강제하고, Task별 **예산 상한(Budget Cap)** 초과 시 자동 일시정지 |
| **환각·실패** — 한 단계 실패가 전체 파이프라인을 무너뜨림 | **하이브리드 검증**(L1 자체 재시도 + L2 의미 검증)과 **체크포인트 재개**로 실패 지점부터 안전하게 복구 |
| **불투명성** — 에이전트가 내부에서 뭘 하는지 안 보임 | 노드 단위 **실시간 로그 + 비용 콘솔**을 대시보드로 가시화 |

---

## ⚙️ 어떻게 돌아가나 (동작 원리)

```
┌─────────────┐   POST /api/tasks    ┌──────────────────────────────────────┐
│  Next.js    │ ───────────────────► │           FastAPI Backend             │
│  Dashboard  │                      │                                       │
│             │ ◄─ polling (status,  │   ┌────────────────────────────────┐  │
│  (콘솔 UI)  │     logs, costs) ───  │   │        Orchestrator            │  │
└─────────────┘                      │   │  (async DAG pipeline)          │  │
                                     │   │                                │  │
                                     │   │  ┌──────────┐   ┌──────────┐   │  │
                                     │   │  │ Worker A │──►│ Worker B │   │  │
                                     │   │  │  (node)  │   │  (node)  │   │  │
                                     │   │  └────┬─────┘   └────┬─────┘   │  │
                                     │   │       │ L1 재시도(3) │         │  │
                                     │   │       ▼              ▼         │  │
                                     │   │   Checkpoint     Checkpoint    │  │
                                     │   │       │              │         │  │
                                     │   │       └──► Budget Cap 체크 ◄───┘  │
                                     │   └────────────────┬───────────────┘  │
                                     │                    ▼                  │
                                     │      call_gemini_with_cost()          │
                                     │      → 토큰/비용 DB 기록               │
                                     └────────────────────┬──────────────────┘
                                                          ▼
                                                  Gemini API (gemini-3.5-flash)
```

**처리 흐름**

1. **작업 접수** — 사용자가 대시보드에서 프롬프트를 제출하면 `POST /api/tasks`로 Task 생성(`pending`). 시스템이 OFF면 503으로 거부.
2. **백그라운드 실행** — FastAPI `BackgroundTasks`가 `run_task_pipeline`을 비동기로 띄움. Task 상태가 `running`으로 전환.
3. **노드 실행 (DAG)** — 오케스트레이터가 워커 노드들을 `asyncio.gather`로 병렬 실행. 노드 간 의존성이 있으면 앞 노드 출력을 다음 노드 입력으로 주입.
4. **L1 마이크로 검증** — 각 노드는 최대 **3회 재시도**. 빈 응답·스키마 위반 시 스스로 재시도하고, 끝내 실패하면 Task를 `failed`로.
5. **비용 추적 & 예산 상한** — 모든 호출의 input/output 토큰과 예상 비용(USD)을 `token_costs` 테이블에 기록. 누적 비용이 **상한($0.50 기본)을 넘으면 Task를 `paused`로 자동 정지**.
6. **체크포인트** — 노드가 성공할 때마다 출력 상태를 `checkpoints`에 저장. 재개 시 완료된 노드는 **건너뛰고** 멈춘 지점부터 이어서 실행(`POST /api/tasks/{id}/resume`).
7. **가시화** — 대시보드가 status·logs·costs 엔드포인트를 폴링해 실시간으로 진행 상황과 누적 비용을 보여줌.

---

## 💡 실제 사용 시 이점

- **예산이 새지 않는다** — "에이전트가 폭주해서 요금 폭탄" 시나리오를 구조적으로 차단. 상한에 닿으면 멈추고, 검토 후 `resume`으로 이어가면 됨.
- **중간에 죽어도 처음부터 다시 안 한다** — 5단계 파이프라인 중 4단계에서 실패해도, 체크포인트 덕분에 4단계부터 재개. 시간·비용 절약.
- **블랙박스가 아니다** — 어느 노드가 토큰을 얼마나 썼고 왜 재시도했는지 로그로 다 보임. 디버깅과 비용 최적화가 쉬움.
- **ON/OFF 한 번으로 전체 통제** — `system_active` 토글로 전체 시스템을 즉시 중단/재개. 운영 중 비상 정지 스위치.
- **확장 가능한 골격** — 노드를 추가하거나 의존성 그래프를 바꾸는 것만으로 새 워크플로우 구성. 비용·검증·체크포인트는 공통 인프라가 자동 처리.

### 적용 예시
- 다단계 데이터 파이프라인(수집 → 정제 → 요약 → 리포트)을 비용 한도 안에서 자동 실행
- 장시간 배치 작업을 체크포인트로 안전하게 분할 실행
- LLM 비용을 팀/프로젝트 단위로 추적해야 하는 내부 자동화 도구

---

## 🧱 기술 스택

| 영역 | 스택 |
|---|---|
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0, SQLite |
| LLM | Google Gemini (`gemini-3.5-flash`) via `google-genai` |
| Frontend | Next.js (App Router), TypeScript, TailwindCSS |
| 테마 | EvoAgent Console — Slate 950 배경 + Amber 500 액센트 |

**데이터 모델** — `settings`, `tasks`, `checkpoints`, `token_costs`, `logs` (5개 테이블, `backend/models.py`)

---

## 🚀 실행 방법

### 1. Backend

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt

# .env 생성 후 본인의 Gemini API 키 입력
echo "GEMINI_API_KEY=your_key_here" > .env

uvicorn main:app --reload   # http://localhost:8000 (docs: /docs)
```

> ⚠️ `.env`는 git에 커밋되지 않습니다(`.gitignore` 처리됨). 클론 후 직접 만들어야 합니다.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev    # http://localhost:3000
```

백엔드 주소를 바꾸려면 `frontend/.env.local`에 `NEXT_PUBLIC_API_URL=http://localhost:8000/api`.

---

## 📡 API 엔드포인트

| Method | Path | 설명 |
|---|---|---|
| `GET` | `/api/settings` | 시스템 설정 조회 |
| `POST` | `/api/settings` | 시스템/학습 ON·OFF 토글 |
| `POST` | `/api/tasks` | 새 Task 생성 + 파이프라인 실행 |
| `GET` | `/api/tasks/{id}` | Task 상태 조회 |
| `POST` | `/api/tasks/{id}/resume` | 일시정지/실패 Task를 체크포인트부터 재개 |
| `GET` | `/api/tasks/{id}/logs` | 노드별 실행 로그 |
| `GET` | `/api/tasks/{id}/costs` | 노드별 토큰·비용 기록 |

---

## 🗺️ 로드맵

현재는 **동작하는 MVP 스켈레톤**입니다. 핵심 인프라(비용·체크포인트·L1 검증)는 구현됐고, 다음을 고도화 중입니다.

- [ ] **동적 파이프라인 생성** — 현재 하드코딩된 노드 템플릿(`orchestrator.py`)을 제거하고, 사용자 프롬프트를 분석해 Sub-task를 동적으로 분할
- [ ] **L2 Milestone Gateway** — 분기점에서 결과물의 의미론적 품질을 검증하는 단계 추가
- [ ] **실시간 스트리밍** — 폴링 대신 WebSocket으로 로그/상태 푸시 (`websockets` 의존성 준비됨)
- [ ] **벡터 메모리** — 작업 패턴 학습용 임베딩 저장 (`chromadb` 준비됨)
- [ ] 배포 시 CORS 출처 제한 및 FastAPI lifespan 마이그레이션

---

## 📂 프로젝트 구조

```
evolving-agent-platform/
├── backend/
│   ├── main.py           # FastAPI 앱 + REST 라우터
│   ├── orchestrator.py   # 멀티 에이전트 파이프라인 (핵심)
│   ├── models.py         # SQLAlchemy ORM
│   ├── schemas.py        # Pydantic 스키마
│   ├── database.py       # DB 설정
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── app/page.tsx  # EvoAgent Console 대시보드
│       └── lib/api.ts    # API 클라이언트
├── docs/
│   └── cursor_tasks/     # 감독관-워커 작업 지시서
├── CLAUDE.md             # Claude Code 개발 규칙
└── EAP_CONTEXT.md        # 아키텍처 인수인계 문서
```

자세한 아키텍처 결정 이력은 [`EAP_CONTEXT.md`](EAP_CONTEXT.md)를 참고하세요.
