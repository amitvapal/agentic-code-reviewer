"""Pydantic models for review findings and results."""

from typing import Literal

from pydantic import BaseModel, Field


class Finding(BaseModel):
    """A single issue raised by one of the review chains."""

    kind: Literal["bug", "style", "refactor"]
    file: str
    line: int | None = None
    severity: Literal["low", "medium", "high"]
    summary: str
    detail: str
    suggested_fix: str | None = None


class ChainResult(BaseModel):
    """The structured output of one chain: its findings plus its CoT reasoning."""

    findings: list[Finding] = Field(default_factory=list)
    reasoning: str = ""


class Review(BaseModel):
    """The aggregated, de-duplicated result of reviewing a diff."""

    findings: list[Finding] = Field(default_factory=list)
    summary: str = ""
