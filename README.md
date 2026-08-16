# Mô phỏng GPLX

Ứng dụng desktop Windows phục vụ ôn tập và thi mô phỏng tình huống giao thông. Hai chế độ ôn tập chạy hoàn toàn offline; phần thi tốt nghiệp được chuẩn bị giao diện để tích hợp máy chủ sau.

## Chức năng hiện có

- Trang chủ gồm hai lựa chọn: **Ôn tập** và **Thi tốt nghiệp**.
- **Tự luyện:** chọn một trong ba nguồn nội dung: ngẫu nhiên 1–15 tình huống, bộ đề tối đa 10 tình huống do Admin chuẩn bị, hoặc tự chọn trong danh sách 120 tình huống theo chương/từ khóa.
- Màn hình luyện tập hỗ trợ chuyển nhanh giữa các câu; câu đúng đủ 4 phần được đánh dấu xanh, câu sai ít nhất một phần được đánh dấu đỏ và đáp án nháp được giữ khi chuyển câu.
- **Thi thử:** lấy ngẫu nhiên 10 tình huống, mặc định 15 phút, không lộ đáp án trong lúc làm và tự nộp khi hết giờ.
- Catalog chuẩn có 6 chương, 120 tình huống, 480 phần câu hỏi và 1.920 phương án được trích từ `MP1.pdf`.
- Mỗi phần câu hỏi luôn có đúng 4 phương án A–D và đúng một đáp án đúng.
- **Thi tốt nghiệp:** đã có màn hình chọn khóa thi, nhập SBD và vùng hiển thị thông tin thí sinh. Việc kết nối máy chủ sẽ triển khai sau.

## Công nghệ

- Python 3.11–3.13
- PySide6 / Qt 6, Qt Multimedia và FFmpeg backend
- SQLite cho nội dung và lịch sử
- PyInstaller `--onedir` để tạo bản phát hành offline

## Chạy ở môi trường phát triển

```powershell
.\scripts\setup.ps1
.\scripts\run.ps1
```

Ở lần chạy đầu tiên, ứng dụng tự tạo `content/bundled_content.db` từ catalog được đóng trong mã nguồn và tự cài bản đang dùng vào `%LOCALAPPDATA%\MoPhongGPLX\content.db`. Người dùng không cần cài SQLite hoặc nhập SQL.

## Đặt và kiểm tra video

Chép trực tiếp 120 file `1.mp4` đến `120.mp4` vào:

```text
content\videos\
```

Sau đó kiểm tra database và video:

```powershell
.\scripts\verify-content.ps1
```

Kết quả đúng phải báo database hợp lệ và `Đã đủ 120/120 video`.

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

## Build bản offline

```powershell
.\scripts\build.ps1
```

Kết quả nằm trong `dist\MoPhongGPLX` với cấu trúc:

```text
MoPhongGPLX\
├── MoPhongGPLX.exe
├── _internal\
└── content\
    ├── bundled_content.db
    └── videos\
        ├── 1.mp4
        └── ... 120.mp4
```

Phải phân phối nguyên thư mục `dist\MoPhongGPLX`; không sao chép riêng file EXE.

## Các lớp dữ liệu

- Nguồn có thể tái tạo và lưu trong Git: `src/gplx_sim/data/content_catalog.json`.
- Database gốc đi cùng bản phát hành: `content/bundled_content.db`.
- Database nội dung đang dùng: `%LOCALAPPDATA%\MoPhongGPLX\content.db`.
- Bản sao trước khi nâng phiên bản: `%LOCALAPPDATA%\MoPhongGPLX\content.before_update.db`.
- Lịch sử tự luyện/thi thử: `%LOCALAPPDATA%\MoPhongGPLX\history.db`.
- Video dùng chung: `content/videos/` cạnh ứng dụng.

Nếu database đang dùng bị thiếu bảng hoặc sai cấu trúc, ứng dụng sao lưu rồi tự khôi phục từ database gốc. Các chỉnh sửa hợp lệ của trang quản trị không bị ghi đè khi mở lại cùng phiên bản.

## Tái tạo catalog từ PDF

Chỉ chạy khi `MP1.pdf` thay đổi:

```powershell
.\.venv\Scripts\python.exe .\scripts\import_mp1.py .\MP1.pdf .\src\gplx_sim\data\content_catalog.json
```

Trình nhập kiểm tra đúng 120 trang, 6 chương, 4 phần mỗi tình huống, 4 phương án mỗi phần và nhận diện đáp án được tô đỏ.
