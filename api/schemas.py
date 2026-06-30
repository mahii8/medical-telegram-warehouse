"""
api/schemas.py
Pydantic models for request/response validation.
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class TopProduct(BaseModel):
    term: str
    mention_count: int


class ChannelActivity(BaseModel):
    channel_name: str
    channel_type: str
    total_posts: int
    avg_views: float
    first_post_date: Optional[datetime]
    last_post_date: Optional[datetime]
    total_images: int
    pct_posts_with_image: float


class MessageSearchResult(BaseModel):
    message_id: int
    channel_name: Optional[str] = None
    message_text: str
    view_count: int
    forward_count: int
    message_date: datetime
    has_image: bool

    class Config:
        from_attributes = True


class VisualContentStats(BaseModel):
    channel_name: str
    total_posts: int
    posts_with_images: int
    pct_with_images: float
    avg_views_with_image: Optional[float]
    avg_views_without_image: Optional[float]
