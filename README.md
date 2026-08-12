# Mô phỏng GPLX

Ứng dụng desktop Windows phục vụ tự luyện và thi thử tình huống giao thông, chạy hoàn toàn offline.

## Công nghệ

- Python 3.11–3.13
- PySide6 / Qt 6
- Qt Multimedia và FFmpeg backend
- SQLite cho nội dung và lịch sử
- PyInstaller `--onedir` để tạo bản phát hành

## Chạy ở môi trường phát triển

```powershell
.\scripts\setup.ps1
.\scripts\run.ps1
```

Ứng dụng tự tạo dữ liệu mẫu lần đầu. Dữ liệu thật được đặt tại `content/content.db`; video đặt tại `content/videos`.

## Kiểm thử

```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Build bản offline

```powershell
.\scripts\build.ps1
```

Kết quả nằm trong `dist/MoPhongGPLX`. Phải phân phối nguyên thư mục; không chỉ sao chép riêng EXE.

## Vị trí dữ liệu

- Nội dung dùng chung: `content/content.db` và `content/videos/`.
- Lịch sử người dùng: `%LOCALAPPDATA%\MoPhongGPLX\history.db`.
- Khi phát triển, có thể đặt biến `GPLX_RUNTIME_DIR` để chuyển lịch sử sang một thư mục thử nghiệm.

## Bước tích hợp dữ liệu thật

1. Chuẩn hóa video thành MP4/H.264/AAC và đặt tên theo mã tình huống.
2. Chuyển bộ câu hỏi vào schema trong `src/gplx_sim/data/schema_content.sql`.
3. Chạy kiểm tra dữ liệu và video trước khi phát hành.
4. Tạo bộ cài từ thư mục `dist/MoPhongGPLX` bằng Inno Setup hoặc WiX.
