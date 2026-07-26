# Inno Loop Engineering

`inno-loop-engineering`은 `intent.md`를 입력으로 받아 개발을 **project-init → project-plan → project-run → project-review**로 반복하는 Codex 플러그인이다. 일반 내부 개발·검증은 자동 진행하고, 승인 필요 위험은 `BLOCKED`에서 멈춘다.

> **Shared Core**: 이 저장소가 소유한 Python package `loop_engine`이 Shared Core다.
> 외부 또는 내부/company `loop_engine` 패키지·저장소에 의존하지 않는다.

## 빠른 시작

1. 대상 프로젝트 루트에 `intent.md`를 작성한다. 기존 이름 `intend.md`도 별칭으로 읽을 수 있다. 또는 요청에서 프로젝트 내부의 단일 UTF-8 파일을 명시 입력으로 지정할 수 있다.
2. 새 Codex 세션을 연다.
3. 다음처럼 요청한다.

   ```text
   $inno-loop intent.md를 기준으로 inno-loop 수행 부탁해
   ```

`intent.md를 기준으로 inno-loop 수행 부탁해`, `loop engine으로 수행 부탁해`, `루프 엔진으로 수행해줘`, `asdf.md를 기준으로 loop engine 수행 부탁해` 같은 자연어 요청도 전체-loop skill의 대상이다. 명시 입력은 프로젝트 루트 내부의 단일 UTF-8 regular file이어야 한다. 명시 입력이 없을 때 `intent.md`와 `intend.md`가 함께 있거나 둘 다 없으면 입력 모호성으로 `BLOCKED`된다.

## 여러 lifecycle run

각 lifecycle은 별도 run ID와 상태·artifact·registry를 가진다.

```text
.loop-engine/runs/<run-id>/state.json
.loop-engine/runs/<run-id>/artifacts/
.loop-engine/runs/<run-id>/registry.json
.loop-engine/current.json
```

- 같은 입력 hash의 진행 중 run은 재개한다.
- 완료된 run 뒤 다른 입력 파일을 요청하면 새 run을 만든다.
- 다른 입력의 진행 중 run이 있으면 `새 lifecycle로`를 명시해야 새 run을 만든다.
- `loop-engine runs list`, `runs select --run-id <id>`, `runs lease`로 run을 조회·선택·잠글 수 있다.

## 전체 loop

| 단계 | 수행 | 주요 근거 |
| --- | --- | --- |
| `project-init` | 의도·범위·가정·위험을 정리 | charter, design, roadmap |
| `project-plan` | 작업·DoD·검증·rollback을 계획 | execution plan, validation matrix |
| `project-run` | 계획 범위 구현과 검증 실행 | run log, command/test evidence |
| `project-review` | 수용 기준 독립 판정 | review 또는 remediation packet |

review가 현재 수용 기준 미달이면 `project-plan`으로만 돌아가 다시 수행한다. 모든 기준이 통과하면 `COMPLETE`다.

### Init/Plan 품질 게이트

`project-init`과 각 `project-plan` iteration은 입력 packet, 서로 다른 run ID를
가진 세 개의 분석 artifact, judge requirement matrix를 hash-bound JSON artifact로
기록해야 한다. judge는 material requirement의 unanimous weight / 전체 material
weight로 consistency score를 계산한다. 50 미만 또는 security, privacy,
irreversible effect, compliance, budget, core architecture의 모순은 차단한다.
50–80은 모든 material difference를 해결한 Mediator artifact가 있어야 한다.

`complete-init`은 bound charter/design/roadmap을, `complete-plan`은 현재
iteration의 execution plan/validation matrix를 검증한다. 재계획은 이전 plan 및
review hash와 non-deferrable 실패 정보를 포함하는 structured remediation packet이
없으면 시작할 수 없다.

## 안전 경계

다음은 자동 진행하지 않고 승인 요청 후 `BLOCKED`된다.

- 외부 또는 비가역 효과
- 보안·개인정보·비밀정보 위험
- 비용·모델·실행 한도 초과
- intent 밖 범위 또는 핵심 아키텍처 변경
- 반복 평가 실패 또는 불확실한 위험

무응답은 승인으로 처리하지 않는다. 기존 `.inno-loop/state.json`도 새 init으로 덮어쓰지 않는다.

## 상태와 산출물

대상 프로젝트에 다음 경로가 생성된다.

```text
.loop-engine/runs/<run-id>/state.json
.loop-engine/runs/<run-id>/artifacts/
.loop-engine/current.json
```

상태에는 입력 hash, evidence, checkpoint, block reason, remediation 정보가 기록된다. 산출물은 프로젝트 루트 기준 상대 경로로 evidence에 연결한다.

> **레거시**: 기존 `.inno-loop/state.json`은 첫 실행 시 `.loop-engine/`으로 자동 마이그레이션된다.

## CLI

로컬 editable install 뒤 `loop-engine`이 상태 전이를 제공한다. 플러그인 루트의
`scripts/loopctl.py`는 같은 core를 호출하는 호환 래퍼다.

```bash
PROJECT_ROOT=/path/to/project

python3 -m pip install -e /path/to/inno-loop-engineering

# intent.md 우선, intend.md 별칭 자동 탐색
loop-engine --project-root "$PROJECT_ROOT" init-auto

# 명시 파일 입력
loop-engine --project-root "$PROJECT_ROOT" \
  init --intent-file "asdf.md"

# 상태 확인
loop-engine --project-root "$PROJECT_ROOT" status
```

CLI를 직접 쓸 때도 `plan`, `run`, `review`, `review-complete`, `replan`은 실제 evidence가 있을 때만 호출한다.
품질 게이트는 `record-input-packet`, `run-quality-gate`, `complete-init`,
`complete-plan`, `record-review-artifact`, `record-remediation-packet` 명령으로
실행·검증한다. `run-quality-gate`는 caller가 제공한 local JSON runner를 shell 없이
세 번 독립 실행하고, judge와 필요 시 Mediator artifact를 active run 아래에 저장한다.
runner 오류·미가용·hash mismatch는 redacted evidence를 남기고 `BLOCKED`된다. 패키지는
모델 endpoint나 외부 서비스를 내장 호출하지 않는다.

선택적으로 `record-epistemic-ledger`는 현재 loop/iteration의 evidence-first
claim ledger를 기록한다. ledger가 있는 plan은 해당 hash와 task별
`precondition_claim_ids`, `effect_claims`, `failure_effects`를 bind해야 한다.
`retrieve-trajectories --tag <tag>`는 이전 run의 local tag match를 planning
hint로만 기록하며, retrieved data는 evidence·approval·quality gate를 만족할 수
없다. `health report`는 registry agent의 timeout/failure/retry/quarantine를
기록하고 required unhealthy agent를 fail-closed `BLOCKED`로 처리한다.

## 개발·검증

```bash
python3 -m unittest discover -s plugin/inno-loop-engineering/tests -v
python3 /home/inno/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py \
  plugin/inno-loop-engineering
```

추가 사용 방법은 [HTML 가이드](docs/inno-loop-engineering-guide.html), 정책·계약은 [신규 개발개요](inno-loop-engineering-신규개발개요.md)를 참조한다.
