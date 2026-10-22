import json
import time
import urllib.request
from datetime import datetime

from PIL import Image, ImageDraw

from luma.core.interface.serial import spi, noop
from luma.core.legacy import text
from luma.core.legacy.font import CP437_FONT, proportional
from luma.core.render import canvas
from luma.led_matrix.device import max7219

PADERBORN_LAT = 51.7189
PADERBORN_LON = 8.7575
WEATHER_REFRESH_S = 600  # re-check temperature every 10 minutes
SCROLL_STEP_DELAY = 0.04

serial = spi(port=0, device=0, gpio=noop())
device = max7219(serial, cascaded=2, block_orientation=-90,
                  blocks_arranged_in_reverse_order=True)
font = proportional(CP437_FONT)


def fetch_temperature():
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={PADERBORN_LAT}&longitude={PADERBORN_LON}&current_weather=true"
    )
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
        return data["current_weather"]["temperature"]
    except Exception as e:
        print(f"weather fetch failed: {e}")
        return None


def render_text_image(msg):
    width = sum(len(font[ord(c)]) for c in msg)
    img = Image.new("1", (width, device.height))
    draw = ImageDraw.Draw(img)
    text(draw, (0, 0), msg, fill="white", font=font)
    return img, width


def scroll_once(msg):
    img, width = render_text_image(msg)
    for x in range(device.width, -width - 1, -1):
        frame = Image.new("1", (device.width, device.height))
        frame.paste(img, (x, 0))
        with canvas(device) as draw:
            draw.bitmap((0, 0), frame, fill="white")
        time.sleep(SCROLL_STEP_DELAY)


cached_temp = fetch_temperature()
last_fetch = time.perf_counter()

print("starting time/temp looped scroll, Ctrl+C to stop")

while True:
    now = time.perf_counter()
    if now - last_fetch >= WEATHER_REFRESH_S:
        t = fetch_temperature()
        if t is not None:
            cached_temp = t
        last_fetch = now

    time_str = datetime.now().strftime("%H:%M")
    scroll_once(time_str + "   ")

    degree = chr(248)  # CP437 raw byte 248 = degree glyph (unicode '°' is a different byte in CP437)
    temp_str = f"{cached_temp:.1f}{degree}C" if cached_temp is not None else f"--{degree}C"
    scroll_once(temp_str + "   ")
