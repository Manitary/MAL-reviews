import json
import logging
import pickle
import re
import time
from logging.handlers import TimedRotatingFileHandler
from typing import Any

import requests
from bs4 import BeautifulSoup, Tag
from dotenv import dotenv_values
from ratelimit import limits, sleep_and_retry

from src.models import Anime, RatingTag, Review

CONFIG = dotenv_values()
MAL_HEADERS = {"X-MAL-CLIENT-ID": str(CONFIG["CLIENT_ID"])}
TOP_PAGE = "https://myanimelist.net/topanime.php?limit={limit}"
RE_NUM = re.compile(r"\d+")
RE_RANK = re.compile(r"#(\d+)")
RE_ID = re.compile(r"myanimelist\.net/anime/(\d+)/")
SIZE = 50
ANIME_REVIEWS = "{anime_url}/reviews?spoiler=on&filter_check={rating}"
NUM_ENTRIES = 1000
PATH_DUMP_FILE = "data/data.pickle"

logger = logging.getLogger(__name__)


@sleep_and_retry
@limits(calls=1, period=5)
def rate_limit_get(url: str, **kwargs: Any) -> requests.Response:
    num_attempts = 0
    while True:
        num_attempts += 1
        r = requests.get(url, **kwargs)
        if r.ok:
            return r
        print(f"Request failed: code {r.status_code}")
        time.sleep(num_attempts * 60)


def get_top_page_urls(url: str, **kwargs: Any) -> list[str]:
    bs = BeautifulSoup(rate_limit_get(url=url, **kwargs).text, features="html.parser")
    h = bs.find_all("h3", "anime_ranking_h3")
    return [next(entry.children).attrs["href"] for entry in h]


def get_top_urls(num: int) -> list[str]:
    urls: list[str] = []
    for i in range(0, num, SIZE):
        logger.info("Retrieving URLs for ranks %d-%d", i + 1, i + SIZE)
        urls.extend(get_top_page_urls(TOP_PAGE.format(limit=i)))
    return urls


def parse_review(review: Tag, tag: RatingTag) -> Review:
    rating_element = review.find("span", "num")
    assert isinstance(rating_element, Tag)
    rating = int(rating_element.text)
    if not review.attrs["data-reactions"]:
        icons = (0,) * 3
        count = (0,) * 7
    else:
        reaction_data = json.loads(review.attrs["data-reactions"])
        icons = tuple(map(int, reaction_data["icon"]))
        count = tuple(map(int, reaction_data["count"]))
    return Review(tag=tag, rating=rating, reactions=count, displayed_reactions=icons)


def get_top_reviews_for_rating(
    anime_url: str, rating: RatingTag = RatingTag.ALL, num: int = 3
) -> list[Review]:
    logger.info("Scraping top %d reviews with rating %s", num, rating.name.lower())
    bs = BeautifulSoup(
        rate_limit_get(
            url=ANIME_REVIEWS.format(anime_url=anime_url, rating=rating.value),
            headers=MAL_HEADERS,
        ).text,
        features="html.parser",
    )
    reviews = bs.find_all("div", "review-element")
    if not reviews:
        return []
    return [
        parse_review(review, rating) for review in reviews[: min(len(reviews), num)]
    ]


def extract_rank(bs: BeautifulSoup, rank_type: str) -> int:
    rank_element = bs.find("span", rank_type)
    assert isinstance(rank_element, Tag)
    rank_text = RE_RANK.search(rank_element.text)
    if not rank_text:
        raise AttributeError("No rank found")
    return int(rank_text.group(1))


def extract_id_from_url(url: str) -> int:
    match = RE_ID.search(url)
    if not match:
        raise AttributeError("Invalid URL")
    return int(match.group(1))


def extract_review_count(bs: BeautifulSoup) -> tuple[int, ...]:
    ratio_box = bs.find("div", "review-ratio__box")
    assert isinstance(ratio_box, Tag)
    return tuple(map(int, RE_NUM.findall(ratio_box.text)))


def extract_title(bs: BeautifulSoup) -> str:
    title_element = bs.find("h1", "title-name")
    assert isinstance(title_element, Tag)
    return title_element.text


def get_anime_data(url: str) -> Anime:
    bs = BeautifulSoup(
        rate_limit_get(url=url, headers=MAL_HEADERS).text, features="html.parser"
    )
    anime_id = extract_id_from_url(url)
    title = extract_title(bs)
    rank = extract_rank(bs, "ranked")
    popularity = extract_rank(bs, "popularity")
    review_count = {
        RatingTag(i): count for i, count in enumerate(extract_review_count(bs), 1)
    }
    top_reviews = {
        rating: get_top_reviews_for_rating(url, rating)
        for rating in RatingTag
        if rating != RatingTag.ALL
    }
    return Anime(anime_id, title, url, rank, popularity, review_count, top_reviews)


def main(num: int) -> None:
    urls = get_top_urls(num)
    anime: list[Anime] = []
    for i, url in enumerate(urls, 1):
        logger.info("Processing #%d: %s", i, url)
        print(i, url)
        try:
            entry = get_anime_data(url)
        except Exception as e:
            print("Error")
            logger.exception("Failed to  process %s\nException: %s", url, e)
        else:
            anime.append(entry)
    with open(PATH_DUMP_FILE, "wb") as f:
        pickle.dump(anime, f)


if __name__ == "__main__":
    log_file = f"logs/reviews.log"
    logging.basicConfig(
        handlers=[
            TimedRotatingFileHandler(
                log_file, when="midnight", backupCount=7, encoding="UTF-8"
            )
        ],
        format="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )
    logger.info("-" * 60)
    main(num=NUM_ENTRIES)
    logger.info("-" * 60 + "\n\n")
