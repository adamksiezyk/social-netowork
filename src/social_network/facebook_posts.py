import datetime as dt
import json
from dataclasses import dataclass, field

from .config import NEXT_FEED_TEXT, POST_URL_TEXT, home_uri, tz
from .facebook_scraper import create_url, fetch_html, get_first_child
from .utils import iterate, take_nth


def create_posts_uri(page_id: str) -> str:
    return f"{home_uri}/{page_id}/?v=timeline"


def get_posts_as_soups(soup):
    return soup.find(attrs={"class": "feed"}).find().children


def get_next_posts_url(soup):
    el = soup.find(string=NEXT_FEED_TEXT)
    if el is None:
        return None
    next_posts_url = el.find_parent().find_parent().get("href")
    return create_url(next_posts_url)


@dataclass
class Post:
    timestamp: dt.datetime
    content: str
    likes: int
    comments: int
    url: str = field(repr=False)


def create_post_from_soup(post):
    try:
        return Post(
            timestamp=get_timestamp(post),
            content=get_content(post),
            likes=get_number_of_likes(post),
            comments=get_number_of_comments(post),
            url=get_url(post),
        )
    except:
        return None


def get_timestamp(post):
    page_insights = list(json.loads(post.get("data-ft"))
                         ["page_insights"].values())[0]
    post_context = page_insights["post_context"]
    publish_time = post_context["publish_time"]
    return dt.datetime.fromtimestamp(publish_time).astimezone(tz)


def get_content(post):
    paragraph = post.find("p")
    return " ".join(paragraph.stripped_strings)


def get_number_of_likes(post):
    footer = list(post.children)[1]
    return int(footer.a.text)


def get_number_of_comments(post):
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


def get_url(post):
    return post.find(string=POST_URL_TEXT).find_parent().get("href")


def fetch_feed(s, page_id: str):
    uri = create_posts_uri(page_id)
    soup = fetch_html(s, uri)
    posts_soups = get_posts_as_soups(soup)
    posts = [create_post_from_soup(p) for p in posts_soups]
    yield from posts

    next_url = get_next_posts_url(soup)
    if next_url is not None:
        yield from fetch_feed_stream(s, next_url)


def fetch_feed_stream(s, url):
    soup = fetch_html(s, url)
    contrainer = iterate(get_first_child, soup.find_all("table")[1])
    posts_soups = take_nth(5, contrainer).children
    posts = [create_post_from_soup(p) for p in posts_soups]
    yield from posts

    next_url = get_next_posts_url(soup)
    if next_url is not None:
        yield from fetch_feed_stream(s, next_url)
