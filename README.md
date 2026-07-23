# Inno Loop Engineering

`inno-loop-engineering`은 `intent.md`를 입력으로 받아 개발을 **project-init → project-plan → project-run → project-review**로 반복하는 Codex 플러그인이다. 일반 내부 개발·검증은 자동 진행하고, 승인 필요 위험은 `BLOCKED`에서 멈춘다.

> **Shared Core**: 이 플러그인은 `loop_engine` pip 패키지를 Shared Core로 사용한다.
> 핵심 정책 스펙(승인 정책·상태 기계·아티팩트 계약)은 `loop_engine/docs/spec/`을 단일 진실 출처로 참조한다.

## 빠른 시작

1. 대상 프로젝트 루트에 `intent.md`를 작성한다. 기존 이름 `intend.md`도 별칭으로 읽을 수 있다.
2. 새 Codex 세션을 연다.
3. 다음처럼 요청한다.

   ```text
   $inno-loop intent.md를 기준으로 inno-loop 수행 부탁해
   ```

`intent.md를 기준으로 inno-loop 수행 부탁해` 같은 자연어 요청도 전체-loop skill의 대상이다. `intent.md`와 `intend.md`가 함께 있거나 둘 다 없으면 입력 모호성으로 `BLOCKED`된다.

## 전체 loop

| 단계 | 수행 | 주요 근거 |
| --- | --- | --- |
| `project-init` | 의도·범위·가정·위험을 정리 | charter, design, roadmap |
| `project-plan` | 작업·DoD·검증·rollback을 계획 | execution plan, validation matrix |
| `project-run` | 계획 범위 구현과 검증 실행 | run log, command/test evidence |
| `project-review` | 수용 기준 독립 판정 | review 또는 remediation packet |

review가 현재 수용 기준 미달이면 `project-plan`으로만 돌아가 다시 수행한다. 모든 기준이 통과하면 `COMPLETE`다.

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
.loop-engine/state.json
.loop-engine/artifacts/
```

상태에는 입력 hash, evidence, checkpoint, block reason, remediation 정보가 기록된다. 산출물은 프로젝트 루트 기준 상대 경로로 evidence에 연결한다.

> **레거시**: 기존 `.inno-loop/state.json`은 첫 실행 시 `.loop-engine/`으로 자동 마이그레이션된다.

## CLI

플러그인 루트의 `scripts/loopctl.py`는 상태 전이를 제공한다.

```bash
PLUGIN_ROOT=/path/to/inno-loop-engineering/plugin/inno-loop-engineering
PROJECT_ROOT=/path/to/project

# intent.md 우선, intend.md 별칭 자동 탐색
python3 "$PLUGIN_ROOT/scripts/loopctl.py" --project-root "$PROJECT_ROOT" init-auto

# 명시 파일 입력
python3 "$PLUGIN_ROOT/scripts/loopctl.py" \
  --project-root "$PROJECT_ROOT" init --intent-file "$PROJECT_ROOT/intent.md"

# 상태 확인
python3 "$PLUGIN_ROOT/scripts/loopctl.py" --project-root "$PROJECT_ROOT" status
```

CLI를 직접 쓸 때도 `plan`, `run`, `review`, `review-complete`, `replan`은 실제 evidence가 있을 때만 호출한다.

## 개발·검증

```bash
python3 -m unittest discover -s plugin/inno-loop-engineering/tests -v
python3 /home/inno/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py \
  plugin/inno-loop-engineering
```

추가 사용 방법은 [HTML 가이드](docs/inno-loop-engineering-guide.html), 정책·계약은 [신규 개발개요](inno-loop-engineering-신규개발개요.md)를 참조한다.
