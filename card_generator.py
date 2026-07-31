from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import os
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont, ImageOps

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_TEMPLATE = BASE_DIR / "assets" / "boarding_pass.png"

# Màu chữ tím đậm của mẫu vé.
TEXT_COLOR = (99, 54, 151, 255)
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
    """Tìm font hoạt động được trên Windows VPS và Railway Linux."""
    env_name = "FONT_BOLD" if bold else "FONT_REGULAR"
    custom_font = os.getenv(env_name, "").strip()
    if custom_font:
        yield Path(custom_font)

    if os.name == "nt":
        font_dir = Path(os.getenv("WINDIR", r"C:\Windows")) / "Fonts"
        names = (
            ("arialbd.ttf", "segoeuib.ttf", "calibrib.ttf")
            if bold
            else ("arial.ttf", "segoeui.ttf", "calibri.ttf")
        )
        for name in names:
            yield font_dir / name
    else:
        names = (
            (
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
                "/usr/share/fonts/truetype/lato/Lato-Bold.ttf",
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            )
            if bold
            else (
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
                "/usr/share/fonts/truetype/lato/Lato-Regular.ttf",
                "/System/Library/Fonts/Supplemental/Arial.ttf",
            )
        )
        for name in names:
            yield Path(name)


def _load_font(size: int, *, bold: bool = True) -> ImageFont.ImageFont:
    for path in _font_candidates(bold):
        if not path.is_file():
            continue
        try:
            return ImageFont.truetype(str(path), size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _measure_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def _ellipsize(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
) -> str:
    if _measure_width(draw, text, font) <= max_width:
        return text

    suffix = "…"
    low, high = 0, len(text)
    while low < high:
        mid = (low + high + 1) // 2
        candidate = text[:mid].rstrip() + suffix
        if _measure_width(draw, candidate, font) <= max_width:
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
    min_size: int = 14,
    padding_x: int = 8,
    bold: bool = True,
    align: str = "left",
) -> None:
    """
    Ghi chữ chính giữa theo chiều dọc của ô.

    Dùng anchor='lm/mm/rm' để tránh lỗi chữ bị dồn lên mép trên khi chạy
    bằng font khác nhau giữa Windows và Railway Linux.
    """
    x1, y1, x2, y2 = box
    clean_text = " ".join(str(text).split()) or "-"
    max_width = max(1, x2 - x1 - padding_x * 2)

    selected_font: ImageFont.ImageFont | None = None
    for size in range(max_size, min_size - 1, -1):
        font = _load_font(size, bold=bold)
        if _measure_width(draw, clean_text, font) <= max_width:
            selected_font = font
            break

    if selected_font is None:
        selected_font = _load_font(min_size, bold=bold)
        clean_text = _ellipsize(draw, clean_text, selected_font, max_width)

    center_y = (y1 + y2) / 2 + 1
    if align == "center":
        x = (x1 + x2) / 2
        anchor = "mm"
    elif align == "right":
        x = x2 - padding_x
        anchor = "rm"
    else:
        x = x1 + padding_x
        anchor = "lm"

    draw.text(
        (round(x), round(center_y)),
        clean_text,
        font=selected_font,
        fill=TEXT_COLOR,
        anchor=anchor,
    )


def _paste_round_avatar(base: Image.Image, avatar_bytes: bytes | None) -> None:
    if not avatar_bytes:
        return

    try:
        avatar = Image.open(BytesIO(avatar_bytes)).convert("RGBA")
    except Exception:
        return

    avatar_size = 40
    border_width = 3
    full_size = avatar_size + border_width * 2

    avatar = ImageOps.fit(
        avatar,
        (avatar_size, avatar_size),
        method=Image.Resampling.LANCZOS,
    )

    avatar_mask = Image.new("L", (avatar_size, avatar_size), 0)
    ImageDraw.Draw(avatar_mask).ellipse(
        (0, 0, avatar_size - 1, avatar_size - 1),
        fill=255,
    )

    avatar_layer = Image.new("RGBA", (full_size, full_size), (0, 0, 0, 0))
    ImageDraw.Draw(avatar_layer).ellipse(
        (0, 0, full_size - 1, full_size - 1),
        fill=AVATAR_BORDER,
    )
    avatar_layer.paste(avatar, (border_width, border_width), avatar_mask)

    # Chính giữa ô PASSENGER bên trái.
    base.alpha_composite(avatar_layer, (50, 309))


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
            "Ảnh boarding_pass.png phải đúng kích thước 1448x1086 để thông tin không bị lệch. "
            f"Kích thước hiện tại: {image.width}x{image.height}."
        )

    draw = ImageDraw.Draw(image)
    _paste_round_avatar(image, avatar_bytes)

    # ------------------------------------------------------------------
    # Vé nhỏ bên trái: chỉ ghi vào phần trống bên dưới nhãn của từng ô.
    # ------------------------------------------------------------------
    draw_field_text(draw, (96, 307, 343, 356), data.display_name, max_size=22, min_size=14)
    draw_field_text(draw, (83, 406, 343, 455), data.origin.upper(), max_size=22, min_size=14)
    draw_field_text(draw, (83, 505, 343, 554), data.destination.upper(), max_size=21, min_size=13)
    draw_field_text(draw, (83, 604, 343, 653), data.resolved_flight_code().upper(), max_size=22, min_size=14)
    draw_field_text(draw, (83, 703, 343, 752), data.date_text, max_size=21, min_size=14)
    draw_field_text(draw, (83, 802, 343, 851), data.time_text, max_size=21, min_size=14)

    # ------------------------------------------------------------------
    # Khối thông tin chính.
    # Template đã có icon @ nên username không cần thêm dấu @ lần nữa.
    # ------------------------------------------------------------------
    draw_field_text(draw, (466, 370, 760, 425), data.display_name, max_size=24, min_size=14)
    draw_field_text(draw, (837, 370, 1164, 425), data.username.lstrip("@"), max_size=23, min_size=14)
    draw_field_text(draw, (466, 497, 760, 550), str(data.user_id), max_size=21, min_size=13)
    draw_field_text(draw, (837, 497, 1164, 550), data.nationality.upper(), max_size=22, min_size=14)

    # Ngày và giờ ở hàng dưới cùng.
    draw_field_text(draw, (466, 849, 728, 908), data.date_text, max_size=22, min_size=14)
    draw_field_text(draw, (837, 849, 1042, 908), data.time_text, max_size=22, min_size=14)

    output = BytesIO()
    image.convert("RGB").save(output, format="PNG", optimize=True)
    return output.getvalue()
