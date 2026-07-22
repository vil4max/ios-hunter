from __future__ import annotations

from planner.plan import DailyPlan


def pipeline_counts(plan: DailyPlan) -> dict[str, int]:
    return dict(plan.status_counts)


def summarize_funnel(plan: DailyPlan) -> str:
    counts = plan.status_counts
    applied = counts.get("Applied", 0)
    archived = counts.get("Archived", 0)
    inbox = counts.get("Inbox", 0)
    return (
        f"Inbox {inbox}, Applied {applied}, Archived {archived}, "
        f"attention {len(plan.needs_attention)}, follow-ups due {len(plan.pending_follow_ups)}."
    )
