#!/usr/bin/env python3
"""PWA の名簿に、動画の続き（きょうの行動・行方不明）を書き込む。
  python3 video-tools/ep3/pwa_patch.py video-tools/ep3/story/<名前>_pwa.json
入力：台本と一緒に Claude が書く <名前>_pwa.json
  { "day": 3,
    "roster": "../input/islanders.json",
    "missing": { "yuradayo0330": { "text": "森の奥へ探検に行ったまま、戻ってこない…" } },
    "today": [ { "id": "ibu131313", "spot": "cove", "anim": "work", "tool": "rod", "text": "入り江で釣りをしている" } ] }
出力：video-tools/out/islanders_day<day>.json（名簿まるごと）。Muse は投稿の瞬間にこれを Firebase の islanders に同期する。
同じ場所の人は、岸や森の縁に沿って 3.4 ずつ間をあけて並ぶ（並び順＝today に書いた順）。
"""
import json, os, sys

# 場所（島の座標）。dx, dz は向いている方向（cove/beach は海の方）
SPOTS = {
    'cove':       {'x': -8.5, 'z': 188.7, 'dx': -0.87, 'dz': 0.50},   # 入り江の岸
    'beach':      {'x': 249.3, 'z': 131.0, 'dx': 0.89, 'dz': 0.47},   # 漂着した東の砂浜
    'farm':       {'x': -7.0, 'z': 99.0, 'dx': 0.6, 'dz': 0.8},        # 平原の畑の予定地
    'forestEdge': {'x': -78.0, 'z': -24.0, 'dx': -0.98, 'dz': -0.2},   # 森の入口（森の方を向く）
    'plaza':      {'x': 0.0, 'z': 12.0, 'dx': 0.0, 'dz': -1.0},        # 中央の広場
}
GAP = 3.4

def main():
    src = os.path.abspath(sys.argv[1])
    P = json.load(open(src, encoding='utf-8'))
    day = int(P['day'])
    roster_path = os.path.join(os.path.dirname(src), P.get('roster', '../input/islanders.json'))
    R = json.load(open(roster_path, encoding='utf-8'))
    people = {p['id']: p for p in R['islanders']}
    count = {}
    errs = []
    for t in P.get('today', []):
        pid = t['id']
        if pid not in people: errs.append(f'名簿に無い: {pid}'); continue
        sp = SPOTS.get(t.get('spot'))
        if not sp: errs.append(f'場所が無い: {t.get("spot")}'); continue
        k = count.get(t['spot'], 0); count[t['spot']] = k + 1
        side = 0 if k == 0 else (1 if k % 2 else -1) * ((k + 1) // 2)
        tx, tz = -sp['dz'], sp['dx']  # 並ぶ向き（向いている方向に直角）
        people[pid]['today'] = {
            'day': day, 'text': t['text'], 'anim': t.get('anim', 'idle'),
            'x': round(sp['x'] + tx * side * GAP, 1), 'z': round(sp['z'] + tz * side * GAP, 1),
            'dx': sp['dx'], 'dz': sp['dz'], **({'tool': t['tool']} if t.get('tool') else {}),
        }
    for pid, m in (P.get('missing') or {}).items():
        if pid not in people: errs.append(f'名簿に無い: {pid}'); continue
        people[pid]['missing'] = {'day': day, **m}
        people[pid].pop('today', None)
    if errs:
        sys.exit('止めました：' + ' / '.join(errs))
    out_dir = os.path.join(os.path.dirname(__file__), '..', 'out')
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f'islanders_day{day}.json')
    R['updatedAt'] = R.get('updatedAt')
    json.dump(R, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'出力: {os.path.relpath(out)}（きょうの行動 {sum(1 for p in R["islanders"] if "today" in p)}人、行方不明 {len(P.get("missing") or {})}人）')

if __name__ == '__main__':
    main()
