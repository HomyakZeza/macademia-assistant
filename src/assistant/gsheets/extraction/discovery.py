import re
from dataclasses import dataclass, field


_RANGE_RE = re.compile(r"^(.+?)\s+(\d+)\s*-\s*(\d+)$")

_LIST_RE = re.compile(r"^(.+?)\s+(\d+(?:\s*,\s*\d+)+)$")

_SINGLE_RE = re.compile(r"^(.+?)\s+(\d+)$")


@dataclass
class ParsedSheetName:
    raw_name: str
    subject: str
    classes: list[str] = field(default_factory=list)
    format_matched: str = "unknown"


def parse_sheet_name(raw_name: str) -> ParsedSheetName:
    name = raw_name.strip()

    m = _LIST_RE.match(name)
    if m:
        subject = m.group(1).strip()
        classes = [c.strip() for c in m.group(2).split(",")]
        return ParsedSheetName(
            raw_name=raw_name,
            subject=subject,
            classes=classes,
            format_matched="list",
        )

    m = _RANGE_RE.match(name)
    if m:
        subject = m.group(1).strip()
        start, end = m.group(2), m.group(3)
        if int(start) <= int(end):
            classes = [str(n) for n in range(int(start), int(end) + 1)]
        else:
            classes = [start, end]
        return ParsedSheetName(
            raw_name=raw_name,
            subject=subject,
            classes=classes,
            format_matched="range",
        )

    m = _SINGLE_RE.match(name)
    if m:
        return ParsedSheetName(
            raw_name=raw_name,
            subject=m.group(1).strip(),
            classes=[m.group(2)],
            format_matched="single",
        )

    return ParsedSheetName(
        raw_name=raw_name,
        subject=name,
        classes=[],
        format_matched="subject_only",
    )