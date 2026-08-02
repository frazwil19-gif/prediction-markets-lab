# Daily Workflow

**Status: planned for Stage 2. Not yet implemented.**

```
ChatGPT daily scan
  ↓
Candidate football and tennis events
  ↓
User checks bookmaker and exchange odds
  ↓
User pastes prices into ChatGPT or Google Sheets
  ↓
ChatGPT calculates fair probability and EV
  ↓
ChatGPT returns A+, A, B, C or Reject
  ↓
User manually places qualifying trade
  ↓
Trade recorded in Google Sheets
  ↓
Result and closing price logged later
```

## Constraints on this workflow

- Must not require a desktop computer every day.
- Must not require a local server or constant Python execution.
- Must not require a paid cloud environment.
- Must not require continuous API polling.
- Heavy setup (this repository, Sheets structure) is a one-time cost;
  daily operation must be simple enough to do from a phone in a short
  session.

## Stage 1 note

The calculation functions this workflow will call
(`probability.consensus`, `ev.expected_value`, `decisions.grading`,
etc.) exist and are unit-tested now. What's missing is the glue: CSV
templates for manual entry, the report generator, and the Google
Sheets read/write adapter. See `docs/ROADMAP.md` for sequencing.
