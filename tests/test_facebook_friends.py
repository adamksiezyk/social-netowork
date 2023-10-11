import asyncio
import os

from social_network.facebook_friends import create_friends_url, fetch_friends
from social_network.facebook_scraper import create_session

USER_ID = "adam.ksiezyk.5"


async def test_facebook_friends():
    email = os.environ["FB_EMAIL"]
    password = os.environ["FB_PASSWORD"]
    uri = create_friends_url(USER_ID)

    async with create_session(email, password) as s:
        friends = fetch_friends(s, uri)
        async for friend in friends:
            print(friend)


if __name__ == "__main__":
    asyncio.run(test_facebook_friends())
