# Inno Loop Engineering

`inno-loop-engineering`은 프로젝트의 `intent.md`를 입력으로 받아 개발 작업을
**project-init → project-plan → project-run → project-review**로 수행하고, 부족한
부분은 근거가 있는 재계획으로 되돌리는 로컬 lifecycle engine입니다. 일반적인
구현·검증은 자동으로 이어 가되, 위험하거나 근거가 부족한 경우에는
`BLOCKED`에서 멈춥니다.

> **Shared Core** — 이 저장소가 소유한 Python package `loop_engine`이 상태 전이,
> 증적 검증, safety gate를 담당합니다. 외부 또는 사내 `loop_engine` 패키지·저장소에
> 의존하지 않습니다.

## 핵심 원칙

- 완료는 대화나 자기 보고가 아니라 현재 계획에 연결된 검증 가능한 artifact로 판정합니다.
- 계획·프롬프트·실행 보고서·검토 결과는 hash로 연결됩니다. 계획을 고치면 이전 파생
  증거는 감사용으로만 남고 새 계획을 통과시키는 근거가 될 수 없습니다.
- 자동화는 terminal outcome(`COMPLETE`, `DEFERRED_BACKLOG`, `BLOCKED`)에 도달할
  때까지 계속합니다. `REPLAN`은 종료가 아니라 다음 plan iteration의 시작입니다.
- 외부 효과, 보안·개인정보, 예산, 핵심 설계, 불확실한 위험은 fail-closed로 처리합니다.
- “모르는 것”은 숨기지 않습니다. 선택 기능인 epistemic ledger에 근거·신선도·확인
  방법을 기록하고, 검증되지 않은 가정이 작업을 통과하지 못하게 합니다.

## 빠른 시작

### Codex에서 시작하기

1. 대상 프로젝트 루트에 목표·제약·성공 기준을 적은 `intent.md`를 만듭니다.
   레거시 이름 `intend.md`도 읽을 수 있습니다.
2. 새 Codex 세션에서 다음처럼 요청합니다.

   ```text
   $inno-loop intent.md를 기준으로 inno-loop 수행 부탁해
   ```

`loop engine으로 수행 부탁해`, `루프 엔진으로 수행해줘` 같은 명시적인 lifecycle
요청도 같은 방식으로 처리합니다. 명시 입력 파일은 프로젝트 루트 안의 단일 UTF-8
regular file이어야 합니다. 입력을 지정하지 않았는데 `intent.md`와 `intend.md`가
동시에 있거나 둘 다 없으면 엔진은 추측하지 않고 `BLOCKED`됩니다.

명시적인 inno-loop 요청은 `project-init`과 `project-plan`의 Ouroboros `interview`,
Superpowers `brainstorming`·`writing-plans` 사용을 허용합니다. 이 opt-in은
`project-run`·`project-review`나 다른 작업으로 확장되지 않습니다.

### CLI에서 시작하기

```bash
PROJECT_ROOT=/path/to/project

python3 -m pip install -e /path/to/inno-loop-engineering

# intent.md 우선, intend.md는 호환 별칭
loop-engine --project-root "$PROJECT_ROOT" init-auto --full-lifecycle

# 무인 continuation은 명시 parent-host adapter가 있어야 함
export LOOP_ENGINE_HOST_BRIDGE_COMMAND='your-active-host-adapter --stdio'
loop-engine --project-root "$PROJECT_ROOT" preflight \
  --host-bridge-command "$LOOP_ENGINE_HOST_BRIDGE_COMMAND"

# 현재 run을 terminal 상태까지 진행
loop-engine --project-root "$PROJECT_ROOT" \
  continue-until-terminal --integration-retries 2 \
  --integration-retry-backoff-seconds 1

# 현재 상태 확인
loop-engine --project-root "$PROJECT_ROOT" status
```

명시 파일을 입력으로 쓸 때는 `init --intent-file "asdf.md" --full-lifecycle`을
사용합니다. 별도 lifecycle을 강제로 시작해야 할 때만 `--new-lifecycle`을 추가합니다.

## Run 격리와 상태

각 lifecycle은 서로 독립된 run ID, artifact, registry를 가집니다.

```text
.loop-engine/runs/<run-id>/state.json
.loop-engine/runs/<run-id>/artifacts/
.loop-engine/runs/<run-id>/registry.json
.loop-engine/runs/<run-id>/lease.json
.loop-engine/current.json
```

- 같은 입력 hash의 진행 중 run은 재개합니다.
- 완료된 run 뒤 다른 입력을 요청하면 새 run을 만듭니다.
- 다른 입력의 run이 진행 중이면 `새 lifecycle로`를 명시해야 새 run을 만듭니다.
- `runs list`, `runs select --run-id <id>`, `runs lease`, `runs release-lease`로
  조회·선택·동시 실행 잠금을 관리합니다.
- 레거시 `.inno-loop/state.json`은 첫 실행 시 `.loop-engine/`으로 마이그레이션됩니다.

## Lifecycle 계약

| 단계 | 역할 | 통과에 필요한 핵심 증거 |
| --- | --- | --- |
| `project-init` | 의도·범위·위험·성공 기준을 고정 | input packet, 품질 게이트, charter/design/roadmap, 필수 integration |
| `project-plan` | 작업·DoD·검증·rollback을 버전 관리 | iteration별 품질 게이트, execution plan, validation matrix |
| `project-run` | 승인된 범위만 구현하고 검증 | execution policy, prompt package, validation receipts, run report |
| `project-review` | 기준별 독립 판정 | hash-bound review, remediation packet 또는 terminal 판정 |

초기 cycle은 네 단계를 모두 수행합니다. review가 미달이면 non-deferrable remediation
packet을 기록하고 `project-plan → project-run → project-review`만 다시 돕니다. 기본
자동 재계획 한도는 3회이며, 다음 재계획이 필요하면 `BLOCKED`됩니다. `defer`는 현재
DoD·보안·개인정보·컴플라이언스·예산·비가역 효과가 아닌 검증된 비필수 항목에만 쓸 수
있습니다.

명시적인 lifecycle 요청은 내부적으로 만든 execution plan에 대한 authorization을
기록합니다. 그러므로 routine plan approval을 매 단계 다시 요청하지 않지만, safety
`BLOCKED` gate를 우회할 수는 없습니다.

### Init/Plan 품질 게이트

`project-init`과 각 `project-plan` iteration은 다음을 활성 run artifact 아래에
hash-bound JSON으로 남겨야 합니다.

1. immutable input packet과 canonical requirement matrix
2. 같은 packet만 본 독립 분석 3개(`requirements`, `risk`, `adversarial`)
3. 분석 hash가 생성된 뒤 실행되는 별도 judge requirement matrix
4. legacy noncanonical packet의 50–80 consistency score에서 모든 material
   difference를 해소하는 Mediator artifact
5. `ouroboros-interview`, `superpowers-brainstorming`,
   `superpowers-writing-plans` integration 결과

각 분석은 모든 canonical requirement를 평가합니다. canonical packet에서는 consistency
score가 진단 지표이고, 관점별 구현 세부사항의 차이는 요구사항 범위 충돌로 간주하지
않습니다. 다만 critical contradiction 또는 해결되지 않은 사람의 결정은 차단합니다.
security, privacy, irreversible effect, compliance, budget, core architecture의 material
contradiction도 차단 대상입니다. integration·agent·judge가 실패하거나 없으면
normal-Codex fallback을 만들지 않고 `BLOCKED`됩니다.

## 증적 계보와 실행 계약

계획과 실행 결과는 다음 순서로 묶입니다.

```text
input packet / quality gate
        ↓
execution plan + validation matrix
        ↓
execution policy + prompt package
        ↓
validation receipts + run report
        ↓
review artifact → COMPLETE | REPLAN | DEFERRED_BACKLOG | BLOCKED
```

`project-run`은 plan-bound execution policy를 먼저 기록하고 `make-prompts`로 만든
prompt package를 `exec-prompts`로 실행합니다. validation receipt와 run report는
prompt hash에 묶이며, review는 현재 plan·matrix·prompt·report의 hash와 필수 검증
PASS를 다시 계산합니다. 실행 명령, 변경 파일, 결과, deviation, checkpoint는 run
artifact로 남겨야 합니다.

## 자동 lifecycle supervisor와 host bridge

`continue-until-terminal`은 lifecycle을 이어 가는 supervisor입니다. `project-run`과
`project-review`는 worker로 자동 진행할 수 있습니다. 대화형 `project-init`·`project-plan`·
replan integration은 `$inno-loop`을 받은 **active parent host**가 수행·기록합니다.

무인 supervisor가 planning integration도 실행해야 할 때는 현재 대화 session과 MCP 권한을
실제로 보유한 explicit parent-host adapter를 설정해야 합니다. 기본 bridge는 없습니다.
새 `codex exec` process는 대화·승인·Ouroboros interview session을 계승하지 않으므로
planning host로 사용할 수 없습니다.

```bash
export LOOP_ENGINE_HOST_BRIDGE_COMMAND='your-active-host-adapter --stdio'

loop-engine --project-root "$PROJECT_ROOT" preflight \
  --host-bridge-command "$LOOP_ENGINE_HOST_BRIDGE_COMMAND"
loop-engine --project-root "$PROJECT_ROOT" continue-until-terminal \
  --host-bridge-command "$LOOP_ENGINE_HOST_BRIDGE_COMMAND"
```

`--integration-adapter`는 `--host-bridge-command`의 호환 별칭입니다. adapter는
protocol v2를 사용합니다. 먼저 non-mutating `operation: "preflight"` 요청에 같은
version/request ID, `operation`, `ready: true`를 반환해야 합니다. 이후
`operation: "integrate"` 요청에 같은 version/request ID와 고정 순서 `results`를
반환합니다. 요청에는 run, loop/iteration, attempt, artifact root, lifecycle input
snapshot, lifecycle authorization, init output·현재 plan·remediation lineage, 그리고 있을
경우 current input packet hash가 포함됩니다. 각 `USED` result는 활성 run 아래의 실제
artifact를 가리켜야 하며, request/response receipt도 보존됩니다.

Python child는 MCP·Codex·Ouroboros·Superpowers 권한을 소유하지 않습니다. active parent
host 또는 explicit adapter만 integration을 수행합니다. adapter가 누락되거나 preflight·
결과·schema·시간 제한 검증에 실패하면 성공을 흉내 내지 않고 fail-closed로 기록합니다.
재시도는 integrate process·timeout·응답 검증 같은 일시 오류에만 설정된 한도 내에서
적용됩니다.

## Known / unknown factor 제어

### Epistemic ledger (선택)

`record-epistemic-ledger --artifact <path>`는 현재 loop/iteration의 claim ledger를
기록합니다. claim은 `known`, `assumption`, `known_unknown`,
`suspected_blind_spot` 분류와 출처, 영향도, owner, 상태, timestamp, freshness
(`stable`, `volatile`, `expired`), 충돌 claim 연결을 가집니다.

- active `known`에는 hash-verified primary evidence 또는 validation receipt가
  필요합니다. LLM output, retrieval, self-report만으로는 충분하지 않습니다.
- ledger를 사용한 plan은 ledger hash를 bind하고, 모든 task에
  `precondition_claim_ids`, `effect_claims`, `failure_effects`를 선언합니다.
- high-impact active unknown은 task와 acceptance criterion 모두에 연결되어야 plan을
  완료할 수 있습니다.

### Trajectory와 agent health (선택)

`record-trajectory-summary`는 terminal 또는 replan의 요약을 immutable artifact로
기록합니다. `retrieve-trajectories --tag <tag>`는 로컬의 결정론적 tag match를 planning
hint로만 반환합니다. retrieval 결과는 evidence, quality gate, approval을 충족할 수
없는 **non-authoritative** 정보입니다.

`registry add/update/list`, `health report/status/reconcile`, `heartbeat touch/status`는
run 안의 agent registry와 bounded timeout·failure·retry·quarantine 상태를 관리합니다.
필수 agent가 timeout, failure, unavailable, quarantine 상태가 되면 대체 agent를
자동 생성하지 않고 `BLOCKED`됩니다.

## Safety, HIL, alert, resume

다음은 자동 진행하지 않습니다.

- 외부 또는 비가역 효과
- security, privacy, secrets 위험
- budget limit breach
- intent 밖 범위 또는 core architecture 변경
- repeated evaluation failure

`uncertain_risk`는 승인 category가 아니라 fail-closed 분류입니다. 사람의 routing이
있을 때까지 `BLOCKED`로 남습니다. 승인 요청에는 action, impact, alternatives,
requested decision, evidence reference가 필요하며 무응답은 승인으로 처리하지 않습니다.

모든 terminal `BLOCKED`는 immutable pending alert를 만듭니다. persistent runner는
host-owned alert adapter를 통해서만 이를 전달하고, receipt로 idempotently acknowledge
합니다. HIL alert는 즉시 전달 대상이며, 다른 terminal failure도 execution-stopped
alert로 남습니다.

`resume`은 exact block reason/evidence, project-owner의 remediation status와 evidence,
다음 시도 정책을 bind한 approval 없이는 `BLOCKED`를 해제하지 않습니다. worktree
baseline은 project-run 전에 저장되어 기존 dirty path와 lifecycle artifact 때문에 파일
budget을 잘못 초과 처리하지 않도록 합니다.

## 운영 CLI 요약

| 목적 | 명령 |
| --- | --- |
| 현재 상태 / 자동 진행 지시 | `status`, `continuation`, `continue-until-terminal` |
| host bridge 확인 | `preflight [--host-bridge-command ...]` |
| run 선택·잠금 | `runs list/select/lease/release-lease` |
| 승인·재개·실패 기록 | `request-approval`, `resume`, `failure` |
| alert 관리 | `alerts pending`, `alerts ack` |
| agent registry·health | `registry add/update/list`, `health report/status/reconcile`, `heartbeat touch/status` |
| 증적 등록 | `record-input-packet`, `record-quality-gate`, `record-execution-policy`, `record-prompt-package`, `record-validation-receipt`, `record-run-report`, `record-review-artifact` |
| epistemic/trajectory | `record-epistemic-ledger`, `record-trajectory-summary`, `retrieve-trajectories` |

직접 CLI로 lifecycle event를 호출할 때도 각 command의 실제 evidence가 있어야 합니다.
상세 option은 `loop-engine <command> --help`로 확인합니다. 플러그인 루트의
`scripts/loopctl.py`는 같은 Shared Core를 호출하는 호환 래퍼입니다.

## 문서와 검증

- [초보자 가이드](confluence_xml/loop-engine-beginner-guide.html)
- [신규 개발개요](inno-loop-engineering-신규개발개요.md)
- [artifact contracts](plugin/inno-loop-engineering/references/artifact-contracts.md)
- [state machine](plugin/inno-loop-engineering/references/state-machine.md)
- [approval policy](plugin/inno-loop-engineering/references/approval-policy.md)

```bash
python3 -m unittest discover -s plugin/inno-loop-engineering/tests -v
python3 /home/inno/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py \
  plugin/inno-loop-engineering
```
