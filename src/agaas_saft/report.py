"""Versioned, JSON-serializable results shared by the library and process interface."""

from dataclasses import asdict, dataclass, field
from typing import Literal

from . import __version__

MAX_ISSUES = 100


@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    line: int | None = None
    path: str | None = None


@dataclass
class Report:
    kind: str
    status: Literal["valid", "invalid", "error"] = "valid"
    checks: dict[str, str] = field(default_factory=dict)
    issues: list[Issue] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    truncated: bool = False

    def add(self, code: str, message: str, *, line=None, path=None, error=False):
        if error or self.status == "error":
            self.status = "error"
        else:
            self.status = "invalid"
        if len(self.issues) < MAX_ISSUES:
            self.issues.append(Issue(code, message, line, path))
        else:
            self.truncated = True

    @property
    def exit_code(self) -> int:
        return {"valid": 0, "invalid": 1, "error": 2}[self.status]

    def to_dict(self) -> dict:
        return {
            "interface_version": 1,
            "validator_version": __version__,
            **asdict(self),
        }
