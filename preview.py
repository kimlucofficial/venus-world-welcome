from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from card_generator import WelcomeCardData, make_welcome_card

BASE_DIR = Path(__file__).resolve().parent

# Avatar giả để xem bố cục mà không cần kết nối Discord.
avatar = Image.new("RGBA", (256, 256), (235, 150, 235, 255))
draw = ImageDraw.Draw(avatar)
try:
    font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 120)
except OSError:
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            120,
        )
    except OSError:
        font = ImageFont.load_default()

draw.text((128, 128), "V", anchor="mm", font=font, fill="white")
avatar_path = BASE_DIR / "preview-avatar.png"
avatar.save(avatar_path)

with avatar_path.open("rb") as avatar_file:
    card_data = WelcomeCardData(
        display_name="VENUS WORLD",
        username="vteam2026",
        user_id="1532436928836927508",
        member_number=85,
        date_text="31/07/2026",
        time_text="00:38",
    )
    result = make_welcome_card(card_data, avatar_bytes=avatar_file.read())

preview_path = BASE_DIR / "preview.png"
preview_path.write_bytes(result)
print(f"Đã tạo preview: {preview_path}")
