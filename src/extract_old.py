"""Unreliable, use extract instead.

Unreliable due to how MAL displays top reviews on an anime main page.  
The displayed reviews are not chosen consistently:  
sometimes it's top three voted, sometimes it's three newest, sometimes recommended, etc."""

import enum
import json
import time
from typing import Any
import re

import requests
from bs4 import BeautifulSoup, Tag
from dotenv import dotenv_values
from ratelimit import limits, sleep_and_retry

CONFIG = dotenv_values()
MAL_HEADERS = {"X-MAL-CLIENT-ID": str(CONFIG["CLIENT_ID"])}
RANKING_API = (
    "https://api.myanimelist.net/v2/anime/ranking"
    "?ranking_type={type}&limit={limit}&offset={offset}"
)
ANIME_PAGE = "https://myanimelist.net/anime/{id}"
SIZE = 500
RE_NUM = re.compile(r"\d+")


class Rating(enum.StrEnum):
    RECOMMENDED = "recommended"
    MIXED_FEELINGS = "mixed-feelings"
    NOT_RECOMMENDED = "not-recommended"


@sleep_and_retry
@limits(calls=1, period=5)
def rate_limit_get(**kwargs: Any) -> requests.Response:
    return requests.get(**kwargs)


def get_top(num: int, ranking_type: str = "all") -> list[dict[str, Any]]:
    data: list[dict[str, Any]] = []
    d, r = num // SIZE, num % SIZE
    for i in range(d + (r > 0)):
        url = RANKING_API.format(
            type=ranking_type, limit=SIZE if i < d else r, offset=SIZE * i
        )
        response = rate_limit_get(url=url, headers=MAL_HEADERS)
        data.extend(response.json()["data"])
    return data


def find_div_value(bs: BeautifulSoup, attr: str) -> int:
    element = bs.find("div", attr)
    assert isinstance(element, Tag)
    num = RE_NUM.search(element.text)
    if not num:
        raise AttributeError("Number of reviews not found")
    return int(num.group())


def get_review_data(review: Tag) -> tuple[Rating, tuple[int, ...]]:
    rating_element = review.find("div", "tag")
    assert isinstance(rating_element, Tag)
    rating = Rating(rating_element.attrs["class"][1])
    try:
        reactions: tuple[int, ...] = tuple(
            map(int, json.loads(review.attrs["data-reactions"])["count"])
        )
    except json.JSONDecodeError:
        reactions: tuple[int, ...] = ()
    return rating, reactions


def get_top_recs(bs: BeautifulSoup) -> tuple[tuple[Rating, tuple[int, ...]], ...]:
    # Will not always work as the displayed reviews are not chosen consistently
    # Sometimes it's top three voted, sometimes it's three newest, sometimes recommended, etc.
    return tuple(
        get_review_data(review) for review in bs.find_all("div", "review-element")
    )


def get_reviews_recap(bs: BeautifulSoup) -> tuple[int, ...]:
    return tuple(find_div_value(bs, str(rating)) for rating in Rating)


def get_anime_reviews_data(
    anime_id: int,
) -> dict[str, Any]:
    url = ANIME_PAGE.format(id=anime_id)
    n_attempts = 0
    while True:
        n_attempts += 1
        r = rate_limit_get(url=url, headers=MAL_HEADERS)
        if r.ok:
            break
        print(f"Status code: {r.status_code} -- sleeping")
        time.sleep(60 * n_attempts)
    bs = BeautifulSoup(r.text, features="html.parser")
    recs = get_reviews_recap(bs)
    top_recs = get_top_recs(bs)
    return {"recs": recs, "top_recs": top_recs}


def main() -> None:
    anime_list: list[dict[str, Any]] = [entry["node"] for entry in get_top(1000)]
    for i, anime in enumerate(anime_list, 1):
        print(i, anime["id"])
        anime |= get_anime_reviews_data(anime["id"])
    with open("data/data.json", "w", encoding="utf-8") as f:
        json.dump(anime_list, f)


if __name__ == "__main__":
    main()
