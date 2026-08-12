# Nội dung ngoại tuyến

- `bundled_content.db`: database gốc được tạo tự động từ catalog 120 tình huống và được đóng cùng ứng dụng.
- `videos/`: đặt đúng 120 file `1.mp4` đến `120.mp4` tại đây.

Database mà ứng dụng chỉnh sửa nằm tại `%LOCALAPPDATA%\MoPhongGPLX\content.db`, không nằm trong thư mục này. Chạy `scripts\verify-content.ps1` để kiểm tra đủ database và video trước khi đóng gói.
