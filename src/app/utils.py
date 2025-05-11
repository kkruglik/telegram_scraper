from pathlib import Path

import google.cloud.logging
import yaml
import logging

logger = logging.getLogger("telegram_scraper_service")


def load_yaml(path: str | Path) -> dict:
    with open(path, "rt") as f:
        try:
            config = yaml.safe_load(f.read())
            return config
        except yaml.YAMLError as exc:
            raise exc


def setup_cloud_logging():
    """Setup Google Cloud Logging."""
    try:
        cloud_logging_client = google.cloud.logging.Client()
        cloud_logging_client.setup_logging(log_level=logging.INFO)

        logger.info("Google Cloud Logging has been configured successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to setup Google Cloud Logging: {e}", exc_info=True)
        return False
