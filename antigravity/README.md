# Antigravity 자율 오케스트레이션 (Stage A)

이 디렉터리는 EAP의 **오케스트레이션 두뇌**를 정의합니다.

핵심 원칙: **오케스트레이션은 외부 LLM API 호출이 아니라, Antigravity 내부의 서브에이전트 시스템으로 동작합니다.**
`evolving_companion` 에이전트가 스스로 오케스트레이터가 되어, `define_subagent`/`invoke_subagent` 권한으로 하위 에이전트(`scraper_agent`, `parser_agent` 등)를 동적으로 생성·지시하고, 결과를 취합해 보고하며, 그 과정을 자신의 기억(`user_profile.md`)에 반영해 자가 진화합니다.

> **왜 여기에 체크인하나?** Antigravity의 서브에이전트 정의는 **세션/서버 재시작 시 소실**됩니다(브레인 폴더 안에만 존재). 정의를 레포에 버전 관리로 박아두면 ① 재시작에도 생존하고 ② GitHub로 공유·재현 가능하며 ③ 세션 시작 시 일관되게 다시 로드할 수 있습니다.

---

## 📁 구성

```
antigravity/
├── README.md                              # 이 문서
├── agents/
│   └── evolving_companion/
│       └── agent.json                     # 자율 오케스트레이터 정의 (정규본)
└── user_profile.template.md               # 작업공간 장기기억(.agents/user_profile.md) 템플릿
```

---

## 🧠 동작 메커니즘

```
            ┌──────────────────────────────────────────────────────────┐
 사용자 ───►│              evolving_companion (오케스트레이터)            │
  대형      │  ① user_profile.md 읽기 → 사용자 스타일/포맷에 정렬        │
  태스크    │  ② 태스크 분해 → 하위 서브에이전트 동적 정의/호출          │
            │                                                          │
            │     define_subagent + invoke_subagent                    │
            │        ├──► scraper_agent  (수집)                         │
            │        └──► parser_agent   (정제/표준화)                  │
            │  ③ 결과 취합·검증 → 사용자에게 보고                       │
            │  ④ 자기비평 → user_profile.md의 Evolved Standards/        │
            │              Evolution Log 갱신 (자가 진화)               │
            └──────────────────────────────────────────────────────────┘
```

**핵심 권한** — `agent.json`의 `toolNames`에 포함된:
- `define_subagent` — 하위 에이전트를 동적으로 정의
- `invoke_subagent` — 정의한 하위 에이전트에게 일을 시킴
- `manage_subagents` — 활성 하위 에이전트 추적/회수

여기에 `systemPromptConfig.includeSections`의 `subagent_reminder`가 더해져, 사용자가 말한 **"또 다른 서브에이전트를 생성·지시할 수 있는 권한(enable_subagent_tools)"**이 활성화된 상태입니다.

---

## 🚀 Antigravity에 로드하는 법 (세션 시작 시)

서브에이전트 정의는 재시작 시 사라지므로, 새 세션을 열면 아래 부트스트랩을 Antigravity 감독관 에이전트에게 지시해 재등록합니다.

> **부트스트랩 지시 예시 (복붙용):**
>
> ```
> 이 레포의 antigravity/agents/evolving_companion/agent.json 정의를 그대로 사용해
> evolving_companion 서브에이전트를 define_subagent로 등록해줘.
> 등록 후에는 모든 대형 태스크를 evolving_companion에게 위임하고,
> 그가 스스로 하위 서브에이전트를 스폰해 처리하도록 해.
> ```

로드되면 사용자는 대형 태스크만 던지면 됩니다 — 분해·스폰·취합·기억 갱신은 `evolving_companion`이 자율적으로 수행합니다.

---

## 🗄️ 기억(메모리)

- 위치: 작업공간의 `.agents/user_profile.md`
- 최초 실행 시 없으면 에이전트가 [`user_profile.template.md`](user_profile.template.md) 구조로 자동 생성
- 매 작업 종료 시 `## Current Evolved Standards` 갱신 + `## Evolution Log`에 날짜·근거 append

---

## 🔗 백엔드와의 관계 (Stage A vs Stage B)

| 계층 | 역할 | 상태 |
|---|---|---|
| **Stage A — Antigravity `evolving_companion`** | 오케스트레이션 두뇌 (분해·스폰·취합·자가진화) | **현재 활성** |
| **Stage B — `backend/` FastAPI 서비스** | 영속·관측 계층 (Task/Log/Cost/Checkpoint 저장 + Next.js 대시보드 시각화). 향후 독립 제품화 경로 | 준비 |

백엔드 `orchestrator.py`는 더 이상 LLM을 직접 호출하지 않습니다. 태스크를 받으면 `delegated` 상태로 기록하고, 오케스트레이션은 Antigravity 에이전트가 담당합니다. 에이전트(또는 그 하위 에이전트)는 `run_command`로 백엔드 API에 로그·비용·상태를 기록해 대시보드에 반영할 수 있습니다.
