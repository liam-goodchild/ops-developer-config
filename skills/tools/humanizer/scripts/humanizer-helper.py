#!/usr/bin/env python3
"""Deterministic analyzer for the humanizer skill.

The script does not rewrite text. It surfaces likely AI-writing tells so the
agent can spend its tokens on judgement and prose rather than mechanical scans.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MAX_TEXT_CHARS = 200_000
SNIPPET_RADIUS = 70


@dataclass(frozen=True)
class Rule:
    rule: str
    category: str
    severity: str
    pattern: re.Pattern[str]
    fix: str


RULES: tuple[Rule, ...] = (
    Rule(
        "inflated-significance",
        "content",
        "medium",
        re.compile(r"\b(?:serves as|stands as|is a testament to|is a reminder of|plays a (?:vital|significant|crucial|pivotal|key) role|underscores?|highlights? (?:the )?(?:importance|significance)|reflects broader|sets? the stage for|marks? a (?:shift|turning point)|evolving landscape|indelible mark)\b", re.I),
        "Replace broad significance claims with the concrete thing that happened.",
    ),
    Rule(
        "promotional-language",
        "tone",
        "medium",
        re.compile(r"\b(?:boasts?|vibrant|rich cultural|profound|showcas(?:e|es|ing)|exemplif(?:y|ies|ying)|commitment to|groundbreaking|renowned|breathtaking|must-visit|stunning|seamless|world-class)\b", re.I),
        "Use plain description instead of brochure language.",
    ),
    Rule(
        "vague-attribution",
        "evidence",
        "high",
        re.compile(r"\b(?:industry reports|observers have cited|experts (?:argue|believe|say)|some critics argue|several sources|many believe|it is widely believed|studies show|research suggests)\b", re.I),
        "Name the source, cite the evidence, or remove the attribution.",
    ),
    Rule(
        "ai-vocabulary",
        "language",
        "low",
        re.compile(r"\b(?:additionally|align with|crucial|delve|emphasizing|enduring|enhance|fostering|garner|highlight|interplay|intricate|intricacies|pivotal|showcase|tapestry|testament|underscore|valuable|landscape)\b", re.I),
        "Keep only if it is the simplest accurate word; otherwise use plainer wording.",
    ),
    Rule(
        "superficial-ing-clause",
        "syntax",
        "medium",
        re.compile(r",\s+(?:highlighting|underscoring|emphasizing|ensuring|reflecting|symbolizing|contributing to|cultivating|fostering|encompassing|showcasing)\b[^.!?;]*", re.I),
        "Turn the claim into a concrete sentence or delete it if it adds no information.",
    ),
    Rule(
        "copula-avoidance",
        "syntax",
        "low",
        re.compile(r"\b(?:serves as|stands as|features|offers|boasts)\b", re.I),
        "Use simple verbs such as is, has, or includes when they are clearer.",
    ),
    Rule(
        "negative-parallelism",
        "structure",
        "medium",
        re.compile(r"\bnot only\b[^.!?;]{0,160}\bbut also\b|\bit'?s not just about\b[^.!?;]{0,160}\bit'?s\b", re.I),
        "State the point directly instead of using a not-only-but-also frame.",
    ),
    Rule(
        "false-range",
        "structure",
        "low",
        re.compile(r"\bfrom\s+[^.!?;]{3,80}\s+to\s+[^.!?;]{3,80}", re.I),
        "Check whether the range is meaningful; if not, list the concrete items.",
    ),
    Rule(
        "em-dash",
        "style",
        "medium",
        re.compile(r"—|&mdash;|&#8212;", re.I),
        "Use a comma, period, parentheses, colon, or plain hyphen instead.",
    ),
    Rule(
        "bold-inline-header",
        "style",
        "low",
        re.compile(r"(?m)^\s*[-*]\s+\*\*[^*\n]{1,60}\*\*:\s+"),
        "Avoid repeated bold label list items unless the structure genuinely helps.",
    ),
    Rule(
        "filler-transition",
        "language",
        "low",
        re.compile(r"\b(?:it is important to note that|it is worth noting that|in today'?s (?:world|landscape)|at the end of the day|when it comes to|in conclusion|ultimately)\b", re.I),
        "Cut the throat-clearing and start with the actual point.",
    ),
    Rule(
        "passive-construction",
        "syntax",
        "low",
        re.compile(r"\b(?:is|are|was|were|be|been|being)\s+(?:created|built|managed|handled|processed|generated|configured|implemented|designed|written|used|provided|preserved|improved|enhanced)\b", re.I),
        "Prefer active voice when the actor matters or the sentence feels vague.",
    ),
)


class HumanizerError(RuntimeError):
    """Expected user-facing failure."""


def load_text(args: argparse.Namespace) -> tuple[str, str]:
    if args.text is not None and args.file is not None:
        raise HumanizerError("Use either --text or --file, not both")
    if args.text is not None:
        return args.text, "inline"
    if args.file is None:
        raise HumanizerError("Provide --text or --file")

    path = Path(args.file).expanduser().resolve()
    if not path.exists():
        raise HumanizerError(f"File does not exist: {path}")
    if not path.is_file():
        raise HumanizerError(f"Path is not a file: {path}")
    text = path.read_text(encoding="utf-8")
    return text, str(path)


def sentence_split(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [part.strip() for part in parts if part.strip()]


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w']+\b", text))


def line_col(text: str, index: int) -> tuple[int, int]:
    line = text.count("\n", 0, index) + 1
    last_newline = text.rfind("\n", 0, index)
    col = index + 1 if last_newline < 0 else index - last_newline
    return line, col


def snippet(text: str, start: int, end: int) -> str:
    left = max(0, start - SNIPPET_RADIUS)
    right = min(len(text), end + SNIPPET_RADIUS)
    value = text[left:right].replace("\n", " ")
    return re.sub(r"\s+", " ", value).strip()


def analyze_findings(text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, int, int]] = set()
    for rule in RULES:
        for match in rule.pattern.finditer(text):
            key = (rule.rule, match.start(), match.end())
            if key in seen:
                continue
            seen.add(key)
            line, col = line_col(text, match.start())
            findings.append(
                {
                    "rule": rule.rule,
                    "category": rule.category,
                    "severity": rule.severity,
                    "line": line,
                    "column": col,
                    "match": match.group(0)[:160],
                    "snippet": snippet(text, match.start(), match.end()),
                    "fix": rule.fix,
                }
            )
    findings.sort(key=lambda item: (item["line"], item["column"], item["rule"]))
    return findings


def analyze_rhythm(text: str) -> dict[str, Any]:
    sentences = sentence_split(text)
    lengths = [word_count(sentence) for sentence in sentences]
    starts = []
    for sentence in sentences:
        words = re.findall(r"\b[\w']+\b", sentence.lower())
        if words:
            starts.append(" ".join(words[:2]) if len(words) > 1 else words[0])
    repeated_starts = [
        {"start": start, "count": count}
        for start, count in Counter(starts).most_common()
        if count > 1
    ][:10]

    if not lengths:
        return {
            "sentence_count": 0,
            "average_words": 0,
            "min_words": 0,
            "max_words": 0,
            "stdev_words": 0,
            "repeated_starts": [],
        }

    return {
        "sentence_count": len(lengths),
        "average_words": round(sum(lengths) / len(lengths), 1),
        "min_words": min(lengths),
        "max_words": max(lengths),
        "stdev_words": round(statistics.pstdev(lengths), 1) if len(lengths) > 1 else 0,
        "repeated_starts": repeated_starts,
    }


def rule_of_three_findings(text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    pattern = re.compile(r"\b[^.!?\n,;]{2,50},\s+[^.!?\n,;]{2,50},\s+(?:and|or)\s+[^.!?\n,;]{2,50}")
    for match in pattern.finditer(text):
        segment = match.group(0)
        # Skip obvious front matter and data-like short lists.
        if len(segment) < 30 or re.search(r"[`{}\[\]=]", segment):
            continue
        line, col = line_col(text, match.start())
        findings.append(
            {
                "rule": "rule-of-three",
                "category": "structure",
                "severity": "low",
                "line": line,
                "column": col,
                "match": segment[:160],
                "snippet": snippet(text, match.start(), match.end()),
                "fix": "Check whether the three-part list is natural or just filler symmetry.",
            }
        )
    return findings[:20]


def analyze(text: str, source: str, limit: int = 80) -> dict[str, Any]:
    risk_flags: list[dict[str, str]] = []
    if not text.strip():
        risk_flags.append({"severity": "high", "reason": "input text is empty"})
    if len(text) > MAX_TEXT_CHARS:
        risk_flags.append({"severity": "medium", "reason": f"input text exceeds {MAX_TEXT_CHARS} characters; analysis was truncated"})
        text = text[:MAX_TEXT_CHARS]

    findings = analyze_findings(text)
    findings.extend(rule_of_three_findings(text))
    findings.sort(key=lambda item: (item["line"], item["column"], item["rule"]))

    categories = Counter(item["category"] for item in findings)
    rules = Counter(item["rule"] for item in findings)
    severity = Counter(item["severity"] for item in findings)

    return {
        "ok": not any(flag["severity"] == "high" for flag in risk_flags),
        "source": source,
        "summary": {
            "characters": len(text),
            "words": word_count(text),
            "ai_tell_count": len(findings),
            "top_categories": [{"category": key, "count": value} for key, value in categories.most_common(8)],
            "top_rules": [{"rule": key, "count": value} for key, value in rules.most_common(10)],
            "severity_counts": dict(severity),
        },
        "rhythm": analyze_rhythm(text),
        "risk_flags": risk_flags,
        "findings": findings[: max(0, limit)],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze text for common AI-writing patterns")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze")
    source = analyze_parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text")
    source.add_argument("--file")
    analyze_parser.add_argument("--limit", type=int, default=80, help="Maximum findings to return")
    analyze_parser.add_argument("--json", action="store_true", help="Emit JSON (default)")

    parsed = parser.parse_args()

    try:
        text, source_name = load_text(parsed)
        result = analyze(text, source_name, parsed.limit)
        print(json.dumps(result, indent=2))
        return 0 if result.get("ok", False) else 2
    except HumanizerError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

