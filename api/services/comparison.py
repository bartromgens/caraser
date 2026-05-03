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
        return ImageFont.load_default()


def _draw_label(draw: ImageDraw.ImageDraw, text: str, x: int, y: int, font) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    rx0 = x
    ry0 = y
    rx1 = x + tw + _LABEL_PADDING_X * 2
    ry1 = y + th + _LABEL_PADDING_Y * 2
    draw.rounded_rectangle([rx0, ry0, rx1, ry1], radius=_LABEL_RADIUS, fill=_LABEL_BG)
    draw.text(
        (rx0 + _LABEL_PADDING_X, ry0 + _LABEL_PADDING_Y - bbox[1]),
        text,
        font=font,
        fill=_LABEL_FG,
    )


def build_comparison_image(before_bytes: bytes, after_bytes: bytes) -> bytes:
    before = Image.open(BytesIO(before_bytes)).convert("RGB")
    after = Image.open(BytesIO(after_bytes)).convert("RGB")

    target_w = min(before.width, after.width)

    def resize_to_width(img: Image.Image) -> Image.Image:
        if img.width == target_w:
            return img
        ratio = target_w / img.width
        return img.resize((target_w, round(img.height * ratio)), Image.LANCZOS)

    before = resize_to_width(before)
    after = resize_to_width(after)

    total_h = before.height + _GAP + after.height
    canvas = Image.new("RGB", (target_w, total_h), (30, 30, 30))
    canvas.paste(before, (0, 0))
    canvas.paste(after, (0, before.height + _GAP))

    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = _load_font(_LABEL_FONT_SIZE)

    _draw_label(draw, "BEFORE", _LABEL_MARGIN, _LABEL_MARGIN, font)
    _draw_label(draw, "AFTER", _LABEL_MARGIN, before.height + _GAP + _LABEL_MARGIN, font)

    canvas = canvas.convert("RGBA")
    canvas = Image.alpha_composite(canvas, overlay)

    buf = BytesIO()
    canvas.convert("RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue()
