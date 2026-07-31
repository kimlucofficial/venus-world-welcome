from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import os
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont, ImageOps

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_TEMPLATE = BASE_DIR / "assets" / "boarding_pass.png"

# Màu tím đậm khớp với phần label có sẵn trên boarding pass.
TEXT_COLOR = (104, 56, 154, 255)
TEXT_STROKE = TEXT_COLOR
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
    """Danh sách font theo thứ tự ưu tiên trên Railway và Windows."""
    env_name = "FONT_BOLD" if bold else "FONT_REGULAR"
    custom = os.getenv(env_name, "").strip()
    if custom:
        yield Path(custom)

    if bold:
        # Railway Dockerfile cài fonts-comfortaa tại đường dẫn này.
        yield Path("/usr/share/fonts/truetype/comfortaa/Comfortaa-Bold.ttf")
        yield Path("/usr/share/fonts/truetype/lato/Lato-Heavy.ttf")
        yield Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    else:
        yield Path("/usr/share/fonts/truetype/comfortaa/Comfortaa-Regular.ttf")
        yield Path("/usr/share/fonts/truetype/lato/Lato-Regular.ttf")
        yield Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")

    if os.name == "nt":
        font_dir = Path(os.getenv("WINDIR", r"C:\Windows")) / "Fonts"
        windows_names = (
            ("ARLRDBD.TTF", "arialbd.ttf", "segoeuib.ttf", "calibrib.ttf")
            if bold
            else ("arial.ttf", "segoeui.ttf", "calibri.ttf")
        )
        for name in windows_names:
            yield font_dir / name


def _load_font(size: int, *, bold: bool = True) -> ImageFont.FreeTypeFont:
    for path in _font_candidates(bold):
        if not path.is_file():
            continue
        try:
            return ImageFont.truetype(str(path), size=size)
        except OSError:
            continue

    # Không dùng ImageFont.load_default vì nó làm chữ cực nhỏ trên Railway.
    raise RuntimeError(
        "Không tìm thấy font TrueType. Trên Railway hãy deploy source có Dockerfile; "
        "trên Windows có thể đặt FONT_BOLD và FONT_REGULAR trong .env."
    )


def _measure(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    stroke_width: int,
) -> tuple[int, int, tuple[int, int, int, int]]:
    box = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    return box[2] - box[0], box[3] - box[1], box


def _ellipsize(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
    stroke_width: int,
) -> str:
    width, _, _ = _measure(draw, text, font, stroke_width)
    if width <= max_width:
        return text

    suffix = "…"
    low, high = 0, len(text)
    while low < high:
        mid = (low + high + 1) // 2
        candidate = text[:mid].rstrip() + suffix
        width, _, _ = _measure(draw, candidate, font, stroke_width)
        if width <= max_width:
            low = mid
        else:
            high = mid - 1
    return text[:low].rstrip() + suffix


def draw_field_text(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    *,
    max_size: int,
    min_size: int,
    padding_x: int = 10,
    padding_y: int = 5,
    bold: bool = True,
    align: str = "center",
    stroke_width: int = 1,
) -> None:
    """Vẽ chữ vừa ô, lớn nhất có thể và căn giữa chuẩn cả ngang lẫn dọc."""
    x1, y1, x2, y2 = box
    clean_text = " ".join(str(text).split()) or "-"
    max_width = max(1, x2 - x1 - padding_x * 2)
    max_height = max(1, y2 - y1 - padding_y * 2)

    selected_font: ImageFont.ImageFont | None = None
    selected_bounds: tuple[int, int, int, int] | None = None
    selected_text = clean_text

    for size in range(max_size, min_size - 1, -1):
        font = _load_font(size, bold=bold)
        width, height, bounds = _measure(draw, clean_text, font, stroke_width)
        if width <= max_width and height <= max_height:
            selected_font = font
            selected_bounds = bounds
            break

    if selected_font is None:
        selected_font = _load_font(min_size, bold=bold)
        selected_text = _ellipsize(
            draw,
            clean_text,
            selected_font,
            max_width,
            stroke_width,
        )
        _, _, selected_bounds = _measure(
            draw,
            selected_text,
            selected_font,
            stroke_width,
        )

    assert selected_bounds is not None
    left, top, right, bottom = selected_bounds
    text_width = right - left
    text_height = bottom - top

    if align == "left":
        x = x1 + padding_x - left
    elif align == "right":
        x = x2 - padding_x - text_width - left
    else:
        x = x1 + (x2 - x1 - text_width) / 2 - left

    y = y1 + (y2 - y1 - text_height) / 2 - top

    draw.text(
        (round(x), round(y)),
        selected_text,
        font=selected_font,
        fill=TEXT_COLOR,
        stroke_width=stroke_width,
        stroke_fill=TEXT_STROKE,
    )


def _paste_round_avatar(base: Image.Image, avatar_bytes: bytes | None) -> None:
    if not avatar_bytes:
        return

    try:
        avatar = Image.open(BytesIO(avatar_bytes)).convert("RGBA")
    except Exception:
        return

    avatar_size = 42
    border_width = 3
    full_size = avatar_size + border_width * 2

    avatar = ImageOps.fit(
        avatar,
        (avatar_size, avatar_size),
        method=Image.Resampling.LANCZOS,
    )

    mask = Image.new("L", (avatar_size, avatar_size), 0)
    ImageDraw.Draw(mask).ellipse(
        (0, 0, avatar_size - 1, avatar_size - 1),
        fill=255,
    )

    layer = Image.new("RGBA", (full_size, full_size), (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse(
        (0, 0, full_size - 1, full_size - 1),
        fill=AVATAR_BORDER,
    )
    layer.paste(avatar, (border_width, border_width), mask)
    base.alpha_composite(layer, (49, 307))


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
    if image.size != (1448, 1086):
        raise ValueError(
            "Ảnh boarding_pass.png phải đúng kích thước 1448x1086. "
            f"Kích thước hiện tại: {image.width}x{image.height}."
        )

    draw = ImageDraw.Draw(image)
    _paste_round_avatar(image, avatar_bytes)

    # Vé nhỏ bên trái — font vừa, đậm, cute và căn giữa.
    draw_field_text(draw, (100, 307, 343, 357), data.display_name, max_size=25, min_size=17)
    draw_field_text(draw, (83, 406, 343, 455), data.origin.upper(), max_size=25, min_size=17)
    draw_field_text(draw, (83, 505, 343, 554), data.destination.upper(), max_size=24, min_size=16)
    draw_field_text(draw, (83, 604, 343, 653), data.resolved_flight_code().upper(), max_size=25, min_size=17)
    draw_field_text(draw, (83, 703, 343, 752), data.date_text, max_size=24, min_size=17)
    draw_field_text(draw, (83, 802, 343, 851), data.time_text, max_size=24, min_size=17)

    # Khối thông tin chính.
    draw_field_text(draw, (466, 370, 760, 426), data.display_name, max_size=28, min_size=18)
    draw_field_text(draw, (837, 370, 1164, 426), data.username.lstrip("@"), max_size=27, min_size=17)
    draw_field_text(draw, (466, 497, 760, 550), str(data.user_id), max_size=20, min_size=15)
    draw_field_text(draw, (837, 497, 1164, 550), data.nationality.upper(), max_size=26, min_size=17)

    # Hàng ngày và giờ phía dưới.
    draw_field_text(draw, (466, 849, 728, 908), data.date_text, max_size=25, min_size=17)
    draw_field_text(draw, (837, 849, 1042, 908), data.time_text, max_size=25, min_size=17)

    output = BytesIO()
    image.convert("RGB").save(output, format="PNG", optimize=True)
    return output.getvalue()
