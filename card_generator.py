from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import os
from pathlib import Path
from typing import Iterable, Literal

from PIL import Image, ImageDraw, ImageFont, ImageOps

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_TEMPLATE = BASE_DIR / "assets" / "boarding_pass.png"

TEXT_COLOR = (105, 59, 151, 255)
AVATAR_BORDER = (218, 112, 210, 255)
FontWeight = Literal["medium", "semibold", "bold"]


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


def _font_candidates(weight: FontWeight) -> Iterable[Path]:
    """Font ổn định giữa Railway Linux và Windows VPS."""
    custom_name = {
        "medium": "FONT_MEDIUM",
        "semibold": "FONT_SEMIBOLD",
        "bold": "FONT_BOLD",
    }[weight]
    custom = os.getenv(custom_name, "").strip()
    if custom:
        yield Path(custom)

    linux_names = {
        "medium": (
            "/usr/share/fonts/truetype/lato/Lato-Medium.ttf",
            "/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Medium.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ),
        "semibold": (
            "/usr/share/fonts/truetype/lato/Lato-Semibold.ttf",
            "/usr/share/fonts/truetype/lato/Lato-Bold.ttf",
            "/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ),
        "bold": (
            "/usr/share/fonts/truetype/lato/Lato-Bold.ttf",
            "/usr/share/fonts/truetype/lato/Lato-Heavy.ttf",
            "/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ),
    }
    for name in linux_names[weight]:
        yield Path(name)

    if os.name == "nt":
        font_dir = Path(os.getenv("WINDIR", r"C:\Windows")) / "Fonts"
        windows_names = {
            "medium": ("segoeui.ttf", "calibri.ttf", "arial.ttf"),
            "semibold": ("segoeuib.ttf", "calibrib.ttf", "arialbd.ttf"),
            "bold": ("segoeuib.ttf", "calibrib.ttf", "arialbd.ttf"),
        }
        for name in windows_names[weight]:
            yield font_dir / name


def _load_font(size: int, *, weight: FontWeight = "semibold") -> ImageFont.FreeTypeFont:
    for path in _font_candidates(weight):
        if path.is_file():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                continue
    raise RuntimeError(
        "Không tìm thấy font TrueType. Khi host Railway hãy giữ Dockerfile trong source."
    )


def _measure(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
) -> tuple[int, int, tuple[int, int, int, int]]:
    bounds = draw.textbbox((0, 0), text, font=font)
    return bounds[2] - bounds[0], bounds[3] - bounds[1], bounds


def _ellipsize(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
) -> str:
    if _measure(draw, text, font)[0] <= max_width:
        return text

    suffix = "…"
    low, high = 0, len(text)
    while low < high:
        mid = (low + high + 1) // 2
        candidate = text[:mid].rstrip() + suffix
        if _measure(draw, candidate, font)[0] <= max_width:
            low = mid
        else:
            high = mid - 1
    return text[:low].rstrip() + suffix


def _render_text_crop(text: str, font: ImageFont.ImageFont) -> Image.Image:
    """
    Render chữ ra layer riêng rồi cắt đúng phần pixel thực sự nhìn thấy.

    Cách này không dựa vào ascender/descender/baseline của font, nên phần nét chữ
    được đặt đúng chính giữa ô theo cả chiều ngang lẫn chiều dọc.
    """
    probe = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    probe_draw = ImageDraw.Draw(probe)
    left, top, right, bottom = probe_draw.textbbox((0, 0), text, font=font)

    pad = 6
    width = max(1, right - left + pad * 2)
    height = max(1, bottom - top + pad * 2)
    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    layer_draw = ImageDraw.Draw(layer)
    layer_draw.text(
        (pad - left, pad - top),
        text,
        font=font,
        fill=TEXT_COLOR,
    )

    ink_box = layer.getchannel("A").getbbox()
    if ink_box is None:
        return layer
    return layer.crop(ink_box)


def draw_field_text(
    image: Image.Image,
    box: tuple[int, int, int, int],
    text: str,
    *,
    size: int,
    min_size: int,
    weight: FontWeight = "semibold",
    padding_x: int = 10,
    padding_y: int = 5,
) -> None:
    """
    Căn giữa thật sự theo pixel nhìn thấy của chữ.

    Chữ ngắn giữ nguyên kích thước thiết kế. Chỉ thu nhỏ nếu nội dung quá dài.
    """
    x1, y1, x2, y2 = box
    clean_text = " ".join(str(text).split()) or "-"
    max_width = max(1, x2 - x1 - padding_x * 2)
    max_height = max(1, y2 - y1 - padding_y * 2)
    measure_draw = ImageDraw.Draw(image)

    selected_font: ImageFont.ImageFont | None = None
    selected_text = clean_text

    for current_size in range(size, min_size - 1, -1):
        font = _load_font(current_size, weight=weight)
        width, height, _ = _measure(measure_draw, clean_text, font)
        if width <= max_width and height <= max_height:
            selected_font = font
            break

    if selected_font is None:
        selected_font = _load_font(min_size, weight=weight)
        selected_text = _ellipsize(measure_draw, clean_text, selected_font, max_width)

    text_layer = _render_text_crop(selected_text, selected_font)

    # Center theo đúng khung ô, dùng kích thước pixel thực tế của nét chữ.
    target_x = round(x1 + (x2 - x1 - text_layer.width) / 2)
    target_y = round(y1 + (y2 - y1 - text_layer.height) / 2)
    image.alpha_composite(text_layer, (target_x, target_y))


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

    _paste_round_avatar(image, avatar_bytes)

    # Vé nhỏ bên trái.
    draw_field_text(image, (100, 307, 343, 357), data.display_name, size=20, min_size=14)
    draw_field_text(image, (83, 406, 343, 455), data.origin.upper(), size=20, min_size=14)
    draw_field_text(image, (83, 505, 343, 554), data.destination.upper(), size=19, min_size=13)
    draw_field_text(image, (83, 604, 343, 653), data.resolved_flight_code().upper(), size=20, min_size=14)
    draw_field_text(image, (83, 703, 343, 752), data.date_text, size=19, min_size=14)
    draw_field_text(image, (83, 802, 343, 851), data.time_text, size=19, min_size=14)

    # Khối thông tin chính.
    draw_field_text(image, (466, 370, 760, 426), data.display_name, size=23, min_size=15)
    draw_field_text(image, (837, 370, 1164, 426), data.username.lstrip("@"), size=22, min_size=15)
    draw_field_text(
        image,
        (466, 497, 760, 550),
        str(data.user_id),
        size=17,
        min_size=13,
        weight="medium",
    )
    draw_field_text(image, (837, 497, 1164, 550), data.nationality.upper(), size=21, min_size=15)

    # Hàng ngày và giờ phía dưới.
    draw_field_text(image, (466, 849, 728, 908), data.date_text, size=20, min_size=14)
    draw_field_text(image, (837, 849, 1042, 908), data.time_text, size=20, min_size=14)

    output = BytesIO()
    image.convert("RGB").save(output, format="PNG", optimize=True)
    return output.getvalue()
