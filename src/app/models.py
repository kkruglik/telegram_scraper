from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class Message(BaseModel):
    id: int
    text: str


class ChannelMeta(BaseModel):
    channel_id: str
    date: datetime


class ChannelMessages(BaseModel):
    meta: ChannelMeta
    messages: List[Message]


class ChannelRequestByID(BaseModel):
    channel_id: int


class ChannelRequestByName(BaseModel):
    channel_name: str


class ChannelIDRequest(BaseModel):
    channel: str


class ChannelIDResponse(BaseModel):
    channel_id: int
    username: Optional[str] = None
