# Venus World Welcome Bot 🎀

Bot tự động tạo **boarding pass welcome** từ ảnh template Venus World khi thành viên mới tham gia Discord.

## Chức năng

- Tự chạy khi có thành viên mới (`on_member_join`).
- Điền avatar, display name, username, user ID, số thành viên, ngày và giờ.
- Gửi ảnh vào đúng welcome channel.
- Có slash command `/testwelcome` dành cho người có quyền **Manage Server**.
- Tự co chữ khi tên Discord quá dài.

> Discord không cung cấp quốc tịch của thành viên. Vì vậy trường `NATIONALITY` lấy từ `DEFAULT_NATIONALITY` trong `.env`.

## 1. Chuẩn bị bot Discord

1. Vào Discord Developer Portal và tạo application/bot.
2. Trong trang **Bot**, bật **Server Members Intent**.
3. Mời bot vào server với các quyền:
   - View Channel
   - Send Messages
   - Attach Files
   - Use Application Commands
4. Trong Discord, bật **Developer Mode**, sau đó copy:
   - ID welcome channel
   - ID server

## 2. Cài trên Windows VPS

Khuyến nghị dùng Python 3.11 hoặc 3.12.

1. Giải nén thư mục bot.
2. Chạy `setup.bat` một lần để cài thư viện và tạo file `.env`.
3. Mở file `.env` và điền:

```env
DISCORD_TOKEN=token_cua_bot
WELCOME_CHANNEL_ID=id_kenh_welcome
TEST_GUILD_ID=id_server
```

4. Chạy `start.bat`.
5. Trong server, dùng `/testwelcome` để kiểm tra bố cục.

## 3. Chạy 24/7

Cách đơn giản nhất trên Windows VPS:

- Mở `start.bat` và giữ cửa sổ chạy.
- Hoặc dùng Task Scheduler để chạy `start.bat` khi Windows khởi động.

## Tùy chỉnh

- Ảnh nền: `assets/boarding_pass.png`
- Vị trí chữ: `card_generator.py`
- Tin nhắn welcome: `WELCOME_MESSAGE` trong `.env`
- Múi giờ: `TIMEZONE=Asia/Ho_Chi_Minh`

## Lỗi thường gặp

### Bot online nhưng không gửi khi có người join

- Chưa bật **Server Members Intent** trong Developer Portal.
- Bot thiếu quyền xem kênh, gửi tin hoặc đính kèm file.
- `WELCOME_CHANNEL_ID` sai.

### `/testwelcome` không xuất hiện

- Điền đúng `TEST_GUILD_ID`, restart bot và chờ vài giây.
- Bot phải được mời với scope `applications.commands`.

### Chữ tiếng Việt bị ô vuông

Bot tự tìm Arial/Segoe UI trên Windows. Có thể chỉ định trực tiếp:

```env
FONT_BOLD=C:\Windows\Fonts\arialbd.ttf
FONT_REGULAR=C:\Windows\Fonts\arial.ttf
```

## Deploy lên Railway

Source đã có sẵn `railway.json` và `Procfile`.

1. Đưa toàn bộ file trong thư mục này lên **root** của GitHub repository.
2. Không upload `.env` thật lên GitHub.
3. Railway → **New Project** → **Deploy from GitHub Repo**.
4. Trong **Variables**, nhập các biến từ `.env.example`.
5. Start Command đã được đặt sẵn là `python bot.py`.

Bot Discord không cần Domain và không cần biến `PORT`.

## Bản sửa bố cục

- Chữ được căn giữa theo chiều dọc bằng text anchor, nên không còn dồn lên mép ô khi đổi từ Windows sang Railway Linux.
- Các dòng `FROM`, `TO`, `FLIGHT`, `DATE`, `BOARDING TIME` được căn cùng một trục.
- Username không bị lặp hai dấu `@` vì template đã có icon `@`.
- Template bắt buộc giữ đúng kích thước `1448x1086`.
