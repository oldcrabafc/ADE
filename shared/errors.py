from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ADEError(Exception):
    code: str
    message: str

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


def validation_error(message: str) -> ADEError:
    return ADEError("ADE-IMP-001", message)


def export_error(message: str) -> ADEError:
    return ADEError("ADE-EXP-003", message)
