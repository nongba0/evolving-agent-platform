# evolving_companion — 기억하고 진화하는 동반자

이 디렉터리는 EAP의 **핵심**을 정의합니다: 사용자를 기억하고 쓸수록 진화하는 companion 에이전트.

핵심 원칙: **`evolving_companion`의 본질은 "축적되고 진화하는 사용자 맥락"입니다.**
사용자의 스타일·포맷·습관을 `.agents/user_profile.md`에 장기 기억으로 쌓고, 매 작업마다 자기비평을 거쳐 더 잘 맞게 진화합니다.
하위 에이전트 스폰(오케스트레이션)은 이 기억을 *활용하는* **보조 능력**일 뿐, 핵심이 아닙니다.

> **왜 여기에 체크인하나?** Antigravity의 서브에이전트 정의는 **세션/서버 재시작 시 소실**됩니다(브레인 폴더 안에만 존재). 정의를 레포에 버전 관리로 박아두면 ① 재시작에도 생존하고 ② GitHub로 공유·재현 가능하며 ③ 세션 시작 시 일관되게 다시 로드할 수 있습니다.

---

## 📁 구성

```
antigravity/
├── README.md                              # 이 문서
├── agents/
│   └── evolving_companion/
│       └── agent.json                     # companion 정의 (개인화+자가진화 / 오케스트레이션은 보조)
└── user_profile.template.md               # 장기기억(.agents/user_profile.md) 템플릿
```

---

## 🧠 핵심 루프 — 기억하고 진화한다

```
        ┌──────────────────────────────────────────────┐
        │           .agents/user_profile.md            │
        │   (장기 기억: 스타일 · 포맷 · 습관 · 표준)     │
        └───────▲──────────────────────────┬───────────┘
        ④ 진화   │                          │ ① 읽고 정렬
        (자기비평)│                          ▼
  사용자 ──────►  ┌───────┴──────────────────────────────┐
   태스크        │           evolving_companion          │
                │  ② 기억에 맞춰 작업 수행               │
                │  ③ (대형 작업 한정) 하위 팀 구성  ← 보조│
                └───────────────────┬──────────────────-┘
                                    ▼
                            사용자에게 보고
```

1. **기억 정렬** — 작업 시작 시 `.agents/user_profile.md`를 읽어(없으면 생성) 사용자 스타일에 정렬.
2. **맞춤 수행** — 기억에 맞춰 작업 처리.
3. **(보조) 하위 팀 구성** — 작업이 클 때만 `define_subagent`/`invoke_subagent`로 전용 하위 에이전트(`scraper_agent`, `parser_agent` 등)를 꾸려 협업. 작은 작업은 직접.
4. **자가 진화** — 종료 시 자기비평 → `## Current Evolved Standards` 갱신 + `## Evolution Log`에 날짜·근거 append.

---

## 🚀 Antigravity에 로드하는 법 (세션 시작 시)

서브에이전트 정의는 재시작 시 사라지므로, 새 세션을 열면 아래를 감독관 에이전트에게 지시해 재등록합니다.

> **부트스트랩 지시 예시 (복붙용):**
>
> ```
> 이 레포의 antigravity/agents/evolving_companion/agent.json 정의로
> evolving_companion 서브에이전트를 define_subagent로 등록해줘.
> 작업 시작 시 .agents/user_profile.md를 읽어 내 스타일에 맞추고,
> 작업이 끝나면 자기비평으로 그 기억을 갱신하도록 해.
> (큰 작업이면 그때만 하위 에이전트를 꾸려 처리)
> ```

---

## 🗄️ 기억(메모리) — 본체

- 위치: 작업공간의 `.agents/user_profile.md`
- 최초 실행 시 없으면 [`user_profile.template.md`](user_profile.template.md) 구조로 자동 생성
- 매 작업 종료 시 `## Current Evolved Standards` 갱신 + `## Evolution Log`에 날짜·근거 append
- 이 파일이 곧 **차별점(해자)**: 흉내 낼 수 없는 건 기능이 아니라 그 사용자에 대해 쌓인 맥락

---

## 🔗 보조 능력 · 백엔드와의 관계

| 계층 | 역할 | 비고 |
|---|---|---|
| **기억 / 진화** (`user_profile.md`) | 개인화 + 자가진화 | **핵심** |
| `evolving_companion` | 기억 기반 작업 수행 | 핵심 |
| 오케스트레이션 (`define/invoke_subagent`) | 대형 작업 시 하위 팀 구성 | **보조 능력** |
| `backend/` FastAPI | Task/Log/Cost 저장 + 대시보드 | 영속·관측 (LLM 미호출) |

백엔드 `orchestrator.py`는 LLM을 호출하지 않는다. 태스크를 `delegated`로 기록하고, 에이전트가 `run_command`로 write-back 엔드포인트(`POST /api/tasks/{id}/logs|costs|status`)에 보고하면 대시보드에 반영된다.
