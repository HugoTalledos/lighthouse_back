from __future__ import annotations
import io
from typing import Union, Tuple
from PIL import Image, ImageDraw, ImageFont

from ...domain.models import GeneratedImage, ImageBrief
from ...domain.ports import ImageComposerPort

_TARGET_W, _TARGET_H = 1200, 628
_BAR_H = 140
_BAR_ALPHA = 160
_CTA_COLOR = (24, 119, 242)  # #1877F2
_MARGIN = 24
_HEADLINE_SIZE = 48
_CTA_SIZE = 18
_FONT_PATHS = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]

_AnyFont = Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]


def _load_font(size: int) -> _AnyFont:
    for path in _FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def _center_crop(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w, new_h = int(src_w * scale), int(src_h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def _draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: _AnyFont,
    xy: Tuple[int, int],
    max_width: int,
    fill: Tuple[int, int, int, int],
) -> None:
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = "{} {}".format(current, word).strip()
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    x, y = xy
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        bbox = draw.textbbox((0, 0), line, font=font)
        y += (bbox[3] - bbox[1]) + 4


def _draw_cta_pill(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: _AnyFont,
    img_w: int,
    img_h: int,
    margin: int,
    color: Tuple[int, int, int],
) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    pad_x, pad_y = 16, 8
    pill_w = text_w + 2 * pad_x
    pill_h = text_h + 2 * pad_y
    x1 = img_w - margin - pill_w
    y1 = img_h - margin - pill_h
    x2 = img_w - margin
    y2 = img_h - margin
    r = pill_h // 2
    draw.rounded_rectangle([(x1, y1), (x2, y2)], radius=r, fill=(*color, 255))
    draw.text((x1 + pad_x, y1 + pad_y), text, font=font, fill=(255, 255, 255, 255))


class PillowImageComposer(ImageComposerPort):
    def compose(self, image: GeneratedImage, brief: ImageBrief) -> bytes:
        img = Image.open(io.BytesIO(image.image_bytes)).convert("RGBA")
        img = _center_crop(img, _TARGET_W, _TARGET_H)

        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        bar_y = _TARGET_H - _BAR_H
        draw.rectangle([(0, bar_y), (_TARGET_W, _TARGET_H)], fill=(0, 0, 0, _BAR_ALPHA))

        headline_font = _load_font(_HEADLINE_SIZE)
        _draw_wrapped_text(
            draw,
            brief.headline,
            headline_font,
            (_MARGIN, bar_y + 16),
            _TARGET_W - 2 * _MARGIN,
            (255, 255, 255, 255),
        )

        cta_font = _load_font(_CTA_SIZE)
        _draw_cta_pill(draw, brief.cta_text, cta_font, _TARGET_W, _TARGET_H, _MARGIN, _CTA_COLOR)

        result = Image.alpha_composite(img, overlay).convert("RGB")
        buf = io.BytesIO()
        result.save(buf, format="PNG")
        return buf.getvalue()
