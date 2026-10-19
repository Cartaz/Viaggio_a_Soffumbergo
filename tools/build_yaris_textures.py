"""Author small, original game textures. No Toyota photographs are embedded."""
from pathlib import Path
import math
import random

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "art/vehicles/yaris_2022/textures"


def font(size):
    for path in ("C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(22)
    im = Image.new("RGB", (256, 256))
    pixels = im.load()
    for y in range(256):
        for x in range(256):
            weave = 7 * math.sin(x * math.pi / 2) * math.cos(y * math.pi / 2)
            diamond = 5 if (x + y) % 32 < 2 or (x - y) % 32 < 2 else 0
            v = int(40 + weave + diamond + rng.uniform(-3, 3))
            pixels[x, y] = (v, v + 1, v + 2)
    im.save(OUT / "cloth.png")
    im = Image.new("RGB", (1024, 512), (9, 13, 19))
    d = ImageDraw.Draw(im)
    d.text((50, 25), "HOME", font=font(28), fill=(205, 215, 222))
    d.text((840, 25), "12:00", font=font(28), fill=(205, 215, 222))
    for x, title, value in [(42, "Audio", "DAB"), (365, "Telefono", "Bluetooth"), (688, "Energia", "HYBRID")]:
        d.rounded_rectangle((x, 100, x + 294, 438), radius=8, fill=(22, 34, 44), outline=(70, 90, 105), width=2)
        d.text((x + 24, 124), title, font=font(30), fill=(220, 224, 226))
        d.text((x + 24, 335), value, font=font(28), fill=(156, 202, 229))
    for i in range(5):
        d.rounded_rectangle((82 + i * 40, 220 - i * 13, 100 + i * 40, 285), radius=3, fill=(155, 198, 220))
    d.ellipse((460, 202, 546, 288), outline=(155, 198, 220), width=9)
    d.line((480, 250, 525, 250), fill=(155, 198, 220), width=6)
    d.rounded_rectangle((750, 210, 915, 288), radius=13, outline=(155, 198, 220), width=5)
    for i in range(4):
        d.rectangle((765 + i * 36, 223, 785 + i * 36, 275), fill=(115, 175, 197))
    im.save(OUT / "touch_7.png")
    im = Image.new("RGB", (1024, 384), (5, 8, 12))
    d = ImageDraw.Draw(im)
    for cx in [180, 844]:
        d.arc((cx - 145, 45, cx + 145, 335), 125, 415, fill=(82, 157, 215), width=8)
        for i in range(25):
            a = math.radians(135 + i * 11.25)
            r = 132
            d.line((cx + r * math.cos(a), 190 + r * math.sin(a), cx + (r - 10) * math.cos(a), 190 + (r - 10) * math.sin(a)), fill=(190, 202, 214), width=2)
    d.text((118, 150), "P", font=font(86), fill=(225, 237, 242))
    d.text((793, 150), "0", font=font(86), fill=(225, 237, 242))
    d.text((785, 250), "km/h", font=font(24), fill=(176, 192, 207))
    d.text((445, 75), "READY", font=font(30), fill=(96, 205, 149))
    d.text((445, 165), "12:00", font=font(38), fill=(225, 237, 242))
    d.text((414, 265), "Hybrid system", font=font(22), fill=(176, 192, 207))
    im.save(OUT / "cluster.png")
    im = Image.new("RGB", (512, 128), (8, 12, 17))
    d = ImageDraw.Draw(im)
    d.text((23, 20), "AUTO    21.0", font=font(54), fill=(201, 218, 228))
    d.text((355, 90), "A/C", font=font(24), fill=(174, 198, 211))
    im.save(OUT / "climate.png")
    im = Image.new("RGB", (1024, 220), (230, 232, 229))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 64, 220), fill=(25, 54, 136))
    d.rectangle((960, 0, 1024, 220), fill=(25, 54, 136))
    d.text((25, 135), "I", font=font(43), fill="white")
    d.text((180, 40), "YARIS", font=font(135), fill=(30, 34, 40))
    im.save(OUT / "plate.png")


if __name__ == "__main__":
    main()
