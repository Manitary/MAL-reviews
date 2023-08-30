from typing import Counter

from src.models import Anime, RatingTag, Review

ReviewCount = Counter[tuple[str, ...]]


def get_pct_rating(
    data: list[Anime], rating: RatingTag
) -> list[tuple[int, int, str, float]]:
    pct = [
        (
            anime.rank,
            anime.id,
            anime.title,
            round(
                anime.review_count[rating] / sum(anime.review_count.values()) * 100,
                2,
            )
            if sum(anime.review_count.values()) > 0
            else 0,
        )
        for anime in data
    ]
    return pct


def top_n_ratings(data: list[Anime], n: int = 3) -> ReviewCount:
    return Counter(
        tuple(map(Review.get_tag_name, anime.top_n_reviews(n))) for anime in data
    )


def num_anime_with_non_positive(data: ReviewCount) -> int:
    return sum(
        data[x]
        for x in data
        if any(rating != RatingTag.RECOMMENDED.name for rating in x)
    )


def num_top_not_positive(data: ReviewCount) -> int:
    return sum(data[x] for x in data if x and x[0] != RatingTag.RECOMMENDED.name)


def num_no_positive(data: ReviewCount) -> int:
    return sum(data[x] for x in data if RatingTag.RECOMMENDED.name not in x)


def negative_review_data(data: list[Anime]) -> list[tuple[int, int, int, int, float]]:
    negative = [
        (
            anime.rank,
            anime.id,
            i,
            review.num_reactions,
            round(
                (review.reactions[2] + review.reactions[3]) / review.num_reactions * 100
                if review.num_reactions > 0
                else 0,
                2,
            ),
        )
        for anime in data
        for i, review in enumerate(anime.top_n_reviews(3), 1)
        if review.tag == RatingTag.NOT_RECOMMENDED
    ]
    return negative


def no_review(data: list[Anime]) -> list[tuple[int, int, str]]:
    return [
        (anime.rank, anime.id, anime.title)
        for anime in data
        if not sum(anime.review_count.values())
    ]


def all_top_negative(data: list[Anime]) -> list[tuple[int, int, str]]:
    return [
        (anime.rank, anime.id, anime.title)
        for anime in data
        if sum(anime.review_count.values())
        and all(
            review.tag == RatingTag.NOT_RECOMMENDED for review in anime.top_n_reviews(3)
        )
    ]
