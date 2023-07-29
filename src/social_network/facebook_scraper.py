import datetime as dt
import json
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import partial
from typing import Iterable

import requests
from bs4 import BeautifulSoup

from .config import NEXT_FEED_TEXT, POST_URL_TEXT, base_uri, home_url, proto, tz
from .utils import take_nth


# Scraper
def create_url(path):
    return f"{proto}://{base_uri}/{path.strip('/')}"


def _get_login_data() -> tuple[str, dict, dict]:
    res = requests.get(home_url)
    res.raise_for_status()
    soup = BeautifulSoup(res.text)
    form = soup.find(attrs={"id": "login_form"})
    action_url: str = form.get("action")
    inputs = form.find_all("input", attrs={"type": ["hidden", "submit"]})
    data = {el.get("name"): el.get("value") for el in inputs}
    cookies = res.cookies
    return action_url, data, cookies


@contextmanager
def create_session(email: str, password: str) -> Iterable[requests.Session]:
    login_url, login_data, login_cookies = _get_login_data()
    login_data["email"] = email
    login_data["pass"] = password
    s = requests.Session()
    res = s.post(
        create_url(login_url),
        data=login_data,
        cookies=login_cookies,
        allow_redirects=False,
    )
    if res.status_code != 302:
        raise RuntimeError("Error while logging in.")
    yield s
    s.close()


def fetch_html(s, url):
    res = s.get(url)
    res.raise_for_status()
    return BeautifulSoup(res.text)


def get_nth_child(n, soup):
    return take_nth(n, soup.children)


get_first_child = partial(get_nth_child, 0)
