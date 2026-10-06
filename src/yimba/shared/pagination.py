from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, Sequence, TypeVar

T = TypeVar("T")

MAX_PAGE_SIZE = 100


@dataclass(frozen=True, slots=True)
class PageParams:
    page: int = 1
    size: int = 20

    def __post_init__(self) -> None:
        if self.page < 1:
            raise ValueError("page must be >= 1")
        if not 1 <= self.size <= MAX_PAGE_SIZE:
            raise ValueError(f"size must be between 1 and {MAX_PAGE_SIZE}")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


@dataclass(frozen=True, slots=True)
class Page(Generic[T]):
    items: Sequence[T] = field(default_factory=tuple)
    total: int = 0
    page: int = 1
    size: int = 20
