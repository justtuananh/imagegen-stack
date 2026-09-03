"""
content_vi.py — chữ nghĩa hiện trên giao diện Auralis (gợi ý, trích dẫn, hướng dẫn).

Lấy nguyên từ bản thiết kế. Để bên server và phát qua `/api/options` để sửa lời văn
không phải đụng vào JS, và để không có hai bản chép tay rồi lệch nhau.
"""

EDIT_CHIPS = [
    "Đổi nền", "Xoá vật thể phía sau", "Sáng hơn", "Chụp gần hơn", "Tông màu ấm hơn",
]

FILTERS = ["Tất cả", "Ảnh mới", "Bản sửa"]

SUGGESTIONS = [
    {"tag": "bán hàng", "text": "Ảnh sản phẩm ly sứ trắng trên nền gỗ, ánh sáng tự nhiên"},
    {"tag": "mạng xã hội", "text": "Bó hoa hướng dương trên bàn ăn, nắng buổi sáng"},
    {"tag": "chân dung", "text": "Chân dung ánh sáng cửa sổ, nền tối giản, tông điện ảnh"},
    {"tag": "hình nền", "text": "Dãy núi mù sương lúc bình minh, tông xanh lam nhẹ"},
]

QUOTES = [
    {"t": "Mọi thứ bạn có thể tưởng tượng đều là thật.", "a": "Pablo Picasso"},
    {"t": "Tôi mơ về tranh của mình, rồi tôi vẽ giấc mơ ấy.", "a": "Vincent van Gogh"},
    {"t": "Nghệ thuật không phải điều bạn thấy, mà là điều bạn khiến người khác thấy.", "a": "Edgar Degas"},
    {"t": "Nghệ thuật không tái tạo cái hữu hình; nó khiến ta thấy được cái vô hình.", "a": "Paul Klee"},
    {"t": "Sáng tạo là dám dấn thân.", "a": "Henri Matisse"},
    {"t": "Sự đơn giản là đỉnh cao của tinh tế.", "a": "Leonardo da Vinci"},
]

HELP = [
    {"n": "1", "title": "Viết điều bạn muốn thấy",
     "body": "Gõ vào ô ở cuối màn hình bằng tiếng Việt bình thường: có gì trong ảnh, ở đâu, "
             "ánh sáng ra sao. Không cần từ khoá kỹ thuật."},
    {"n": "2", "title": "Chọn thêm nếu muốn",
     "body": "Mở “Tùy chỉnh nâng cao” để chọn phong cách, khung ảnh và số lượng ảnh. "
             "Bỏ qua cũng được — Auralis tự chọn giúp bạn."},
    {"n": "3", "title": "Chờ vài giây",
     "body": "Thanh tiến trình cho biết ảnh đang được vẽ tới đâu. Ảnh xong sẽ hiện ngay "
             "trong khung trò chuyện."},
    {"n": "4", "title": "Sửa cho vừa ý",
     "body": "Bấm “Sửa ảnh này” rồi nói điều muốn thay đổi, hoặc bấm vào ảnh để xem lớn và "
             "ghi yêu cầu ngay bên cạnh. Mọi ảnh đều được lưu trong Thư viện ảnh."},
]
