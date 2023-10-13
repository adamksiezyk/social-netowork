import asyncio
import logging
import os

import httpx

from social_network.facebook_posts import Post, create_post_from_soup, fetch_feed, fetch_feed_generator
from social_network.facebook_scraper import create_session

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(fmt="%(asctime)s - %(levelname)s - %(name)8s - %(message)s", datefmt="%H:%M:%S")
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)

PAGE_ID = "pisorgpl"


async def test_facebook_posts_generator():
    logger.info("Starting scraping posts")

    email = os.environ["FB_EMAIL"]
    password = os.environ["FB_PASSWORD"]

    num_workers = 4
    queue = asyncio.Queue()
    output = []

    async with create_session(email, password) as s:
        posts = fetch_feed_generator(s, PAGE_ID)

        i = 0
        async for post in posts:
            await queue.put(post)
            if i == 10:
                break
            i += 1
        logger.info(f"Found {queue.qsize()} posts to fetch")
        logger.info(f"Creating {num_workers} workers")
        workers = [asyncio.create_task(_worker(s, queue, output)) for _ in range(num_workers)]
        await queue.join()

        logger.info("Finished processing tasks queue, cancelling workers")
        for w in workers:
            w.cancel()

        for p in output:
            print(p)


async def _worker(s: httpx.AsyncClient, queue: asyncio.Queue, output: list[Post]) -> None:
    logger.debug("Worker created, waiting for tasks")
    while True:
        try:
            post_soup = await queue.get()
            logger.debug("Task received, processing")
            post = await create_post_from_soup(post_soup, s)
            if post is None:
                logger.debug("Could not parse post")
            else:
                logger.debug("Post parsed successfuly")
                output.append(post)
            queue.task_done()
        except asyncio.CancelledError:
            logger.debug("Worker cancelled")
            return


if __name__ == "__main__":
    asyncio.run(test_facebook_posts_generator())
