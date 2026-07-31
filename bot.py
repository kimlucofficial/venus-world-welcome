from __future__ import annotations

import asyncio
from datetime import datetime
from io import BytesIO
import logging
import os
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from card_generator import WelcomeCardData, make_welcome_card

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("venus-welcome")


# Custom emoji do bạn cung cấp.
EMOJI_WELCOME_ABOARD = "<:96359bubbleheart:1532387513031721101>"
EMOJI_WELCOME = "<a:SaF_Bluerollingstar:1532586674952081519>"
EMOJI_FLIGHT = "<a:fwb_cloudfly:1532586588658204724>"
EMOJI_PASSENGER = "<:14776kuromibow:1532387089281450135>"


def env_int(name: str, default: int | None = None) -> int | None:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} phải là một số nguyên.") from exc


TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
WELCOME_CHANNEL_ID = env_int("WELCOME_CHANNEL_ID")
TEST_GUILD_ID = env_int("TEST_GUILD_ID")
TIMEZONE_NAME = os.getenv("TIMEZONE", "Asia/Ho_Chi_Minh").strip()
DEFAULT_NATIONALITY = os.getenv("DEFAULT_NATIONALITY", "VIETNAM").strip() or "VIETNAM"

if not TOKEN:
    raise RuntimeError("Thiếu DISCORD_TOKEN trong file .env hoặc Railway Variables")
if WELCOME_CHANNEL_ID is None:
    raise RuntimeError("Thiếu WELCOME_CHANNEL_ID trong file .env hoặc Railway Variables")

try:
    SERVER_TIMEZONE = ZoneInfo(TIMEZONE_NAME)
except ZoneInfoNotFoundError as exc:
    raise RuntimeError(
        f"TIMEZONE='{TIMEZONE_NAME}' không hợp lệ. Thử dùng Asia/Ho_Chi_Minh."
    ) from exc

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)


def build_card_data(member: discord.Member) -> WelcomeCardData:
    now = datetime.now(SERVER_TIMEZONE)
    member_count = member.guild.member_count or len(member.guild.members)
    return WelcomeCardData(
        display_name=member.display_name,
        username=member.name,
        user_id=member.id,
        member_number=member_count,
        date_text=now.strftime("%d/%m/%Y"),
        time_text=now.strftime("%H:%M"),
        nationality=DEFAULT_NATIONALITY,
    )


async def render_member_card(
    member: discord.Member,
    data: WelcomeCardData | None = None,
) -> BytesIO:
    avatar_bytes: bytes | None = None
    try:
        avatar_bytes = await member.display_avatar.with_size(256).read()
    except discord.HTTPException:
        log.warning("Không tải được avatar của %s", member)

    card_data = data or build_card_data(member)
    png_bytes = await asyncio.to_thread(
        make_welcome_card,
        card_data,
        avatar_bytes=avatar_bytes,
    )
    return BytesIO(png_bytes)


def build_welcome_view(
    member: discord.Member,
    data: WelcomeCardData,
    image_filename: str,
) -> discord.ui.LayoutView:
    """
    Tạo welcome card cỡ lớn bằng Discord Components V2.

    MediaGallery làm ảnh hiển thị rộng như mẫu tham khảo. Phần nội dung nằm
    ngay bên dưới ảnh trong cùng một container, thay vì embed nhỏ có thumbnail.
    """
    member_count = member.guild.member_count or len(member.guild.members)

    view = discord.ui.LayoutView(timeout=None)
    container = discord.ui.Container(
        accent_colour=discord.Colour.from_rgb(225, 126, 214),
    )

    gallery = discord.ui.MediaGallery()
    gallery.add_item(
        media=f"attachment://{image_filename}",
        description=f"Boarding pass của {member.display_name}",
    )
    container.add_item(gallery)
    container.add_item(discord.ui.Separator())

    welcome_text = (
        f"## {EMOJI_WELCOME_ABOARD} WELCOME ABOARD\n"
        f"{EMOJI_WELCOME} **Chào mừng {member.mention} đã đến với "
        f"{member.guild.name}!**\n\n"
        f"{EMOJI_FLIGHT} **Chuyến bay:** `{data.resolved_flight_code()}`\n"
        f"{EMOJI_PASSENGER} **Hành khách:** `#{member_count}`\n\n"
        f"-# VENUS WORLD • {data.date_text} • {data.time_text}"
    )
    container.add_item(discord.ui.TextDisplay(welcome_text))
    view.add_item(container)
    return view


async def get_welcome_channel(guild: discord.Guild) -> discord.abc.Messageable | None:
    channel = guild.get_channel(WELCOME_CHANNEL_ID)
    if channel is None:
        try:
            channel = await bot.fetch_channel(WELCOME_CHANNEL_ID)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            log.exception("Không tìm thấy hoặc không truy cập được welcome channel")
            return None

    if getattr(channel, "guild", guild).id != guild.id:
        log.error("WELCOME_CHANNEL_ID không thuộc server %s", guild.name)
        return None
    return channel


async def send_welcome(member: discord.Member, channel: discord.abc.Messageable) -> None:
    data = build_card_data(member)
    image_buffer = await render_member_card(member, data)
    filename = f"welcome-{member.id}.png"
    file = discord.File(image_buffer, filename=filename)
    view = build_welcome_view(member, data, filename)

    await channel.send(
        file=file,
        view=view,
        allowed_mentions=discord.AllowedMentions(
            users=True,
            roles=False,
            everyone=False,
        ),
    )


@bot.event
async def on_ready() -> None:
    if not getattr(bot, "_venus_synced", False):
        try:
            if TEST_GUILD_ID:
                guild_object = discord.Object(id=TEST_GUILD_ID)
                bot.tree.copy_global_to(guild=guild_object)
                await bot.tree.sync(guild=guild_object)
                log.info("Đã sync slash command cho test server %s", TEST_GUILD_ID)
            else:
                await bot.tree.sync()
                log.info("Đã sync slash command global")
            bot._venus_synced = True
        except discord.HTTPException:
            log.exception("Không sync được slash command")

    log.info("Bot online: %s (ID: %s)", bot.user, bot.user.id if bot.user else "?")


@bot.event
async def on_member_join(member: discord.Member) -> None:
    channel = await get_welcome_channel(member.guild)
    if channel is None:
        return

    try:
        await send_welcome(member, channel)
        log.info("Đã gửi welcome card cho %s", member)
    except discord.Forbidden:
        log.exception("Bot thiếu quyền gửi tin nhắn hoặc đính kèm file")
    except discord.HTTPException:
        log.exception("Discord API lỗi khi gửi welcome card")
    except Exception:
        log.exception("Lỗi không xác định khi tạo welcome card")


@bot.tree.command(name="testwelcome", description="Tạo thử boarding pass welcome của bạn")
@app_commands.guild_only()
async def test_welcome(interaction: discord.Interaction) -> None:
    if not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("Lệnh này chỉ dùng trong server.", ephemeral=True)
        return

    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message(
            "Bạn cần quyền **Manage Server** để dùng lệnh này.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        data = build_card_data(interaction.user)
        image_buffer = await render_member_card(interaction.user, data)
        filename = f"welcome-test-{interaction.user.id}.png"
        file = discord.File(image_buffer, filename=filename)
        view = build_welcome_view(interaction.user, data, filename)
        await interaction.followup.send(
            file=file,
            view=view,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions(
                users=True,
                roles=False,
                everyone=False,
            ),
        )
    except Exception:
        log.exception("Lỗi khi chạy /testwelcome")
        await interaction.followup.send(
            "❌ Không tạo được welcome card. Hãy xem Deploy Logs trên Railway.",
            ephemeral=True,
        )


bot.run(TOKEN, log_handler=None)
