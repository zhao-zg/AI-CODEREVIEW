import os
from multiprocessing import Process

from redis import Redis
from rq import Queue

from biz.utils.log import logger
from biz.utils.default_config import get_env_with_default, get_env_int

queue_driver = get_env_with_default('QUEUE_DRIVER')

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
            redis_host = get_env_with_default('REDIS_HOST')
            redis_port = get_env_int('REDIS_PORT')
            logger.info(f'REDIS_HOST: {redis_host}，REDIS_PORT: {redis_port}')
            queues[queue_name] = Queue(queue_name, connection=Redis(redis_host, redis_port))

        queues[queue_name].enqueue(function, *args, **kwargs)
    else:
        process = Process(target=function, args=args, kwargs=kwargs)
        process.start()
