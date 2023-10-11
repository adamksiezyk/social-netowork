import asyncio
import os

from social_network.facebook_posts import fetch_feed
from social_network.facebook_scraper import create_session

PAGE_ID = "pisorgpl"


async def test_facebook_posts():
    email = os.environ["FB_EMAIL"]
    password = os.environ["FB_PASSWORD"]

    async with create_session(email, password) as s:
        posts = fetch_feed(s, PAGE_ID)
        i = 0
        async for post in posts:
            print(i, post)
            if i == 10:
                break
            i += 1


if __name__ == "__main__":
    asyncio.run(test_facebook_posts())
