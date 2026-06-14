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
  - `orchestrator.py`는 더 이상 LLM을 직접 호출하지 않으며, 태스크 수신 시 상태를 `delegated`로 설정하여 Antigravity 에이전트로 제어권을 위임합니다.
  - 에이전트가 보고하는 진행 상황을 기록하고 노출하기 위한 write-back API 엔드포인트(`/api/tasks/{id}/status|logs|costs`)를 제공하는 **영속·관측(Observability) 계층** 역할을 수행합니다.
  - SQLAlchemy 기반으로 SQLite(`db.sqlite3`) 연동 완료.
- **Frontend (Next.js)**: 
  - 백엔드 API 클라이언트(`api.ts`) 및 대시보드 UI([page.tsx](file:///C:/Users/sangw/OneDrive/바탕%20화면/Project/evolving-agent-platform/frontend/src/app/page.tsx)) 구축 완료.
  - 실시간 로그 콘솔, 작업 실행 흐름도(DAG 맵), 토큰 누적 비용/예산 진행바 및 에이전트 장기기억 변경사항(Evolved Standards)에 대한 Diff 뷰어 구현 완료.
  - TailwindCSS 기반의 Slate + Amber 다크 테마 적용.

## 6. 다음(Next) 개발 목표 (Stage A 고도화)
1. **역할 계약(Role Contract) 및 기억 슬라이스 주입**: `evolving_companion`이 자식 에이전트를 스폰할 때, 스타일과 포맷 표준을 명시적으로 자식 브리핑에 주입하여 자식 에이전트의 기억 망각 현상을 근본적으로 해결.
2. **관측 하트비트 및 Stale 복구**: 태스크 상태가 `delegated`나 `running`에서 영영 멈추는 좀비 상태를 방지하기 위해, 백엔드 타임아웃 감지 및 하트비트 복구 시스템 도입.
3. **웹소켓(WebSockets) 실시간 연동**: 대시보드가 백엔드 DB의 변경사항을 Polling 방식 대신 실시간으로 브로드캐스팅 받아 화면에 즉시 렌더링하도록 WebSocket 스트림 연동.

## 7. 아키텍처 갱신 (2026-06-13) — 기억·진화 중심으로 재정의
이전(5·6장)의 "백엔드 `orchestrator.py`가 LLM을 호출해 파이프라인을 돌리는" 모델을 폐기하고, **핵심을 `evolving_companion`의 "축적·진화하는 사용자 맥락(기억)"으로 재정의**했습니다.
- **핵심 (재확인)**: 본질은 오케스트레이션이 아니라 **기억·자가진화 개인화**입니다. `.agents/user_profile.md`에 사용자 스타일·포맷·습관을 쌓고 매 작업마다 자기비평으로 진화하는 것이 해자입니다. 오케스트레이션(하위 에이전트 스폰)은 대형 작업용 **보조 능력**일 뿐입니다.
- **결정**: (보조 능력인) 오케스트레이션도 외부 LLM API 호출이 아니라 Antigravity 내부 서브에이전트 협업으로 동작합니다.
- **메커니즘**: `evolving_companion`이 `define_subagent`/`invoke_subagent`/`manage_subagents` 권한으로 하위 에이전트(`scraper_agent`, `parser_agent` 등)를 동적으로 스폰·지시하고, 결과를 취합해 보고하며, `.agents/user_profile.md`에 기억을 갱신해 자가 진화합니다.
- **정의 위치**: 서브에이전트 정의가 재시작 시 소실되는 문제를 해결하기 위해 [agent.json](file:///C:/Users/sangw/OneDrive/바탕%20화면/Project/evolving-agent-platform/antigravity/agents/evolving_companion/agent.json)으로 레포에 버전 관리 체크인. 세션 시작 시 이 정의를 다시 로드.
- **A→B 전략 유지**: Stage A = Antigravity 에이전트 주도(현재). Stage B = 이 로직을 백엔드로 흡수해 Antigravity 비의존 독립 제품화(향후).
- **참고**: 4장에서 폐기했던 `evolving_companion`을 "기록관"이 아니라 "자율 오케스트레이터"로 부활시킨 것. 사용자 스타일 기억 + 하위 팀 구성 + 자가 진화가 핵심.
