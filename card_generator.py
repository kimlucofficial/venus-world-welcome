from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import os
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont, ImageOps

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_TEMPLATE = BASE_DIR / "assets" / "boarding_pass.png"

TEXT_COLOR = (107, 58, 153, 255)
TEXT_STROKE = (255, 245, 255, 235)
AVATAR_BORDER = (218, 112, 210, 255)


@dataclass(slots=True)
class WelcomeCardData:
    display_name: str
    username: str
    user_id: int | str
    member_number: int
    date_text: str
    time_text: str
    nationality: str = "VIETNAM"
    origin: str = "DISCORD"
    destination: str = "VENUS WORLD"
    flight_code: str | None = None

    def resolved_flight_code(self) -> str:
        return self.flight_code or f"VW-{self.member_number:04d}"


def _font_candidates(bold: bool) -> Iterable[Path]:
    env_name = "FONT_BOLD" if bold else "FONT_REGULAR"
    if os.getenv(env_name):
        yield Path(os.environ[env_name])

    if os.name == "nt":
        windir = Path(os.getenv("WINDIR", r"C:\Windows")) / "Fonts"
        names = (
            ("arialbd.ttf", "segoeuib.ttf", "calibrib.ttf")
            if bold
            else ("arial.ttf", "segoeui.ttf", "calibri.ttf")
        )
        for name in names:
            yield windir / name
    else:
        names = (
            (
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/lato/Lato-Bold.ttf",
                "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf",
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            )
            if bold
            else (
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/lato/Lato-Regular.ttf",
                "/usr/share/fonts/opentype/inter/InterDisplay-Regular.otf",
                "/System/Library/Fonts/Supplemental/Arial.ttf",
            )
        )
        for name in names:
            yield Path(name)


def _load_font(size: int, *, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _font_candidates(bold):
        if path.is_file():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, stroke_width: int = 0) -> int:
    box = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    return box[2] - box[0]


def _ellipsize(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
    stroke_width: int = 0,
) -> str:
    if _text_width(draw, text, font, stroke_width) <= max_width:
        return text

    suffix = "…"
    low, high = 0, len(text)
    while low < high:
        mid = (low + high + 1) // 2
        candidate = text[:mid].rstrip() + suffix
        if _text_width(draw, candidate, font, stroke_width) <= max_width:
            low = mid
        else:
            high = mid - 1
    return text[:low].rstrip() + suffix


def draw_fitted_text(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    *,
    max_size: int,
    min_size: int = 15,
    bold: bool = True,
    fill: tuple[int, int, int, int] = TEXT_COLOR,
    stroke_width: int = 1,
    stroke_fill: tuple[int, int, int, int] = TEXT_STROKE,
    padding_x: int = 8,
    align: str = "left",
) -> None:
    x1, y1, x2, y2 = box
    available_width = max(1, x2 - x1 - padding_x * 2)
    available_height = max(1, y2 - y1)
    clean_text = " ".join(str(text).split()) or "-"

    selected_font: ImageFont.ImageFont | None = None
    for size in range(max_size, min_size - 1, -1):
        font = _load_font(size, bold=bold)
        bounds = draw.textbbox((0, 0), clean_text, font=font, stroke_width=stroke_width)
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        if width <= available_width and height <= available_height - 4:
            selected_font = font
            break

    if selected_font is None:
        selected_font = _load_font(min_size, bold=bold)
        clean_text = _ellipsize(draw, clean_text, selected_font, available_width, stroke_width)

    bounds = draw.textbbox((0, 0), clean_text, font=selected_font, stroke_width=stroke_width)
    text_width = bounds[2] - bounds[0]
    text_height = bounds[3] - bounds[1]

    if align == "center":
        x = x1 + (x2 - x1 - text_width) / 2
    elif align == "right":
        x = x2 - padding_x - text_width
    else:
        x = x1 + padding_x

    y = y1 + (available_height - text_height) / 2 - bounds[1]
    draw.text(
        (round(x), round(y)),
        clean_text,
        font=selected_font,
        fill=fill,
        stroke_width=stroke_width,
        stroke_fill=stroke_fill,
    )


def _paste_round_avatar(base: Image.Image, avatar_bytes: bytes | None) -> None:
    if not avatar_bytes:
        return

    try:
        avatar = Image.open(BytesIO(avatar_bytes)).convert("RGBA")
    except Exception:
        return

    size = 40
    avatar = ImageOps.fit(avatar, (size, size), method=Image.Resampling.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, size - 1, size - 1), fill=255)

    border_size = size + 6
    border = Image.new("RGBA", (border_size, border_size), (0, 0, 0, 0))
    border_draw = ImageDraw.Draw(border)
    border_draw.ellipse((0, 0, border_size - 1, border_size - 1), fill=AVATAR_BORDER)
    border.paste(avatar, (3, 3), mask)
    base.alpha_composite(border, (51, 308))


def make_welcome_card(
    data: WelcomeCardData,
    *,
    avatar_bytes: bytes | None = None,
    template_path: str | Path = DEFAULT_TEMPLATE,
) -> bytes:
    template = Path(template_path)
    if not template.is_file():
        raise FileNotFoundError(f"Không tìm thấy ảnh template: {template}")

    image = Image.open(template).convert("RGBA")
    draw = ImageDraw.Draw(image)

    _paste_round_avatar(image, avatar_bytes)

    # Vé nhỏ bên trái
    draw_fitted_text(draw, (96, 307, 342, 356), data.display_name, max_size=23, min_size=14)
    draw_fitted_text(draw, (47, 407, 342, 455), data.origin.upper(), max_size=23, min_size=15)
    draw_fitted_text(draw, (47, 506, 342, 554), data.destination.upper(), max_size=22, min_size=14)
    draw_fitted_text(draw, (84, 605, 342, 653), data.resolved_flight_code().upper(), max_size=23, min_size=15)
    draw_fitted_text(draw, (84, 704, 342, 752), data.date_text, max_size=22, min_size=15)
    draw_fitted_text(draw, (84, 803, 342, 851), data.time_text, max_size=22, min_size=15)

    # Thông tin chính
    draw_fitted_text(draw, (466, 370, 760, 426), data.display_name, max_size=25, min_size=15)
    draw_fitted_text(draw, (837, 370, 1162, 426), f"@{data.username.lstrip('@')}", max_size=24, min_size=14)
    draw_fitted_text(draw, (466, 497, 760, 550), str(data.user_id), max_size=22, min_size=14)
    draw_fitted_text(draw, (837, 497, 1162, 550), data.nationality.upper(), max_size=23, min_size=15)

    # Ngày và giờ ở phần dưới
    draw_fitted_text(draw, (466, 849, 727, 908), data.date_text, max_size=24, min_size=15)
    draw_fitted_text(draw, (837, 849, 1042, 908), data.time_text, max_size=24, min_size=15)

    output = BytesIO()
    image.convert("RGB").save(output, format="PNG", optimize=True)
    return output.getvalue()
