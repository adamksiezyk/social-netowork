#!/usr/bin/env python3
import asyncio
import datetime as dt
import logging
import os
from dataclasses import asdict
from typing import Callable, Coroutine, Optional

import yaml
from bs4 import BeautifulSoup
from pocketbase import PocketBase
from pocketbase.client import ClientResponseError, RecordService

from social_network.facebook_posts import create_post_from_soup, fetch_feed_generator, get_timestamp
from social_network.facebook_scraper import create_session

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(fmt="%(asctime)s - %(levelname)s - %(name)8s - %(message)s", datefmt="%H:%M:%S")
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)

CONFIG_PATH = './config.yml'


async def fetch_page_posts(page_id: str, today: dt.date):
    logger.info(f"Starting scraping posts for {page_id!r} {today}")

    fb_email = os.environ["FB_EMAIL"]
    fb_password = os.environ["FB_PASSWORD"]
    pb_host = os.environ["PB_HOST"]
    pb_email = os.environ["PB_EMAIL"]
    pb_password = os.environ["PB_PASSWORD"]

    num_workers = 4
    queue = asyncio.Queue()

    client = PocketBase(pb_host)
    client.admins.auth_with_password(pb_email, pb_password)
    pages_collection = client.collection('pages')
    posts_collection = client.collection('posts')

    try:
        page = pages_collection.get_first_list_item(f'name = "{page_id}"')
    except ClientResponseError:
        logger.warning(f'Page {page_id!r} does not exist, creating new entry')
        page = pages_collection.create({'name': page_id})

    async with create_session(fb_email, fb_password) as s:
        async def fetch_post(post_soup: BeautifulSoup) -> Optional[dict]:
            res = await create_post_from_soup(s, post_soup)
            if res is None:
                return None
            res_dict = asdict(res)
            return {'page': page.id, 'post': res_dict}
        posts_soups = fetch_feed_generator(s, page_id)

        async for post_soup in posts_soups:
            if get_timestamp(post_soup).date() < today:
                break
            await queue.put(post_soup)
        logger.info(f"Found {queue.qsize()} posts to fetch")
        logger.info(f"Creating {num_workers} workers")
        workers = [asyncio.create_task(worker(queue, posts_collection, fetch_post)) for _ in range(num_workers)]
        await queue.join()

        logger.info("Finished processing tasks queue, cancelling workers")
        for w in workers:
            w.cancel()


async def worker(input: asyncio.Queue[BeautifulSoup],
                 pb: RecordService,
                 f: Callable[[BeautifulSoup], Coroutine[None, None, Optional[dict]]]) -> None:
    logger.debug("Worker created, waiting for tasks")
    while True:
        arg = await input.get()
        logger.debug("Task received, processing")
        try:
            # Process task
            ret = await f(arg)
            if ret is None:
                logger.warning(f"Function {f.__name__} returned None")
            else:
                logger.debug(f"Task {f.__name__} completed successfuly")
                pb.create(ret)
        except asyncio.CancelledError:
            # Worker cancelled, exit
            logger.debug("Worker cancelled")
            return
        except Exception:
            # Task failed, await the next one
            logger.exception(f"An exception occured while processing {f.__name__}")
        finally:
            # Always free resources
            input.task_done()


async def main() -> None:
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)
    pages = config['pages']
    today = dt.date.today()
    for page_id in pages:
        await fetch_page_posts(page_id, today)

if __name__ == "__main__":
    asyncio.run(main())
