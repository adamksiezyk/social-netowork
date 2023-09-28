import datetime as dt

NEXT_FEED_TEXT = "Zobacz więcej relacji"
POST_URL_TEXT = "Pełne zdarzenie"
NEXT_FRIENDS_TEXT = "Zobacz więcej znajomych"

proto = "https"
base_url = "mbasic.facebook.com"
home_uri = f"{proto}://{base_url}"
friends_path = "friends"

tz = dt.timezone(dt.timedelta(hours=2))
