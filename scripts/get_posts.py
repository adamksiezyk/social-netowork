#!/usr/bin/env python3
import asyncio
import datetime as dt
import logging
import os
from dataclasses import asdict
from functools import partial
from typing import Callable, Coroutine

import httpx
import yaml
from bs4 import PageElement
from pocketbase import PocketBase
from pocketbase.client import ClientResponseError, RecordService
from pocketbase.models.record import BaseModel

from social_network.facebook_posts import create_post_from_soup, fetch_feed_generator, get_timestamp
from social_network.facebook_scraper import create_session

TaskMessage = tuple[str, PageElement]

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(fmt="%(asctime)s - %(levelname)s - %(name)8s - %(message)s", datefmt="%H:%M:%S")
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)

CONFIG_PATH = './config.yml'
NUM_WORKERS = 4


def get_or_create_page(pages_collection: RecordService, page_name: str) -> BaseModel:
    try:
        return pages_collection.get_first_list_item(f'name = "{page_name}"')
    except ClientResponseError:
        logger.warning(f'Page {page_name!r} does not exist, creating new entry')
        return pages_collection.create({'name': page_name})


async def fetch_page_posts(s: httpx.AsyncClient,
                           queue: asyncio.Queue[TaskMessage],
                           page: BaseModel,
                           today: dt.date) -> None:
    logger.info(f"Starting scraping posts for {page.name!r} {today}")
    posts_soups = fetch_feed_generator(s, page.name)

    i = 0
    async for post_soup in posts_soups:
        if get_timestamp(post_soup).date() < today:
            break
        await queue.put((page.id, post_soup))
        i += 1
    logger.info(f"Found {i} posts to fetch")


async def fetch_post(s: httpx.AsyncClient, collection: RecordService, task_message: TaskMessage) -> None:
    page_id, post_soup = task_message
    res = await create_post_from_soup(s, post_soup)
    if res is None:
        logger.warning("Could not fetch post")
        return
    logger.debug("Uploading post")
    collection.create({'page': page_id, 'post': asdict(res)})


async def worker(input: asyncio.Queue[TaskMessage], f: Callable[[TaskMessage], Coroutine]) -> None:
    logger.debug("Worker created, waiting for tasks")
    while True:
        arg = await input.get()
        logger.debug("Task received, processing")
        try:
            # Process task
            await f(arg)
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

    pb_host = os.environ["PB_HOST"]
    pb_email = os.environ["PB_EMAIL"]
    pb_password = os.environ["PB_PASSWORD"]
    logger.info(f"Connecting to PocketBase {pb_host}")
    client = PocketBase(pb_host)
    client.admins.auth_with_password(pb_email, pb_password)
    pages_collection = client.collection('pages')
    posts_collection = client.collection('posts')

    logger.info(f"Creating {NUM_WORKERS} workers")
    queue = asyncio.Queue()

    fb_email = os.environ["FB_EMAIL"]
    fb_password = os.environ["FB_PASSWORD"]
    async with create_session(fb_email, fb_password) as s:
        f = partial(fetch_post, s, posts_collection)
        workers = [asyncio.create_task(worker(queue, f)) for _ in range(NUM_WORKERS)]

        for page_name in pages:
            page = get_or_create_page(pages_collection, page_name)
            await fetch_page_posts(s, queue, page, today)

    await queue.join()
    logger.info("Finished processing tasks queue, cancelling workers")
    for w in workers:
        w.cancel()

if __name__ == "__main__":
    asyncio.run(main())
