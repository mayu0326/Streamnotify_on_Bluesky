#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""拡張時刻フィルターの動作確認"""

from jinja2 import Environment
from template_utils import _extended_time_display_filter, _extended_time_filter

# フィルター登録
env = Environment()
env.filters['extended_time_display'] = _extended_time_display_filter
env.filters['extended_time'] = _extended_time_filter

# テンプレート文字列
template_str = '''{{ "27:00" | extended_time_display }}
({{ "27:00" | extended_time }})  JST'''

# テンプレート実行
template_obj = env.from_string(template_str)
result = template_obj.render()

print('テンプレート実行結果:')
print(result)
print()

# ファイルベースのテンプレート読み込みも確認
print('ファイルベースのテンプレート読み込みテスト:')
from template_utils import load_template_with_fallback, render_template

template_obj = load_template_with_fallback("templates/youtube/yt_archive_template.txt")
if template_obj:
    context = {
        "channel_name": "テストチャンネル",
        "title": "テスト配信",
        "video_url": "https://www.youtube.com/watch?v=test",
        "published_at": "2025-12-21T12:00:00Z"
    }
    # render_template を使うことで、カスタム関数が注入される
    result = render_template(template_obj, context, "youtube_archive")
    print(result)
else:
    print("テンプレート読み込み失敗")
