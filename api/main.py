"""
api/main.py
FastAPI application exposing analytical endpoints over the
medical Telegram data warehouse.
"""

import re
from collections import Counter
from typing import List

from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.database import get_db
from api.schemas import (
    TopProduct,
    ChannelActivity,
    MessageSearchResult,
    VisualContentStats,
)

app = FastAPI(
    title="Medical Telegram Analytics API",
    description="Analytical API over Ethiopian medical Telegram channel data.",
    version="1.0.0",
)

# Common Ethiopian medical/pharma terms to detect for "top products"
STOPWORDS = {
    "the", "and", "for", "with", "this", "that", "from", "are", "you",
    "your", "have", "has", "will", "can", "all", "our", "more", "now",
    "new", "use", "ለ", "በ", "የ", "እና", "ነው", "ላይ",
}


@app.get("/", tags=["Root"])
def root():
    """API health check / welcome message."""
    return {
        "message": "Medical Telegram Analytics API",
        "docs": "/docs",
        "endpoints": [
            "/api/reports/top-products",
            "/api/channels/{channel_name}/activity",
            "/api/search/messages",
            "/api/reports/visual-content",
        ],
    }


@app.get(
    "/api/reports/top-products",
    response_model=List[TopProduct],
    tags=["Reports"],
    summary="Top mentioned products/terms across all channels",
)
def get_top_products(
    limit: int = Query(10, ge=1, le=100, description="Number of top terms to return"),
    db: Session = Depends(get_db),
):
    """
    Returns the most frequently mentioned terms across all message text.
    Uses simple word-frequency analysis, filtering common stopwords.
    """
    rows = db.execute(text("SELECT message_text FROM marts_marts.fct_messages")).fetchall()

    counter = Counter()
    for (text_content,) in rows:
        if not text_content:
            continue
        words = re.findall(r"\b[a-zA-Z]{4,}\b", text_content.lower())
        for w in words:
            if w not in STOPWORDS:
                counter[w] += 1

    top = counter.most_common(limit)
    return [TopProduct(term=term, mention_count=count) for term, count in top]


@app.get(
    "/api/channels/{channel_name}/activity",
    response_model=ChannelActivity,
    tags=["Channels"],
    summary="Posting activity and stats for a specific channel",
)
def get_channel_activity(channel_name: str, db: Session = Depends(get_db)):
    """Returns aggregate posting activity and engagement stats for one channel."""
    row = db.execute(
        text("""
            SELECT channel_name, channel_type, total_posts, avg_views,
                   first_post_date, last_post_date, total_images,
                   pct_posts_with_image
            FROM marts_marts.dim_channels
            WHERE LOWER(channel_name) = LOWER(:channel_name)
        """),
        {"channel_name": channel_name},
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail=f"Channel '{channel_name}' not found")

    return ChannelActivity(
        channel_name=row.channel_name,
        channel_type=row.channel_type,
        total_posts=row.total_posts,
        avg_views=float(row.avg_views or 0),
        first_post_date=row.first_post_date,
        last_post_date=row.last_post_date,
        total_images=row.total_images,
        pct_posts_with_image=float(row.pct_posts_with_image or 0),
    )


@app.get(
    "/api/search/messages",
    response_model=List[MessageSearchResult],
    tags=["Search"],
    summary="Search messages by keyword",
)
def search_messages(
    query: str = Query(..., min_length=2, description="Keyword to search for"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Full-text search across message content for a given keyword."""
    rows = db.execute(
        text("""
            SELECT f.message_id, c.channel_name, f.message_text,
                   f.view_count, f.forward_count, f.message_date, f.has_image
            FROM marts_marts.fct_messages f
            LEFT JOIN marts_marts.dim_channels c ON f.channel_key = c.channel_key
            WHERE f.message_text ILIKE :pattern
            ORDER BY f.view_count DESC
            LIMIT :limit
        """),
        {"pattern": f"%{query}%", "limit": limit},
    ).fetchall()

    return [
        MessageSearchResult(
            message_id=r.message_id,
            channel_name=r.channel_name,
            message_text=r.message_text,
            view_count=r.view_count,
            forward_count=r.forward_count,
            message_date=r.message_date,
            has_image=r.has_image,
        )
        for r in rows
    ]


@app.get(
    "/api/reports/visual-content",
    response_model=List[VisualContentStats],
    tags=["Reports"],
    summary="Image usage statistics across channels",
)
def get_visual_content_stats(db: Session = Depends(get_db)):
    """Returns per-channel statistics on image usage and engagement comparison."""
    rows = db.execute(
        text("""
            SELECT
                c.channel_name,
                COUNT(*) AS total_posts,
                SUM(CASE WHEN f.has_image THEN 1 ELSE 0 END) AS posts_with_images,
                ROUND(
                    100.0 * SUM(CASE WHEN f.has_image THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0),
                    2
                ) AS pct_with_images,
                ROUND(AVG(CASE WHEN f.has_image THEN f.view_count END), 0) AS avg_views_with_image,
                ROUND(AVG(CASE WHEN NOT f.has_image THEN f.view_count END), 0) AS avg_views_without_image
            FROM marts_marts.fct_messages f
            LEFT JOIN marts_marts.dim_channels c ON f.channel_key = c.channel_key
            GROUP BY c.channel_name
            ORDER BY pct_with_images DESC
        """)
    ).fetchall()

    return [
        VisualContentStats(
            channel_name=r.channel_name or "Unknown",
            total_posts=r.total_posts,
            posts_with_images=r.posts_with_images,
            pct_with_images=float(r.pct_with_images or 0),
            avg_views_with_image=float(r.avg_views_with_image) if r.avg_views_with_image else None,
            avg_views_without_image=float(r.avg_views_without_image) if r.avg_views_without_image else None,
        )
        for r in rows
    ]
