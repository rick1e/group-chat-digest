import datetime
import json
import logging
from dataclasses import dataclass, asdict

import redis
from redis import Redis
from telegram import Update


logger = logging.getLogger(__name__)

DEFAULT_MESSAGE_STORAGE = 100

redis_client_singleton = redis.Redis(host='localhost', port=6379, db=0)


def get_redis_client() -> Redis:
    """
    Gets the Redis client
    @return: the Redis client
    """
    return redis_client_singleton


@dataclass
class Message:
    """Stores the content of the messages"""
    message_id: int
    content: str
    owner_id: int
    owner_name: str

    # created_at: datetime.datetime

    @staticmethod
    def convert_update_to_owner(update: Update):
        return f"{update.message.from_user.first_name} {update.message.from_user.last_name}"


def store_message(redis_client: Redis,
                  chat_id: int,
                  message: Message) -> int:
    """
    @param redis_client: The Redis client singleton
    @param chat_id: The unique identifier for the chat session.
    @param message: The message to be stored.
    @return: the number of messages in the queue
    """

    serialized_message = _serialize_message(message)
    chat_key = str(chat_id)

    redis_client.lpush(chat_key, serialized_message)
    # Trim the list to only keep the latest 200 messages
    redis_client.ltrim(chat_key, 0, DEFAULT_MESSAGE_STORAGE - 1)

    # Return the current number of messages in the list
    return redis_client.llen(chat_key)


def _serialize_message(message: Message):
    """Converts Message object to JSON string"""
    return json.dumps(asdict(message))


def chat_exists(redis_client: Redis,
                chat_id: int) -> bool:
    """
    Returns True if the chat exists
    @param redis_client: The Redis client singleton
    @param chat_id: The unique identifier for the chat session.
    @return: True if chat exists
    """
    return redis_client.exists(str(chat_id))


def get_latest_n_messages(
        redis_client: Redis,
        chat_id: int,
        number_of_msgs: int = DEFAULT_MESSAGE_STORAGE
) -> list[Message]:
    """
    Gets the latest n messages. If no number
    is provided, it uses the default value
    @param redis_client:
    @param chat_id:
    @param number_of_msgs:
    @return:
    """
    serialized_messages = redis_client.lrange(str(chat_id), 0, number_of_msgs - 1)
    logger.info(f"Redis Messages: {serialized_messages}")

    messages_json = [json.loads(msg) for msg in serialized_messages]
    messages = [Message(**msg) for msg in messages_json]
    return messages