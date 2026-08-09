from __future__ import annotations

from pathlib import Path

HOTEL_ASSISTANT_INSTRUCTIONS = (
    Path(__file__)
    .with_name("SKILL.md")
    .read_text(
        encoding="utf-8",
    )
    .strip()
)
