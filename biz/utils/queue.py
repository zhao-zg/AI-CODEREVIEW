import os
from multiprocessing import Process

from redis import Redis
from rq import Queue

from biz.utils.log import logger

queue_driver = os.getenv('QUEUE_DRIVER', 'async')

if queue_driver == 'rq':
    queues = {}


def handle_queue(function: callable, *args, **kwargs):
    if queue_driver == 'rq':
        # For git-related events, url_slug is the 4th positional argument.
        # For other events like SVN, use a default queue.
        queue_name = 'default'
        if len(args) > 3 and isinstance(args[3], str):
            queue_name = args[3]

        if queue_name not in queues:
            logger.info(f'REDIS_HOST: {os.getenv("REDIS_HOST", "127.0.0.1")}，REDIS_PORT: {os.getenv("REDIS_PORT", 6379)}')
            queues[queue_name] = Queue(queue_name, connection=Redis(os.getenv('REDIS_HOST', '127.0.0.1'),
                                                                              os.getenv('REDIS_PORT', 6379)))

        queues[queue_name].enqueue(function, *args, **kwargs)
    else:
        process = Process(target=function, args=args, kwargs=kwargs)
        process.start()
