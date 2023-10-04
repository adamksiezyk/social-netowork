import os

from social_network.facebook_posts import fetch_feed
from social_network.facebook_scraper import create_session

PAGE_ID = "PlatformaObywatelska"


def test_facebook_posts():
    email = os.environ["FB_EMAIL"]
    password = os.environ["FB_PASSWORD"]

    with create_session(email, password) as s:
        posts = fetch_feed(s, PAGE_ID)
        for i, post in enumerate(posts):
            print(i, post)
            if i == 9:
                break


if __name__ == "__main__":
    test_facebook_posts()
