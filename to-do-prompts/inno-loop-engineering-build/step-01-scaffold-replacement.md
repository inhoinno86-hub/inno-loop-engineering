# Step 01 Prompt — Scaffold Replacement

## Goal

Create `plugin/inno-loop-engineering` as a valid Codex plugin without touching the legacy plugin.

## Baseline

Use `main` and `inno-loop-engineering-신규개발개요.md` as the baseline.

## Scope

Inspect the existing plugin layout and create `.codex-plugin/plugin.json`, `skills/`, `scripts/`, `references/`, `assets/templates/`, and `tests/` for the new plugin.

## Instructions

Use the plugin scaffold tooling where applicable. Set a concrete name and description. Keep external marketplace installation out of this implementation unless it is required by validation.

## Constraints

Do not modify `plugin/project-loop` in this step. Do not leave manifest placeholders.

## Expected Deliverable

A manifest-backed replacement plugin directory.

## Completion Criteria

- `plugin/inno-loop-engineering/.codex-plugin/plugin.json` exists.
- The manifest name matches the directory name.
- Plugin validation succeeds.

## Next Step Handoff

Use the created folders for contracts and templates.
