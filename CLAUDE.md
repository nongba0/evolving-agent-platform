# CLAUDE.md — Evolving Agent Platform

## 프로젝트 개요
사용자의 대화 패턴과 데이터 처리 습관을 학습하여 스스로 진화하는 멀티 에이전트 플랫폼.
작업이 크면 자동으로 여러 에이전트로 분할하여 협업 처리.

## 기술 스택
- Orchestration: Antigravity `evolving_companion` 서브에이전트 (define/invoke_subagent)
- Backend: Python 3.11+, FastAPI, SQLAlchemy, SQLite (dev) — 영속·관측 계층 (LLM 미호출)
- Frontend: Next.js (App Router), TypeScript, TailwindCSS

## 핵심 아키텍처

### 핵심 모델 — 기억하고 진화하는 companion
- **핵심은 "축적되고 진화하는 사용자 맥락"이다.** `evolving_companion`은 사용자 스타일·포맷·습관을 `.agents/user_profile.md`에 장기 기억으로 쌓고, 매 작업 종료 시 자기비평을 거쳐 `Current Evolved Standards`/`Evolution Log`를 갱신해 진화한다.
- 이 기억이 차별점(해자)이다. 기능이 아니라 "그 사용자에 대해 쌓인 맥락"이 흉내 낼 수 없는 부분.
- **오케스트레이션(하위 에이전트 스폰)은 보조 능력이다.** 대형 작업일 때만 `define_subagent`/`invoke_subagent`로 하위 팀을 꾸린다. 외부 LLM API로 오케스트레이션하지 않고 Antigravity 에이전트 내부에서 수행.
- 정의·기억 템플릿은 [`antigravity/`](antigravity/)에 버전 관리로 체크인(재시작 소실 방지).
- 백엔드(`backend/`)는 **영속·관측 계층**: Task/Log/Cost 저장 + 대시보드. 직접 LLM을 호출하지 않는다.

### 하이브리드 검증 (Hybrid Validation)
1. **L1 Micro-validation**: 워커 에이전트 자체 스키마/타입 검증 + 최대 3회 재시도
2. **L2 Milestone Gateway**: 분기점에서 오케스트레이터 시맨틱 품질 검증

### 비용 관리
- 모든 LLM 호출에 토큰 사용량 추적 (input_tokens, output_tokens, estimated_cost)
- Task별 Budget Cap $0.50 초과 시 자동 일시정지

## 핵심 규칙

### 언어
- 코드 주석: 한국어 또는 영어 (일관성 유지)
- UI 텍스트: 영어 (EvoAgent Console 테마)

### Python / FastAPI
- **백엔드에서 LLM 직접 호출 금지.** 오케스트레이션은 Antigravity `evolving_companion`이 담당하고, 백엔드는 영속·관측만 한다.
- `orchestrator.py`는 태스크를 `delegated` 상태로 기록하는 coordinator일 뿐 (LLM 호출 없음).
- 에이전트가 보고하는 진행상황은 write-back 엔드포인트(`POST /api/tasks/{id}/logs|costs|status`)로 저장된다.
- 새 모델: `models.py` + `schemas.py` 동시 추가

### Next.js / TypeScript
- App Router (`src/app/`)
- API 클라이언트: `src/lib/api.ts`에 집중
- 다크 테마: Slate 950 배경 + Amber 500 액센트

### 파일 구조
```
backend/
├── main.py           # FastAPI 앱 + 라우터
├── models.py         # SQLAlchemy ORM
├── schemas.py        # Pydantic 스키마
├── orchestrator.py   # 위임 coordinator (LLM 호출 없음, 태스크를 delegated 처리)
├── database.py       # DB 설정
├── requirements.txt
└── .env              # 환경변수 (git 금지)

frontend/
├── src/app/page.tsx  # 메인 대시보드
├── src/lib/api.ts    # API 클라이언트
└── package.json
```

### 검증
- Backend: `cd backend && python -m py_compile main.py models.py orchestrator.py`
- Frontend: `cd frontend && npm run build`
- 통합: `uvicorn main:app --reload` + `npm run dev`

### 금지
- 백엔드 코드에서 외부 LLM API 직접 호출 금지 (오케스트레이션은 Antigravity 에이전트 전담)
- `db.sqlite3` 직접 수정 금지
- `.env` Git 커밋 금지

## 장기 기억 참조
사용자의 작업 패턴 및 아키텍처 결정 이력: `C:\Users\sangw\.gemini\antigravity\scratch\web-service\.agents\user_profile.md` 참조.

## 세션 종료 규칙
작업이 끝나면 `C:\Users\sangw\.gemini\antigravity\scratch\web-service\.agents\user_profile.md`의 **Evolution Log**에 오늘 날짜와 함께 변경사항을 기록할 것.
