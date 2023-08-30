from __future__ import annotations

import enum
import itertools
from dataclasses import dataclass
from functools import cached_property


class RatingTag(enum.IntEnum):
    ALL = 0
    RECOMMENDED = 1
    MIXED_FEELINGS = 2
    NOT_RECOMMENDED = 3


class Reaction(enum.IntEnum):
    NICE = 0
    LOVE_IT = 1
    FUNNY = 2
    CONFUSING = 3
    INFORMATIVE = 4
    WELL_WRITTEN = 5
    CREATIVE = 6


@dataclass
class Review:
    tag: RatingTag
    rating: int
    reactions: tuple[int, ...]
    displayed_reactions: tuple[int, ...]

    @staticmethod
    def get_tag_name(review: Review) -> str:
        return review.tag.name

    @cached_property
    def num_reactions(self) -> int:
        return sum(self.reactions)


@dataclass
class Anime:
    id: int
    title: str
    url: str
    rank: int
    popularity: int
    review_count: dict[RatingTag, int]
    top_reviews: dict[RatingTag, list[Review]]

    def top_n_reviews(self, n: int) -> list[Review]:
        return sorted(
            list(itertools.chain(*self.top_reviews.values())),
            key=lambda x: sum(x.reactions),
            reverse=True,
        )[:n]
