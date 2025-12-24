#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UTC → JST 変換の検証スクリプト
"""

from datetime import datetime, timedelta, timezone

# ユーザーが示唆したデータ
api_utc = "2025-12-28T18:00:00Z"  # API が返す UTC

# UTC → JST 変換
utc_time = datetime.fromisoformat(api_utc.replace('Z', '+00:00'))
jst_time = utc_time.astimezone(timezone(timedelta(hours=9))).replace(tzinfo=None)

print("=" * 70)
print("🔍 UTC → JST 変換の検証")
print("=" * 70)
print(f"\n📡 API から返される値（UTC）:")
print(f"   {api_utc}")

print(f"\n✅ JST に変換後:")
print(f"   {jst_time.isoformat()}")

# 拡張時刻のシミュレーション
hour = jst_time.hour
if hour < 12:
    extended_hour = 24 + hour
    date_str = (jst_time - timedelta(days=1)).strftime("%Y年%m月%d日")
else:
    extended_hour = hour
    date_str = jst_time.strftime("%Y年%m月%d日")

print(f"\n🔢 拡張時刻:")
print(f"   時刻: {hour}時 → 拡張表記: {extended_hour}時")
print(f"   日付: {date_str}")

if hour < 12:
    print(f"\n✅ 正しい: 早朝のため、前日の {extended_hour}時 表記を使用")
    print(f"   例: 2025年12月29日27時(2025年12月30日(火)午前3時)")
else:
    print(f"\n⚠️  注意: 午後のため、{extended_hour}時 表記を使用")

print("=" * 70)
