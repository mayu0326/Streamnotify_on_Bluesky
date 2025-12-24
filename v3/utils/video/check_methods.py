import sys
sys.path.insert(0, '.')

try:
    # ファイルを AST で解析
    import ast

    with open('gui_v3.py', 'r', encoding='utf-8-sig') as f:
        tree = ast.parse(f.read())

    # StreamNotifyGUI クラスを探す
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'StreamNotifyGUI':
            # クラスの直接の子メソッドのみ取得
            methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]

            print('=' * 70)
            print('StreamNotifyGUI クラスのメソッド一覧')
            print('=' * 70)
            print('総数:', len(methods))
            print()

            # 最後の10個を表示
            for method in methods[-10:]:
                print('  ✅', method)

            print()
            if 'add_video_dialog' in methods:
                print('✅ add_video_dialog が存在します')
            else:
                print('❌ add_video_dialog が見つかりません')

            if '_add_video_from_id' in methods:
                print('✅ _add_video_from_id が存在します')
            else:
                print('❌ _add_video_from_id が見つかりません')

            break

except Exception as e:
    print('エラー:', e)
    import traceback
    traceback.print_exc()
