import os

from social_network.facebook_friends import fetch_friends
from social_network.facebook_scraper import create_session

USER_ID = "adam.ksiezyk.5"


def test_facebook_friends():
    email = os.environ["FB_EMAIL"]
    password = os.environ["FB_PASSWORD"]

    with create_session(email, password) as s:
        friends = fetch_friends(s, USER_ID)
        for friend in friends:
            print(friend)


if __name__ == "__main__":
    test_facebook_friends()
