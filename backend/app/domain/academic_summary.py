"""Deterministic academic-history summary (AGENTS.md Rule 8: no scores, no LLM, same input -> same output).

Derived from stored marksheet rows only. It never invents marks, subjects or semesters and never
writes back to the source records.
"""

from __future__ import annotations

LIMITED_HISTORY_NOTE = "Summary is based on limited available records (fewer than 2 semesters)."


def summarize(history: list[dict]) -> dict:
    """`history` is chronological: [{semester, subjects: {name: marks}, cgpa}, ...]."""
    if not history:
        return {"available": False, "limited_history": True,
                "points": ["No marksheet records are available for this student."]}

    points: list[str] = []
    limited = len(history) < 2
    if limited:
        points.append(LIMITED_HISTORY_NOTE)

    cgpas = [(h["semester"], h["cgpa"]) for h in history if h.get("cgpa") is not None]
    trend = "insufficient_data"
    if len(cgpas) >= 2:
        first, last = cgpas[0], cgpas[-1]
        delta = round(last[1] - first[1], 2)
        trend = "improving" if delta > 0 else "declining" if delta < 0 else "steady"
        points.append(f"CGPA moved from {first[1]} (semester {first[0]}) to {last[1]} (semester {last[0]}): {trend}.")
        if len(cgpas) >= 3:
            biggest = max(zip(cgpas, cgpas[1:]), key=lambda p: abs(p[1][1] - p[0][1]))
            change = round(biggest[1][1] - biggest[0][1], 2)
            if change != 0:
                points.append(f"Largest semester-to-semester change: {change:+} (semester {biggest[0][0]} to {biggest[1][0]}).")
    elif len(cgpas) == 1:
        points.append(f"Only one CGPA is recorded: {cgpas[0][1]} (semester {cgpas[0][0]}).")

    latest = history[-1]
    subjects = {k: v for k, v in (latest.get("subjects") or {}).items() if isinstance(v, (int, float))}
    if subjects:
        best = max(sorted(subjects), key=lambda k: subjects[k])
        weakest = min(sorted(subjects), key=lambda k: subjects[k])
        points.append(f"In semester {latest['semester']}, highest marks: {best} ({subjects[best]}); lowest marks: {weakest} ({subjects[weakest]}).")

    return {"available": True, "limited_history": limited, "cgpa_trend": trend,
            "semesters_covered": [h["semester"] for h in history], "points": points}
