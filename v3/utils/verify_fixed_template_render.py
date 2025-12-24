# -*- coding: utf-8 -*-

"""
修正後のテンプレートレンダリング確認スクリプト

対象動画が正しく拡張時刻（27時）でレンダリングされるか検証
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from database import get_database
from template_utils import calculate_extended_time_for_event, load_template_with_fallback, render_template
from jinja2 import Environment, FileSystemLoader
import logging
from pathlib import Path

# ロガー設定
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def main():
    print("=" * 80)
    print("🔍 修正後のテンプレートレンダリング検証")
    print("=" * 80)

    # DB から対象動画を取得
    db = get_database()
    videos = db.get_all_videos()

    target_video_id = "58S5Pzux9BI"
    target = None

    for v in videos:
        if v.get("video_id") == target_video_id:
            target = v
            break

    if not target:
        print(f"❌ 対象動画が見つかりません: {target_video_id}")
        return False

    print(f"\n📊 対象動画の現在の DB 値:")
    print(f"  video_id: {target['video_id']}")
    print(f"  title: {target['title']}")
    print(f"  published_at: {target['published_at']}")
    print(f"  classification_type: {target.get('classification_type')}")
    print(f"  live_status: {target.get('live_status')}")
    print(f"  channel_name: {target['channel_name']}")

    # ★ Step 1: 拡張時刻計算を実行
    print(f"\n📋 Step 1: calculate_extended_time_for_event を実行")
    try:
        calculate_extended_time_for_event(target)
        print(f"✅ 拡張時刻計算完了")
        print(f"  extended_hour: {target.get('extended_hour')}")
        print(f"  extended_display_date: {target.get('extended_display_date')}")
    except Exception as e:
        print(f"❌ 拡張時刻計算エラー: {e}")
        return False

    # ★ Step 2: テンプレートをロードしてレンダリング
    print(f"\n📋 Step 2: テンプレートをロード")
    try:
        # テンプレートディレクトリを設定
        template_dir = Path(__file__).parent / "templates"
        env = Environment(loader=FileSystemLoader(str(template_dir)))

        # yt_schedule_template.txt をロード
        template_path = "youtube/yt_schedule_template.txt"
        try:
            template_obj = env.get_template(template_path)
            print(f"✅ テンプレートロード成功: {template_path}")
        except Exception as e:
            print(f"❌ テンプレートロード失敗: {e}")
            return False

        # レンダリング
        print(f"\n📋 Step 3: テンプレートをレンダリング")
        rendered_text = render_template(template_obj, target, template_type="youtube_schedule")

        if rendered_text:
            print(f"✅ テンプレートレンダリング成功")
            print(f"\n📝 レンダリング結果:")
            print(f"━" * 80)
            print(rendered_text)
            print(f"━" * 80)

            # 27時 が含まれているか確認
            if "27時" in rendered_text:
                print(f"\n✅ 拡張時刻（27時）が表示されています！")
                return True
            else:
                print(f"\n⚠️ 拡張時刻（27時）が表示されていません")
                print(f"  レンダリング結果内容をご確認ください")
                # 拡張時刻が計算されたか確認
                if "extended_hour" in target and target["extended_hour"] == 27:
                    print(f"  ℹ️ extended_hour は計算されています (27) が、テンプレートで使用されていない可能性があります")
                return False
        else:
            print(f"❌ テンプレートレンダリング失敗")
            return False

    except Exception as e:
        print(f"❌ テンプレートレンダリング例外: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    print(f"\n{'='*80}")
    if success:
        print(f"✅ テンプレートレンダリング検証成功")
    else:
        print(f"❌ テンプレートレンダリング検証失敗")
    print(f"{'='*80}")
    sys.exit(0 if success else 1)
