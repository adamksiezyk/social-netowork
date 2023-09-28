import time
from dataclasses import dataclass, field
from typing import Optional

from social_network.config import NEXT_FRIENDS_TEXT, friends_path, home_uri
from social_network.facebook_scraper import create_url, fetch_html


def create_friends_url(user_id: str) -> str:
    return f"{home_uri}/{user_id}/{friends_path}"


def get_friends_as_soups(soup):
    return soup.find_all("table")[2:-3]


def get_next_friends_url(soup):
    el = soup.find(string=NEXT_FRIENDS_TEXT)
    if el is None:
        return None
    next_friends_url = el.find_parent().find_parent().get("href")
    return create_url(next_friends_url)


@dataclass
class Friend:
    id: str
    name: str
    num_common_friends: Optional[int]
    profile_picture_url: str = field(repr=False)

    @property
    def url(self):
        return create_url(self.id)


def create_friend_from_soup(soup):
    return Friend(
        id=get_id(soup),
        name=get_name(soup),
        profile_picture_url=get_profile_picture_url(soup),
        num_common_friends=get_num_common_friends(soup),
    )


def get_id(soup):
    url = soup.find("a").get("href")
    if url.startswith('/profile.php'):
        return url.split("&")[0].strip("/")
    return url.split("?")[0].strip("/")


def get_name(soup):
    return " ".join(soup.find("a").stripped_strings)


def get_profile_picture_url(soup):
    return soup.find("img").get("src")


def get_num_common_friends(soup):
    try:
        return int(next(soup.find("div").stripped_strings).split()[0])
    except StopIteration:
        return None


def fetch_friends(s, user_id: str):
    url = create_friends_url(user_id)
    soup = fetch_html(s, url)
    friends_soups = get_friends_as_soups(soup)
    friends = [create_friend_from_soup(p) for p in friends_soups]
    yield from friends

    time.sleep(2)
    next_url = get_next_friends_url(soup)
    if next_url is not None:
        yield from fetch_friends(s, next_url)
