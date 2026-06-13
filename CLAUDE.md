# CLAUDE.md — Evolving Agent Platform

## 프로젝트 개요
사용자의 대화 패턴과 데이터 처리 습관을 학습하여 스스로 진화하는 멀티 에이전트 플랫폼.
작업이 크면 자동으로 여러 에이전트로 분할하여 협업 처리.

## 기술 스택
- Backend: Python 3.11+, FastAPI, SQLAlchemy, SQLite (dev), google-genai (Gemini API)
- Frontend: Next.js (App Router), TypeScript, TailwindCSS
- LLM: Gemini 3.5 Flash (`gemini-3.5-flash`)

## 핵심 아키텍처

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
- `call_gemini_with_cost()` 통해서만 LLM 호출 (비용 추적 보장)
- 새 모델: `models.py` + `schemas.py` 동시 추가
- `.env`에 `GEMINI_API_KEY` 저장. 코드에 하드코딩 절대 금지
- `orchestrator.py`의 체크포인트/비용 로깅 흐름 보존 필수

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
├── orchestrator.py   # 멀티 에이전트 파이프라인 핵심
├── database.py       # DB 설정
├── requirements.txt
└── .env              # API 키 (git 금지)

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
- `call_gemini_with_cost()` 우회 직접 Gemini API 호출 금지
- `db.sqlite3` 직접 수정 금지
- `.env` Git 커밋 금지

## 장기 기억 참조
사용자의 작업 패턴 및 아키텍처 결정 이력: `C:\Users\sangw\.gemini\antigravity\scratch\web-service\.agents\user_profile.md` 참조.

## 세션 종료 규칙
작업이 끝나면 `C:\Users\sangw\.gemini\antigravity\scratch\web-service\.agents\user_profile.md`의 **Evolution Log**에 오늘 날짜와 함께 변경사항을 기록할 것.
