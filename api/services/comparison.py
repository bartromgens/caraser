from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
_LABEL_FONT_SIZE = 22
_LABEL_PADDING_X = 14
_LABEL_PADDING_Y = 8
_LABEL_MARGIN = 14
_LABEL_RADIUS = 6
_GAP = 6
_LABEL_BG = (0, 0, 0, 140)
_LABEL_FG = (255, 255, 255, 255)


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(_FONT_PATH, size)
    except OSError:
        return ImageFont.load_default(size=size)


def _draw_label(
    draw: ImageDraw.ImageDraw, text: str, y: int, font, panel_w: int
) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    label_w = tw + _LABEL_PADDING_X * 2
    rx0 = (panel_w - label_w) // 2
    ry0 = y
    rx1 = rx0 + label_w
    ry1 = y + th + _LABEL_PADDING_Y * 2
    draw.rounded_rectangle([rx0, ry0, rx1, ry1], radius=_LABEL_RADIUS, fill=_LABEL_BG)
    draw.text(
        (rx0 + _LABEL_PADDING_X, ry0 + _LABEL_PADDING_Y - bbox[1]),
        text,
        font=font,
        fill=_LABEL_FG,
    )


def _crop_to_panel(img: Image.Image, panel_w: int, panel_h: int) -> Image.Image:
    """Centre-crop img to panel_w × panel_h, scaling down first if needed."""
    # Scale so the image is at least panel_w wide and panel_h tall (cover fit).
    scale = max(panel_w / img.width, panel_h / img.height)
    if scale < 1.0:
        img = img.resize(
            (round(img.width * scale), round(img.height * scale)), Image.LANCZOS
        )
    left = (img.width - panel_w) // 2
    top = (img.height - panel_h) // 2
    return img.crop((left, top, left + panel_w, top + panel_h))


def build_comparison_image(before_bytes: bytes, after_bytes: bytes) -> bytes:
    before = Image.open(BytesIO(before_bytes)).convert("RGB")
    after = Image.open(BytesIO(after_bytes)).convert("RGB")

    # Choose canvas width = narrowest image width (no upscaling).
    canvas_w = min(before.width, after.width)
    panel_w = canvas_w
    # Natural panel height for each image at canvas_w width (no upscaling).
    before_natural_h = round(before.height / before.width * panel_w)
    after_natural_h = round(after.height / after.width * panel_w)
    # Cap at 4:5 max; use the smaller of the two naturals to avoid black bars.
    max_panel_h = canvas_w * 5 // 8  # half of 4:5 canvas height
    panel_h = min(before_natural_h, after_natural_h, max_panel_h)

    before = _crop_to_panel(before, panel_w, panel_h)
    after = _crop_to_panel(after, panel_w, panel_h)

    total_h = before.height + _GAP + after.height
    canvas = Image.new("RGB", (canvas_w, total_h), (30, 30, 30))
    canvas.paste(before, (0, 0))
    canvas.paste(after, (0, before.height + _GAP))

    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = _load_font(_LABEL_FONT_SIZE)

    _draw_label(draw, "BEFORE", _LABEL_MARGIN, font, canvas_w)
    _draw_label(draw, "AFTER", before.height + _GAP + _LABEL_MARGIN, font, canvas_w)

    canvas = canvas.convert("RGBA")
    canvas = Image.alpha_composite(canvas, overlay)

    buf = BytesIO()
    canvas.convert("RGB").save(buf, format="JPEG", quality=85)
    return buf.getvalue()
