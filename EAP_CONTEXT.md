# Evolving Agent Platform — Context & Handover Document

이 문서는 이전 대화에서 논의된 **Evolving Agent Platform(자율 진화형 멀티 에이전트 플랫폼)**의 모든 기획, 아키텍처 결정, 코딩 규칙을 새 대화(또는 Claude Code)로 안전하게 이전하기 위한 인수인계(Handover) 문서입니다.
새로운 에이전트나 대화를 시작할 때 이 문서를 먼저 읽게 하세요.

---

## 1. 프로젝트 비전
단순한 챗봇이 아니라, **사용자의 대화 패턴과 데이터 처리 습관을 스스로 학습하여 진화하는 멀티 에이전트 플랫폼**입니다.
작업의 규모가 크면 오케스트레이터가 하위 워커 에이전트들을 생성해 작업을 분할(DAG)하고 협업 처리합니다.

## 2. 아키텍처 핵심 결정사항

### 2.1. 하이브리드 검증 시스템 (Hybrid Validation)
LLM의 환각(Hallucination)과 오류를 통제하기 위해 2단계 검증을 도입했습니다.
1. **L1 Micro-validation**: 워커 에이전트 레벨에서 Pydantic 스키마 및 타입 검증 수행. 실패 시 스스로 최대 3회 재시도.
2. **L2 Milestone Gateway**: DAG 파이프라인의 핵심 분기점에서 오케스트레이터가 결과물의 '의미론적(Semantic) 품질'을 종합 검증.

### 2.2. 비용 추적 및 통제 (Cost Management)
- LLM(Gemini) 호출 시 반드시 입력/출력 토큰을 계산하고 예상 비용(USD)을 산출합니다.
- DB(`token_costs` 테이블)에 모든 비용을 기록합니다.
- Task별로 Budget Cap(예: $0.50)을 설정하여, 한도 초과 시 파이프라인을 자동 일시정지(`paused`)합니다.

### 2.3. 디스코드 봇(Discord Bot) 기능 보류
- 초기에는 원격 실행을 위해 디스코드 봇을 기획했으나, **현재 단계에서는 배제**하기로 결정했습니다.
- 오직 내부 오케스트레이션과 대시보드(Next.js) 기능 고도화에 집중합니다.

## 3. 감독관-워커 워크플로우 (Claude Code 도입)

프로젝트 개발 방식은 다음과 같이 역할이 완전히 분리되었습니다.
- **Antigravity (감독관)**: 아키텍처 설계, 리뷰, 작업 지시서 작성
- **Claude Code (개발자)**: `CLAUDE.md` 규칙에 따른 코딩, 구현, 테스트 수행 및 진화 기록 갱신

### 작업 지시 및 수행 방식
1. 감독관이 `docs/cursor_tasks/` 하위에 작업 지시서(예: `task_001_xxx.md`)를 작성.
2. Claude Code 터미널에서 해당 지시서를 참조하여 개발 수행.
3. 작업 완료 후, Claude Code가 스스로 기억 보존 규칙에 따라 문서를 갱신.

## 4. 기록관(Archivist) 로직의 흡수
- 기존에는 `evolving_companion`이라는 서브에이전트가 기록관 역할을 수행하도록 기획했으나, **Claude Code의 자체 Task 시스템과 기능이 중복되어 폐기**했습니다.
- 대신 **"세션 종료 규칙"**을 `CLAUDE.md`에 명시하여, Claude Code가 개발 세션을 마칠 때마다 학습한 내용과 변경사항을 문서에 스스로 덧붙이도록 아키텍처를 단순화했습니다.

## 5. 현재 구현 상태 및 기술 스택
- **Backend (FastAPI)**: 
  - `orchestrator.py`에 L1 재시도 로직, 비용 추적, 체크포인트 저장 로직의 뼈대가 하드코딩되어 있습니다. (실제 동적 분할 기능 추가 개발 필요)
  - SQLAlchemy 기반으로 SQLite(`db.sqlite3`) 연동 완료.
  - LLM 모델: `gemini-3.5-flash` (`call_gemini_with_cost` 함수로 래핑됨)
- **Frontend (Next.js)**: 
  - DAG(실행 흐름) 시각화 및 실시간 로그 콘솔을 표시하는 대시보드 UI의 초기 스켈레톤 구축 완료.
  - TailwindCSS 기반의 다크 테마(Slate + Amber) 적용.

## 6. 다음(Next) 개발 목표
1. **동적 파이프라인 생성**: `orchestrator.py`의 하드코딩된 steps를 제거하고, 사용자의 프롬프트를 분석해 동적으로 Sub-task를 생성하도록 업그레이드.
2. **Frontend-Backend API 연동**: Next.js 대시보드에서 FastAPI로 실제 Task 생성 요청을 보내고, Polling이나 WebSocket으로 상태 업데이트 받기.
