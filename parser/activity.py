from __future__ import annotations

from dataclasses import dataclass, field

from parser.diff import JobChange


@dataclass
class ActivitySummary:
    new: int = 0
    updated: int = 0
    closed: int = 0
    reopened: int = 0
    changes: list[JobChange] = field(default_factory=list)

    @property
    def actionable(self) -> int:
        return self.new + self.updated + self.reopened

    def headline(self) -> str:
        if self.new > 0:
            base = f"{self.new} new iOS vacancies"
            if self.updated or self.reopened:
                base += f" (+ {self.updated} updated, {self.reopened} reopened)"
            return base
        if self.actionable > 0:
            return f"{self.actionable} actionable opportunities ({self.updated} updated, {self.reopened} reopened)"
        if self.closed > 0:
            return f"No new opportunities; {self.closed} positions closed"
        return "Market unchanged this run"

    def render(self) -> str:
        lines = [
            "Run Activity",
            "",
            f"Actionable: {self.actionable}",
            f"New:        {self.new}",
            f"Updated:    {self.updated}",
            f"Closed:     {self.closed}",
            f"Reopened:   {self.reopened}",
            "",
            self.headline(),
        ]
        return "\n".join(lines)
