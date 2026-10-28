"""Generate the DEADLINE cinematic black-to-pink profile GIF from the existing banner.
The source is the current public GitHub user-attachment already referenced by README.md.
"""
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen
import math
import numpy as np
from PIL import Image, ImageFilter

SOURCE = "https://github.com/user-attachments/assets/5c36e1ce-54d3-4c6d-aaf8-97fd4cc3e000"
DEST = Path("assets/deadline-pink-animated.gif")
DEST.parent.mkdir(parents=True, exist_ok=True)

with urlopen(Request(SOURCE, headers={"User-Agent": "GitHub-Actions"}), timeout=45) as response:
    source_bytes = response.read()
original = Image.open(BytesIO(source_bytes)).convert("RGB")
width = 1000
height = round(original.height * width / original.width)
image = original.resize((width, height), Image.Resampling.LANCZOS)
pixels = np.asarray(image, dtype=np.float32)

# Detect bright, low-saturation lettering within the original title bounds.
mask_arr = np.zeros((height, width), dtype=np.float32)
luminance = pixels.mean(axis=2)
saturation = pixels.max(axis=2) - pixels.min(axis=2)
mask_raw = np.clip((luminance - 102) / 95, 0, 1) * np.clip((35 - saturation) / 20, 0, 1)
x0, x1 = round(200 * width / 1638), round(1435 * width / 1638)
y0, y1 = round(318 * height / 801), round(485 * height / 801)
mask_arr[y0:y1, x0:x1] = mask_raw[y0:y1, x0:x1]
mask = np.asarray(Image.fromarray((mask_arr * 255).astype("uint8"), "L").filter(ImageFilter.GaussianBlur(0.75)), dtype=np.float32) / 255
glow = np.asarray(Image.fromarray((mask * 255).astype("uint8"), "L").filter(ImageFilter.GaussianBlur(10)), dtype=np.float32) / 255
pink = np.array([255, 35, 166], dtype=np.float32)
highlight = 0.85 + 0.15 * np.linspace(0, 1, width, dtype=np.float32)[None, :, None]
frames = []

for frame_index in range(32):
    t = frame_index / 32

    def ease(value):
        value = max(0.0, min(1.0, value))
        return value * value * (3 - 2 * value)

    darkness = ease(min((t - 0.04) / 0.26, (1.03 - t) / 0.23))
    pinkness = ease(min((t - 0.30) / 0.30, (0.91 - t) / 0.21))
    pinkness = min(1.0, pinkness * (0.98 + 0.02 * math.cos(4 * math.pi * t)))
    frame = pixels * (1 - 0.69 * darkness)
    opacity = mask[..., None] * pinkness
    frame = frame * (1 - opacity * 0.88) + pink[None, None, :] * opacity * highlight
    frame += glow[..., None] * pink[None, None, :] * (0.33 * pinkness)
    quantized = Image.fromarray(np.clip(frame, 0, 255).astype("uint8"), "RGB")
    frames.append(quantized.quantize(colors=96, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE))

frames[0].save(DEST, save_all=True, append_images=frames[1:], duration=175, loop=0, optimize=True, disposal=2)
print(f"Created {DEST} ({DEST.stat().st_size:,} bytes), 32 frames, 5.6s loop.")
