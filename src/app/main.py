import logging.config
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException

from .config import initialize_config
from .models import (
    ChannelRequestByName,
    ChannelRequestByID,
    ChannelMessages,
    ChannelIDRequest,
    ChannelIDResponse,
)
from .scraper import TelegramScraperQueue
from .utils import load_yaml, setup_cloud_logging

logger = logging.getLogger("telegram_scraper_service")
logging.config.dictConfig(load_yaml("config/logger.yaml"))

config_name = os.environ.get("CONFIG_NAME")

assert config_name, "CONFIG_NAME environment variable not set"
assert config_name.endswith(".yaml"), "CONFIG_NAME must end with .yaml"

config_path = Path(__file__).resolve().parents[2] / "config" / config_name

config = initialize_config(config_path)

if config.gcp.project_id:
    setup_cloud_logging()

app = FastAPI(
    title="Telegram Scraper Service",
    description="Microservice for scraping Telegram channels",
    version="1.0.0",
)

telegram_queue = TelegramScraperQueue(
    config.scraper.api_id, config.scraper.api_hash, config.scraper.session_name
)


@app.on_event("startup")
async def startup_event():
    """Start the Telegram client queue on startup"""
    await telegram_queue.start()


@app.post("/messages_by_id", response_model=ChannelMessages)
async def get_messages(request: ChannelRequestByID):
    """Get today's messages from a Telegram channel"""
    try:
        result = await telegram_queue.get_today_messages_by_id(request.channel_id)
        return result
    except Exception as e:
        logger.error(f"Error getting messages: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get messages: {str(e)}")


@app.post("/messages_by_name", response_model=ChannelMessages)
async def get_messages(request: ChannelRequestByName):
    """Get today's messages from a Telegram channel"""
    try:
        result = await telegram_queue.get_today_messages_by_name(request.channel_name)
        return result
    except Exception as e:
        logger.error(f"Error getting messages: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get messages: {str(e)}")


@app.post("/channel_id", response_model=ChannelIDResponse)
async def get_channel_id(request: ChannelIDRequest):
    """Get the channel ID for a given channel username or link"""
    try:
        channel_id, username = await telegram_queue.get_channel_id(request.channel)
        return ChannelIDResponse(channel_id=channel_id, username=username)
    except Exception as e:
        logger.error(f"Error getting channel ID: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get channel ID: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "telegram-scraper"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.app.main:app", host="0.0.0.0", port=8000, reload=True)
