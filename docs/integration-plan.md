# Loop Engine Integration Plan

## 목표

`inno-loop-engineering` (Codex Frontend) + `loop_engine` (Claude Code Frontend)을  
공유 Core 위에 올라타는 구조로 통합.

단일 도구 합병이 아님 — **Shared Core + 두 Frontend** 구조.

---

## 환경 정보

| 환경 | 도구 | 레포 경로 |
|------|------|----------|
| 사내 | Claude Code + Codex CLI | `/home/h30104109/repos/loop_engine` |
| 사내 | Claude Code + Codex CLI | `/home/h30104109/repos/inno-loop-engineering` |
| 개인 PC | Codex CLI | inno-loop-engineering |

---

## 목표 아키텍처

```
┌────────────────────────────────────────────────────────────┐
│              Shared Core (pip package: loop-engine)         │
│                                                             │
│  state machine  │  registry+heartbeat  │  coverage score   │
│  approval(5-cat)│  artifact contracts  │  failure fingerpt  │
│  secret-redact  │  SHA256 hash         │  remediation pkt   │
│  DEFERRED_BACKLOG│ criterion-ID rubric │  loopctl CLI       │
└──────────┬──────────────────────────────────┬──────────────┘
           │                                  │
           ▼                                  ▼
┌──────────────────────┐          ┌───────────────────────────┐
│  Codex Frontend       │          │  Claude Code Frontend      │
│  inno-loop-engineering│          │  loop_engine               │
│                       │          │                            │
│  .codex-plugin/       │          │  ~/.claude/loop_engine/    │
│  skills/inno-loop-*   │          │  RULES.md                  │
│                       │          │  skills/project-*.md       │
│  → loop-engine CLI    │          │  → loop-engine CLI         │
└──────────────────────┘          └───────────────────────────┘
```

---

## Phase 의존관계

```
Phase 1 ──→ Phase 2 ──→ Phase 3-A ┐
                    └──→ Phase 3-B ┘──→ Phase 4
```

Phase 3-A와 Phase 3-B는 병렬 수행 가능.

---

## Phase 1 — loop_engine Core 강화

**오케스트레이터:** Claude Code + loop_engine  
**대상 레포:** `/home/h30104109/repos/loop_engine`  
**전제:** 시작 전 git commit (체크포인트)

### 작업 내용

| 항목 | 대상 파일 | 출처 |
|------|----------|------|
| approval 5-카테고리 + fail-closed | `loop_engine/utils/state.py` | inno-loop `approval-policy.md` |
| failure fingerprinting (동일 3회→BLOCKED) | `loop_engine/utils/state.py` | inno-loop `loop_engine.py` |
| SHA256 input hash | `loop_engine/utils/state.py` | inno-loop `loop_engine.py` |
| secret redaction | `loop_engine/utils/state.py` | inno-loop `loop_engine.py` |
| `artifacts.py` 신설 (버전·해시·의존성 무효화) | `loop_engine/utils/artifacts.py` | inno-loop `artifact-contracts.md` |
| DEFERRED_BACKLOG outcome 추가 | `loop_engine/utils/state.py` | inno-loop `state-machine.md` |
| criterion-ID 기반 rubric | `loop_engine/utils/coverage.py` | inno-loop 리뷰 구조 |
| remediation packet 구조 | `loop_engine/utils/state.py` | inno-loop `state-machine.md` |
| 신규 모듈 테스트 추가 | `loop_engine/tests/` | — |

### intent 파일: `intent_phase1_core.md`

```markdown
# Goal
Strengthen the loop_engine Python package core with safety and traceability features
ported from inno-loop-engineering.

# Constraints
- Do NOT change CLI interface signatures (backward compatibility)
- Do NOT call loop-engine CLI mid-run (editable install — source changes take effect immediately)
- All new features must have pytest coverage
- Self-referential: this package orchestrates its own modification — new modules
  must only be invoked after this run completes (guard with version flag if needed)

# Tasks
1. Add 5-category approval system + fail-closed to state.py
   Reference: /home/h30104109/repos/inno-loop-engineering/plugin/inno-loop-engineering/references/approval-policy.md
2. Add failure fingerprinting (3 consecutive identical → BLOCKED) to state.py
   Reference: /home/h30104109/repos/inno-loop-engineering/plugin/inno-loop-engineering/scripts/loop_engine.py
3. Add SHA256 input hash + secret redaction to state.py
4. Create loop_engine/utils/artifacts.py (versioned artifacts, hash-based invalidation)
   Reference: /home/h30104109/repos/inno-loop-engineering/plugin/inno-loop-engineering/references/artifact-contracts.md
5. Add DEFERRED_BACKLOG to VALID outcomes in state.py
6. Add criterion-ID based rubric support to coverage.py
7. Add remediation_packet field to state transitions
8. Write tests for all new features

# Success Criteria
- All existing tests pass
- New tests cover approval, fingerprinting, hash, artifacts, DEFERRED, remediation
- loop-engine CLI commands unchanged
```

---

## Phase 2 — 상태 경로 통일

**오케스트레이터:** Claude Code + loop_engine (Phase 1 완료 버전)  
**대상 레포:** 양쪽 동시  
**전제:** Phase 1 완료 + pip install -e . 재실행

### 작업 내용

| 항목 | 내용 |
|------|------|
| 통일 경로 | `.loop-engine/{project_name}/state.json` |
| 아티팩트 경로 | `.loop-engine/{project_name}/artifacts/` |
| loop_engine 마이그레이션 | `.superpowers/projects/{name}/memory/` → `.loop-engine/{name}/` |
| inno-loop 마이그레이션 | `.inno-loop/` → `.loop-engine/` |
| 역호환 read | 구 경로 존재 시 자동 마이그레이션 로직 |
| 마이그레이션 스크립트 | `scripts/migrate_state_path.py` |

### intent 파일: `intent_phase2_path.md`

```markdown
# Goal
Unify state file paths across both loop_engine and inno-loop-engineering repos
to use .loop-engine/{project_name}/state.json as the single canonical path.

# Constraints
- Existing project data must not be lost
- Backward-compatible read (auto-migrate old path on first access)
- Both repos must be updated atomically (test both before committing either)

# Tasks
1. Update loop_engine/utils/state.py: read/write path → .loop-engine/{name}/state.json
2. Add backward-compat: if .superpowers/projects/{name}/memory/MEMORY.md exists, migrate
3. Update /home/h30104109/repos/inno-loop-engineering/plugin/inno-loop-engineering/scripts/loopctl.py:
   state path → .loop-engine/state.json
4. Add backward-compat: if .inno-loop/state.json exists, migrate
5. Write migration script: scripts/migrate_state_path.py
6. Update all path references in docs and RULES.md

# Success Criteria
- loop-engine state init creates .loop-engine/{name}/state.json
- Old path data auto-migrates on first read
- loopctl.py init creates .loop-engine/state.json
- All tests pass on both repos
```

---

## Phase 3-A — inno-loop-engineering Frontend 업데이트

**오케스트레이터:** Codex CLI + inno-loop-engineering  
**대상 레포:** `/home/h30104109/repos/inno-loop-engineering`  
**전제:** Phase 2 완료

### 작업 내용

| 항목 | 대상 파일 |
|------|----------|
| loopctl.py → loop-engine unified CLI 호출 전환 | `scripts/loopctl.py` |
| Socratic dialogue (N=3 + Mediator) 추가 | `skills/inno-loop-init/SKILL.md` |
| registry + heartbeat 명령 추가 | `skills/inno-loop-run/SKILL.md` |
| approval payload + remediation packet 참조 | `skills/inno-loop-review/SKILL.md` |
| 상태 경로 .loop-engine/ 반영 | 전체 SKILL.md |

### intent 파일: `intent_phase3_codex.md`

```markdown
# Goal
Update inno-loop-engineering Codex Frontend to use the unified loop-engine CLI
and incorporate Socratic init dialogue + sub-agent registry/heartbeat from loop_engine.

# Constraints
- plugin.json entry point must remain functional in Codex CLI
- SKILL.md files must remain valid Codex skill format
- Do not change the 4-loop structure (init/plan/run/review)

# Tasks
1. Update skills/inno-loop-init/SKILL.md: add Socratic dialogue N=3 parallel + Mediator consensus
   Reference: /home/h30104109/repos/loop_engine/claude_config/skills/project-init.md
              /home/h30104109/repos/loop_engine/claude_config/agents/socrates.md
              /home/h30104109/repos/loop_engine/claude_config/agents/mediator.md
2. Update skills/inno-loop-run/SKILL.md: add loop-engine registry add/heartbeat touch commands
3. Update skills/inno-loop-review/SKILL.md: add approval payload structure + DEFERRED_BACKLOG path
4. Update all SKILL.md: state path references → .loop-engine/
5. Update scripts/loopctl.py: delegate state ops to loop-engine CLI where applicable

# Success Criteria
- Codex plugin activates without error
- inno-loop-init triggers Socratic dialogue before writing charter
- inno-loop-run registers sub-agents via loop-engine registry
- State written to .loop-engine/state.json
```

---

## Phase 3-B — loop_engine Claude Code Frontend 업데이트

**오케스트레이터:** Claude Code + loop_engine  
**대상 레포:** `/home/h30104109/repos/loop_engine`  
**전제:** Phase 2 완료  
**병렬 가능:** Phase 3-A와 동시 수행 가능

### 작업 내용

| 항목 | 대상 파일 |
|------|----------|
| approval payload 구조 반영 | `claude_config/RULES.md` |
| remediation packet 반영 | `claude_config/RULES.md` |
| artifact-contracts 기반 산출물 생성 | `claude_config/skills/project-init.md` |
| criterion-ID rubric + DEFERRED_BACKLOG | `claude_config/skills/project-review.md` |
| 상태 경로 .loop-engine/ 반영 | 전체 skills/*.md |

### intent 파일: `intent_phase3_claude.md`

```markdown
# Goal
Update loop_engine Claude Code Frontend (RULES.md + skills) to reflect
the new Core features from Phase 1 and unified paths from Phase 2.

# Constraints
- RULES.md HLT conditions must remain intact
- Skills must remain valid Claude Code skill format

# Tasks
1. Update RULES.md: approval payload structure, remediation packet in replan flow
   Reference: /home/h30104109/repos/inno-loop-engineering/plugin/inno-loop-engineering/references/approval-policy.md
2. Update skills/project-init.md: produce charter/design/roadmap as versioned artifacts
   Reference: /home/h30104109/repos/inno-loop-engineering/plugin/inno-loop-engineering/references/artifact-contracts.md
3. Update skills/project-review.md: criterion-ID based rubric, DEFERRED_BACKLOG outcome path
4. Update all skills: state path → .loop-engine/{project_name}/
5. Update CLAUDE_md_snippet.md: reflect new CLI and path

# Success Criteria
- project-review outputs per-criterion pass/fail with IDs
- DEFERRED_BACKLOG is a valid review outcome
- Replan flow includes remediation_packet in handoff
- All path references use .loop-engine/
```

---

## Phase 4 — 스펙 문서 통합

**오케스트레이터:** Claude Code + loop_engine  
**대상 레포:** `loop_engine` (사내 관리 기준)  
**전제:** Phase 3 완료

### 작업 내용

| 항목 | 내용 |
|------|------|
| `loop_engine/docs/spec/` 신설 | — |
| approval-policy.md 이전 | inno-loop 출처 |
| state-machine.md 이전 | inno-loop 출처 |
| artifact-contracts.md 이전 | inno-loop 출처 |
| RULES.md 리팩토링 | 공유 스펙 참조 구조 |
| 양쪽 README 업데이트 | — |

---

## 사전 준비 체크리스트

- [ ] `git -C /home/h30104109/repos/loop_engine commit -m "checkpoint: before integration"`
- [ ] `git -C /home/h30104109/repos/inno-loop-engineering commit -m "checkpoint: before integration"`
- [ ] `loop-engine --version` 확인 (현재 설치 상태 검증)
- [ ] 기존 `.inno-loop/` 또는 `.superpowers/` 데이터 보유 프로젝트 목록화

---

## 주의사항

1. **Phase 1 자기 참조**: loop_engine이 자신을 수정함. editable install이므로 소스 변경 즉시 반영. 신규 모듈은 run 완료 후에만 CLI 호출하도록 intent에 명시.
2. **pip 재설치**: Phase 1 완료 후 반드시 `pip install -e .` 재실행.
3. **Phase 2 마이그레이션**: 기존 데이터 있는 프로젝트는 마이그레이션 스크립트 실행 전 백업.
4. **Phase 3-A Codex 실행**: `loop-engine` binary PATH 확인 후 시작 (`which loop-engine`).
5. **Phase 3-A/3-B 병렬**: 동일 파일 수정 없으므로 동시 진행 가능. 단, 완료 후 통합 테스트 필요.
