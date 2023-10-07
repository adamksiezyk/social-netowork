from contextlib import contextmanager
from functools import partial
from typing import Iterable

import requests
from bs4 import BeautifulSoup

from .config import HOME_URI, USER_AGENT
from .utils import take_nth


# Scraper
def create_url(path):
    return f"{HOME_URI}/{path.strip('/')}"


def _get_login_data() -> tuple[str, dict, dict]:
    res = requests.get(HOME_URI)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, features="html.parser")
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
    headers = {'User-Agent': USER_AGENT}
    res = s.get(url, headers=headers)
    res.raise_for_status()
    return BeautifulSoup(res.text, features="html.parser")


def get_nth_child(n, soup):
    return take_nth(n, soup.children)


get_first_child = partial(get_nth_child, 0)
