"""make_bg.py - generates assets/bg.jpg (dark navy with teal/amber glow and a faint grid).
Run once:  python make_bg.py     (or replace assets/bg.jpg with any image you like)
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1920, 1080
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
img = np.zeros((H, W, 3), dtype=np.float32)
img[:] = (9, 14, 26)  # base navy


def glow(cx, cy, radius, color, strength):
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / radius
    a = np.clip(1 - d, 0, 1) ** 2 * strength
    for i in range(3):
        img[..., i] += a * color[i]


glow(300, 200, 700, (20, 184, 166), 0.9)    # teal, top left
glow(1650, 150, 600, (59, 90, 220), 0.7)    # indigo, top right
glow(1500, 950, 650, (245, 158, 11), 0.45)  # amber, bottom right
glow(250, 1000, 500, (14, 116, 144), 0.5)   # deep cyan, bottom left

base = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))

# faint document-like grid
grid = Image.new("RGBA", (W, H), (0, 0, 0, 0))
g = ImageDraw.Draw(grid)
for x in range(0, W, 64):
    g.line([(x, 0), (x, H)], fill=(255, 255, 255, 9))
for y in range(0, H, 64):
    g.line([(0, y), (W, y)], fill=(255, 255, 255, 9))

# tilted "resume sheets" floating on the right as decoration
sheets = Image.new("RGBA", (W, H), (0, 0, 0, 0))
for i, (cx, cy, ang, a) in enumerate([(1450, 520, -12, 34), (1620, 600, 8, 26), (1300, 700, 18, 18)]):
    sheet = Image.new("RGBA", (330, 430), (255, 255, 255, a))
    d = ImageDraw.Draw(sheet)
    d.rectangle([28, 30, 150, 46], fill=(45, 212, 191, a * 3))
    for row in range(9):
        d.rectangle([28, 80 + row * 30, 300 - (row % 3) * 50, 90 + row * 30], fill=(255, 255, 255, a * 2))
    sheet = sheet.rotate(ang, expand=True, resample=Image.BICUBIC)
    sheets.alpha_composite(sheet, (cx - sheet.width // 2, cy - sheet.height // 2))
sheets = sheets.filter(ImageFilter.GaussianBlur(1.2))

out = base.convert("RGBA")
out.alpha_composite(grid)
out.alpha_composite(sheets)
out.convert("RGB").save("assets/bg.jpg", quality=88)
print("saved assets/bg.jpg")
