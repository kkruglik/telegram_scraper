import asyncio
import logging
from datetime import datetime, timedelta, timezone

from telethon import TelegramClient

logger = logging.getLogger("telegram_scraper_service")


class TelegramScraperQueue:
    def __init__(self, api_id: int, api_hash: str, session_name: str):
        self.client = TelegramClient(session_name, api_id, api_hash)
        self.queue = asyncio.Queue()
        self.running = False
        self.worker_task = None

    async def start(self):
        """Start the queue worker"""
        if self.running:
            return

        await self.client.start()
        self.running = True
        self.worker_task = asyncio.create_task(self._process_queue())
        logger.info("TelegramScraperQueue started")

    async def stop(self):
        """Stop the queue worker"""
        if not self.running:
            return

        self.running = False
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass

        await self.client.disconnect()
        logger.info("TelegramScraperQueue stopped")

    async def _process_queue(self):
        """Worker that processes queued tasks"""
        while self.running:
            if not self.client.is_connected():
                logger.warning("TelegramScraperQueue client not connected. Reconnecting...")
                try:
                    await asyncio.wait_for(self.client.connect(), timeout=10)
                    logger.info("Reconnection successful")
                except asyncio.TimeoutError:
                    logger.error("Reconnection timed out after 10 seconds")
                    await asyncio.sleep(5)
                    continue
                except Exception as e:
                    logger.error(f"Reconnection failed: {str(e)}")
                    await asyncio.sleep(5)
                    continue

            try:
                task_func, args, kwargs, future = await self.queue.get()
                try:
                    result = await task_func(self.client, *args, **kwargs)
                    future.set_result(result)
                except Exception as e:
                    logger.error(f"Error processing task: {str(e)}", exc_info=True)
                    future.set_exception(e)
                finally:
                    self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Unexpected error in queue processor: {str(e)}", exc_info=True)

    async def _enqueue_task(self, task_func, *args, **kwargs):
        """Add a task to the queue and wait for result"""
        if not self.running:
            await self.start()

        future = asyncio.Future()
        await self.queue.put((task_func, args, kwargs, future))
        return await future

    async def get_today_messages_by_id(self, channel_id: int):
        """Queue a task to get today's messages"""
        return await self._enqueue_task(self._get_today_messages, channel_id=channel_id)

    async def get_today_messages_by_name(self, channel_name: str):
        """Queue a task to get today's messages"""
        return await self._enqueue_task(self._get_today_messages, channel_name=channel_name)

    async def get_channel_id(self, channel: str):
        """Queue a task to get a channel ID"""
        return await self._enqueue_task(self._get_channel_id, channel)

    @staticmethod
    async def _get_today_messages(
        client: TelegramClient, channel_id: int = None, channel_name: str = None
    ):
        """Get messages from the last 24 hours"""
        channel_entity = channel_name or channel_id

        logger.info(f"Getting messages from last 24 hours for channel {channel_id}")

        # Make cutoff_time timezone-aware by using UTC
        cutoff_time = datetime.now(tz=timezone.utc) - timedelta(hours=24)

        messages = {
            "meta": {
                "channel_id": channel_entity,
                "date": datetime.now(tz=timezone.utc),
            },
            "messages": [],
        }

        try:
            async for message in client.iter_messages(
                entity=channel_entity,
                limit=100,
                offset_date=datetime.now(tz=timezone.utc),
            ):
                # Now both dates have timezone info and can be compared
                if message.date < cutoff_time:
                    break

                message_text = message.text
                if message_text is None or message_text == "":
                    continue

                messages["messages"].append({"id": message.id, "text": message_text})

            return messages
        except Exception as e:
            logger.error(f"Error fetching messages for channel {channel_id}: {str(e)}")
            raise

    @staticmethod
    async def _get_channel_id(client: TelegramClient, channel: str):
        """The actual implementation of getting a channel ID"""
        logger.info(f"Getting channel ID for channel {channel}")

        try:
            entity = await client.get_entity(channel)
            channel_id = entity.id
            username = entity.username

            # For supergroups/channels, we need to get the negative ID
            if hasattr(entity, "megagroup") or hasattr(entity, "broadcast"):
                # Convert to channel ID format with -100 prefix
                channel_id = int(f"-100{channel_id}")

            logger.info(f"Found channel ID: {channel_id}")
            return channel_id, username

        except Exception as e:
            logger.error(f"Error getting channel ID for {channel}: {str(e)}")
            raise
