#!/usr/bin/env python
# -*- coding: utf-8 -*-

from database import get_database

db = get_database()
videos = db.get_all_videos()

for v in videos:
    if v['video_id'] == 'SaKd1RqfM5A':
        print(f"video_id: {v['video_id']}")
        print(f"published_at: {v['published_at']}")
        print(f"title: {v['title']}")
        print(f"live_status: {v['live_status']}")
        print(f"content_type: {v['content_type']}")
