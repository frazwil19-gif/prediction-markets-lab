# Contributing

This is a personal, low-cost research project. These notes are mainly
for future-you (or Claude/ChatGPT in a future session) picking this
back up.

## Principles

- Keep it free. Do not add a dependency that requires payment, an API
  key with a paid tier, or a cloud service, without updating
  `docs/PROJECT_PLAN.md` and `README.md` cost sections first.
- Keep it modular. Each new sport/category should slot into the
  existing `ingestion/ → normalisation/ → probability/ → models/ → ev/
  → risk/ → decisions/` pipeline rather than growing its own parallel
  structure.
- No magic numbers. Every threshold belongs in `config/*.yaml`, not
  hard-coded in Python.
- No unvalidated methodology changes. Do not swap the margin-removal
  method, change grading thresholds, or alter model weights without
  documenting the change and rationale in the relevant `docs/*.md`
  file and `CHANGELOG.md`.
- Every calculation function needs a unit test. Every new module
  should have a corresponding file under `tests/unit/` or
  `tests/integration/`.

## Workflow

1. Make changes on a branch or directly if working solo.
2. Run `pytest` — all tests must pass before committing.
3. Update `CHANGELOG.md` with what changed.
4. Commit with a clear, conventional-style message
   (`feat: ...`, `fix: ...`, `docs: ...`, `test: ...`, `chore: ...`).
5. Update `docs/ROADMAP.md` if a stage boundary was crossed.

## Coding standards

See project instructions section 20, summarised: typed functions,
docstrings, modular design, configuration-driven thresholds, no magic
numbers, deterministic calculations, unit + integration tests,
explicit error handling (raise `ValueError` with a clear message, do
not silently coerce bad input), reproducible reports, simple CLI,
minimal dependencies (`pandas`, `numpy`, `pydantic`, `PyYAML`,
`pytest` — add anything else only with a clear justification).
