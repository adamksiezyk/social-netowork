from contextlib import asynccontextmanager
from functools import partial
from typing import AsyncIterator

import httpx
from bs4 import BeautifulSoup

from .config import HOME_URI, USER_AGENT
from .utils import take_nth


# Scraper
def create_url(path):
    return f"{HOME_URI}/{path.strip('/')}"


async def _get_login_data() -> tuple[str, dict, httpx.Cookies]:
    async with httpx.AsyncClient() as client:
        res = await client.get(HOME_URI)
    soup = BeautifulSoup(res.text, features="html.parser")
    form = soup.find(attrs={"id": "login_form"})
    action_url = form.get("action")
    inputs = form.find_all("input", attrs={"type": ["hidden", "submit"]})
    data = {el.get("name"): el.get("value") for el in inputs}
    cookies = res.cookies
    return action_url, data, cookies


@asynccontextmanager
async def create_session(email: str, password: str) -> AsyncIterator[httpx.AsyncClient]:
    login_url, login_data, login_cookies = await _get_login_data()
    login_data["email"] = email
    login_data["pass"] = password
    async with httpx.AsyncClient() as client:
        res = await client.post(
            create_url(login_url),
            data=login_data,
            cookies=login_cookies,
            follow_redirects=False,
        )
        if res.status_code != 302:
            raise RuntimeError("Error while logging in.")
        yield client


async def fetch_html(s: httpx.AsyncClient, url: str) -> BeautifulSoup:
    headers = {'User-Agent': USER_AGENT}
    res = await s.get(url, headers=headers)
    res.raise_for_status()
    return BeautifulSoup(res.text, features="html.parser")


def get_nth_child(n, soup):
    return take_nth(n, soup.children)


get_first_child = partial(get_nth_child, 0)
