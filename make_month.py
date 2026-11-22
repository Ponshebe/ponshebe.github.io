"""毎月20日に GitHub Actions から動く：翌月の営業日カレンダーを作り、Discord に送る。

決まり（オーナー確認済み）
- 毎週日曜は休み
- 月曜が祝日の週は、前日の日曜は営業し、月曜を休む
- 月曜以外の祝日は営業
- 臨時の休み.md の「休み／営業」で上書きする
- 背景は 背景/ の写真をファイル名の順に、1 か月に 1 枚ずつ使う（2027年1月 = 最初の 1 枚）
- できた画像/ に同じ月の画像があれば作らない（手で作って送った月を二重に送らないため）
"""
import calendar
import datetime as dt
import glob
import os
import re
import sys
from zoneinfo import ZoneInfo

import holidays
import requests

from render import render

JST = ZoneInfo("Asia/Tokyo")


def target_month():
    t = (os.environ.get("TARGET") or "").strip()
    if t:
        y, m = t.split("-")
        return int(y), int(m)
    today = dt.datetime.now(JST).date()
    y, m = today.year, today.month + 1
    if m == 13:
        y, m = y + 1, 1
    return y, m


def closed_days(y, m):
    jp = holidays.Japan(years=[y - 1, y, y + 1])
    closed = set()
    for d in range(1, calendar.monthrange(y, m)[1] + 1):
        date = dt.date(y, m, d)
        if date.weekday() == 6:  # 日曜
            if (date + dt.timedelta(days=1)) in jp:
                continue  # 翌日の月曜が祝日 → 日曜は営業
            closed.add(d)
        elif date.weekday() == 0 and date in jp:  # 祝日の月曜は休み
            closed.add(d)
    with open("臨時の休み.md", encoding="utf-8") as f:
        for line in f:
            mm = re.match(r"\|\s*(\d{4})-(\d{2})-(\d{2})\s*\|\s*(休み|営業)", line)
            if mm and int(mm[1]) == y and int(mm[2]) == m:
                d = int(mm[3])
                if mm[4] == "休み":
                    closed.add(d)
                else:
                    closed.discard(d)
    return sorted(closed)


def background(y, m):
    photos = sorted(p for p in glob.glob("背景/*") if p.lower().endswith((".jpg", ".jpeg", ".png")))
    if not photos:
        return None
    k = (y * 12 + m) - (2027 * 12 + 1)
    return photos[k % len(photos)]


def main():
    y, m = target_month()
    out = f"できた画像/{y:04d}-{m:02d}_ポンシェビ営業日.png"
    force = (os.environ.get("FORCE") or "").lower() == "true"
    if os.path.exists(out) and not force:
        print(f"{out} はすでにあるので、作り直しも送信もしません。")
        return 0
    closed = closed_days(y, m)
    bg = background(y, m)
    render(y, m, set(closed), bg, out)
    print("作成:", out, "休み:", closed, "背景:", bg)

    hook = os.environ.get("DISCORD_WEBHOOK")
    if not hook:
        print("DISCORD_WEBHOOK が無いので、送信はしません。")
        return 0
    days = "・".join(f"{d}日" for d in closed)
    msg = (f"【営業日カレンダー】{y}年{m}月分ができました（M・自動）。休み：{days}。"
           "臨時の休みや振替の変更があれば、Mのチャットで伝えてください。直して送り直します。")
    for attempt in range(2):
        with open(out, "rb") as f:
            r = requests.post(hook, data={"payload_json": '{"content": %s}' % __import__("json").dumps(msg, ensure_ascii=False)},
                              files={"files[0]": (os.path.basename(out), f, "image/png")}, timeout=60)
        if r.status_code in (200, 204):
            print("Discord に送信しました。")
            return 0
        print("送信に失敗:", r.status_code, r.text[:200])
    return 1


if __name__ == "__main__":
    sys.exit(main())
