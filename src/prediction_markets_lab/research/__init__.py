"""Research Engine.

Lightweight governance layer for the Prediction Markets Lab research
process: hypothesis registry, behaviour atlas, research results,
evidence grading, and research prioritisation. See
docs/RESEARCH_ENGINE.md for the full design and lifecycle.

This is a CSV + pydantic layer, matching the rest of the project's
near-£0, phone-first architecture — no database, no ML pipeline.
"""

from __future__ import annotations
