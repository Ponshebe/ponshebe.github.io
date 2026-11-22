"""ポンシェビ 営業日カレンダー画像を作る（試作）。

使い方:
  python3 render.py 2026 12 --closed 6,13,20,27 --bg 背景.jpg --out 202612.png

- 日曜・祝日は赤、土曜は青緑、平日は灰色（オーナーの Canva の配色に合わせる）
- 休みの日は赤い丸で囲む
- 祝日は日本の祝日を自動で判定する
"""
import argparse
import calendar
import datetime as dt

import holidays
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONT_LIGHT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Light.ttc"
FONT_DEMI = "/usr/share/fonts/opentype/noto/NotoSansCJK-DemiLight.ttc"

W = H = 1080
RED = (224, 80, 80)
TEAL = (47, 143, 143)
GRAY = (74, 74, 74)
WHITE = (255, 255, 255)
PANEL_BORDER = (155, 127, 176)

COL_X = [170, 292, 415, 538, 661, 784, 907]  # 日〜土の中心


def font(path, size):
    return ImageFont.truetype(path, size, index=0)  # index 0 = 日本語


def center_text(d, xy, text, f, fill):
    x, y = xy
    d.text((x, y), text, font=f, fill=fill, anchor="mm")


def make_background(bg_path):
    if bg_path:
        im = ImageOps.exif_transpose(Image.open(bg_path)).convert("RGB")
        s = min(im.size)
        l, t = (im.width - s) // 2, (im.height - s) // 2
        im = im.crop((l, t, l + s, t + s)).resize((W, H), Image.LANCZOS)
        return im.filter(ImageFilter.GaussianBlur(5))  # 見本のように、ややぼかす
    # 背景写真が無いときの仮の背景（店内の灯りのような暖色）
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    for y in range(H):
        r = int(150 + 60 * (1 - y / H))
        g = int(95 + 40 * (1 - y / H))
        b = int(60 + 20 * (1 - y / H))
        d.line([(0, y), (W, y)], fill=(r, g, b))
    return im


def render(year, month, closed, bg_path=None, out="out.png"):
    jp_hol = holidays.Japan(years=year)
    base = make_background(bg_path).convert("RGBA")

    # 半透明の白いパネル
    panel = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(panel)
    pd.rounded_rectangle((65, 268, 1015, 1025), radius=42,
                         fill=(255, 255, 255, 175), outline=PANEL_BORDER + (255,), width=3)
    img = Image.alpha_composite(base, panel)
    d = ImageDraw.Draw(img)

    # 見出し：月の数字・「月 ポンシェビ営業日」を左右中央に、年はその右端にそろえる
    f_num, f_tsuki, f_title = font(FONT, 195), font(FONT_DEMI, 56), font(FONT_DEMI, 62)
    num = str(month)
    num_w = d.textlength(num, font=f_num)
    title = "ポンシェビ営業日"
    total = num_w + 12 + 56 + 40 + 70 * (len(title) - 1) + d.textlength(title[-1], font=f_title)
    x = (W - total) / 2
    d.text((x, 215), num, font=f_num, fill=WHITE, anchor="ls")
    x += num_w + 12
    d.text((x, 190), "月", font=f_tsuki, fill=WHITE, anchor="ls")
    x += 56 + 40
    for ch in title:
        d.text((x, 190), ch, font=f_title, fill=WHITE, anchor="ls")
        x += 70
    right = (W - total) / 2 + total
    d.text((right, 255), str(year), font=font(FONT_DEMI, 42), fill=WHITE, anchor="rs")

    # 曜日
    f_head = font(FONT_DEMI, 32)
    for i, w in enumerate("日月火水木金土"):
        col = RED if i == 0 else TEAL if i == 6 else GRAY
        center_text(d, (COL_X[i], 338), w, f_head, col)

    # 日付
    cal = calendar.Calendar(firstweekday=6)  # 日曜はじまり
    weeks = cal.monthdayscalendar(year, month)
    step = 107 if len(weeks) <= 5 else 92
    f_day = font(FONT, 50)
    for r, week in enumerate(weeks):
        y = 430 + r * step
        for c, day in enumerate(week):
            if not day:
                continue
            date = dt.date(year, month, day)
            if c == 0 or date in jp_hol:
                col = RED
            elif c == 6:
                col = TEAL
            else:
                col = GRAY
            center_text(d, (COL_X[c], y), str(day), f_day, col)
            if day in closed:
                rad = 44
                d.ellipse((COL_X[c] - rad, y - rad, COL_X[c] + rad, y + rad), outline=RED, width=4)

    # 凡例
    lx, ly = 510, 958
    d.ellipse((lx - 30, ly - 30, lx + 30, ly + 30), outline=RED, width=4)
    d.text((lx + 42, ly), "は休みます", font=font(FONT_DEMI, 60), fill=GRAY, anchor="lm")

    img.convert("RGB").save(out, quality=92)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("year", type=int)
    ap.add_argument("month", type=int)
    ap.add_argument("--closed", default="")
    ap.add_argument("--bg")
    ap.add_argument("--out", default="out.png")
    a = ap.parse_args()
    closed = {int(x) for x in a.closed.split(",") if x}
    print(render(a.year, a.month, closed, a.bg, a.out))
