import datetime as dt
import json
import logging
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import parse_qs, urlparse

import httpx

from .config import HOME_URI, NEXT_FEED_TEXT, POST_URL_TEXT
from .facebook_scraper import create_url, fetch_html, get_first_child
from .utils import iterate, take_nth

logger = logging.getLogger(__name__)


@dataclass
class Post:
    timestamp: str
    content: str
    hashtags: list[str]
    profiles: list[str]
    pages: list[str]
    photos: list[str]
    videos: list[str]
    likes: int
    comments: int
    url: str = field(repr=False)


async def fetch_feed_generator(s: httpx.AsyncClient, page_id: str):
    uri = _create_feed_uri(page_id)
    soup = await fetch_html(s, uri)
    try:
        posts_soups = soup.find(attrs={"class": "feed"}).find().children
    except AttributeError:
        logger.error("Could not parse feed")
        return

    while True:
        for p in posts_soups:
            yield p

        next_uri = _get_next_feed_stream_uri(soup)
        if next_uri is None:
            break
        soup = await fetch_html(s, next_uri)
        table = soup.find_all("table")[1]
        contrainer = iterate(get_first_child, table)
        posts_soups = take_nth(5, contrainer).children


def _create_feed_uri(page_id: str) -> str:
    return f"{HOME_URI}/{page_id}/?v=timeline"


def _get_next_feed_stream_uri(soup):
    el = soup.find(string=NEXT_FEED_TEXT)
    if el is None:
        return None
    next_posts_url = el.find_parent().find_parent().get("href")
    return create_url(next_posts_url)


async def create_post_from_soup(s: httpx.AsyncClient, post) -> Optional[Post]:
    try:
        uri = create_url(_get_post_uri(post))
        content_container = await parse_content(s, uri)
        if content_container is None:
            logger.error("Could not parse post")
            return None

        content, hashtags, profiles, pages, photos, videos = content_container
        return Post(
            timestamp=get_timestamp(post).isoformat(),
            content=content,
            hashtags=hashtags,
            profiles=profiles,
            pages=pages,
            photos=photos,
            videos=videos,
            likes=_get_number_of_likes(post),
            comments=_get_number_of_comments(post),
            url=uri,
        )
    except:
        return None


def get_timestamp(post):
    page_insights = list(json.loads(post.get("data-ft"))["page_insights"].values())[0]
    post_context = page_insights["post_context"]
    publish_time = post_context["publish_time"]
    return dt.datetime.fromtimestamp(publish_time)


def _get_number_of_likes(post):
    footer = list(post.children)[1]
    return int(footer.a.text)


def _get_number_of_comments(post):
    footer = list(post.children)[1]
    stats = list(footer.children)[1]
    comments_section = list(stats.children)[2]
    comments_components = comments_section.text.split()
    if comments_components[0].isnumeric():
        comments = int(comments_components[0])
    elif comments_components[-1].isnumeric():
        comments = int(comments_components[-1])
    else:
        comments = 0
    return comments


def _get_post_uri(post):
    return post.find(string=POST_URL_TEXT).find_parent().get("href")


async def parse_content(s: httpx.AsyncClient, uri: str):
    soup = await fetch_html(s, uri)
    full_post_url = "m_story_permalink_view"
    post = soup.find(id=full_post_url)

    if post is None:
        logger.error("Could not find {full_post_url!r} in post")
        return None

    content = []
    hashtags = []
    profiles = []
    pages = []
    photos = []
    videos = []

    p = post.find("p")
    if p is None or isinstance(p, int):
        return None

    paragraphs = [p, *p.find_next_siblings("p")]
    for p in paragraphs:
        content += p.stripped_strings
        for a in p.findAll("a"):
            url = urlparse(a.get("href"))
            if url.path.startswith("/hashtag") or url.path.startswith("/watch/hashtag"):
                value = url.path.strip("/").split("/")[-1]
                hashtags.append(value)
            elif url.path.startswith("/profile.php"):
                value = parse_qs(url.query)['id']
                profiles.append(value)
            elif url.path.startswith("/photo.php"):
                value = parse_qs(url.query)['fbid']
                photos.append(value)
            elif url.path.startswith("/video_redirect"):
                value = parse_qs(url.query)['src']
                videos.append(value)
            elif url.path.startswith("/l.php"):
                # TODO: handle links
                ...
            else:
                value = url.path.strip('/')
                pages.append(value)

    return " ".join(content), hashtags, profiles, pages, photos, videos
