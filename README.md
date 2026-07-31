# Venus World Welcome Bot 🎀

Bot tự động tạo boarding pass Venus World và gửi welcome card cỡ lớn khi thành viên mới vào Discord.

## Chức năng

- Tự chạy khi có thành viên mới (`on_member_join`).
- Điền avatar, display name, username, user ID, số thành viên, ngày và giờ.
- Chữ được căn đúng giữa phần lòng của từng ô trên template.
- Welcome card dùng **Discord Components V2**: ảnh rộng ở trên, nội dung nằm bên dưới trong cùng một khung.
- Có slash command `/testwelcome` cho người có quyền **Manage Server**.
- Tự thu nhỏ chữ khi tên hoặc Discord ID quá dài.

> Discord không cung cấp quốc tịch. Trường `NATIONALITY` lấy từ `DEFAULT_NATIONALITY`.

## Cài đặt Discord

1. Tạo bot trong Discord Developer Portal.
2. Trong **Bot → Privileged Gateway Intents**, bật **Server Members Intent**.
3. Mời bot với các quyền:
   - View Channel
   - Send Messages
   - Attach Files
   - Use Application Commands
4. Bật Developer Mode trong Discord và copy ID kênh welcome cùng ID server.

## Variables

```env
DISCORD_TOKEN=TOKEN_MOI_CUA_BAN
WELCOME_CHANNEL_ID=ID_KENH_WELCOME
TEST_GUILD_ID=ID_SERVER
TIMEZONE=Asia/Ho_Chi_Minh
DEFAULT_NATIONALITY=VIETNAM
```

Không đưa `.env` hoặc token thật lên GitHub.

## Railway

1. Upload toàn bộ file trong thư mục này lên root GitHub repository.
2. Railway → **New Project** → **Deploy from GitHub Repo**.
3. Thêm các Variables ở trên.
4. Redeploy.

Source đã có `Dockerfile` và `railway.json`. Start Command là:

```bash
python bot.py
```

Bot không cần Domain và không cần biến `PORT`.

## Windows VPS

1. Cài Python 3.11 hoặc 3.12.
2. Chạy `setup.bat`.
3. Điền `.env`.
4. Chạy `start.bat`.

## Test

Trong server, chạy:

```text
/testwelcome
```

## Tùy chỉnh

- Template: `assets/boarding_pass.png`
- Tọa độ và font chữ: `card_generator.py`
- Nội dung welcome và custom emoji: `bot.py`
- Múi giờ: `TIMEZONE`

## Lưu ý

- Giữ `boarding_pass.png` đúng kích thước `1448x1086`.
- Source yêu cầu `discord.py 2.6.3+` để dùng Components V2 và MediaGallery.
- Nếu custom emoji không hiện, bot phải ở trong server chứa các emoji đó hoặc có quyền sử dụng emoji bên ngoài.
