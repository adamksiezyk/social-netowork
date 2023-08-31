import os

from social_network.facebook_friends import fetch_friends
from social_network.facebook_scraper import create_session

MY_PROFILE_URL = "https://mbasic.facebook.com/adam.ksiezyk.5/friends"


def test_scraper():
    email = os.environ["FB_EMAIL"]
    password = os.environ["FB_PASSWORD"]

    with create_session(email, password) as s:
        url = MY_PROFILE_URL
        friends = fetch_friends(s, url)
        for friend in friends:
            print(friend)


if __name__ == "__main__":
    test_scraper()
