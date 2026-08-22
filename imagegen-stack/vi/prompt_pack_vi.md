# Prompt pack tiếng Việt

Mẫu prompt cho từng loại nội dung, kèm từ khoá chống lệch văn hoá.

## Quy tắc chung

1. **Chữ cần hiện trên ảnh luôn đặt trong `"..."`** — `vi_prompt_layer.py` sẽ tách ra và
   chuyển sang đường ghép chữ (W2B). Không bao giờ để model tự viết tiếng Việt.
2. **Luôn nói rõ "Vietnamese"** khi có người hoặc địa điểm. Model được huấn luyện nặng
   dữ liệu Trung Quốc — bỏ trống thì áo dài ra thành sườn xám, nón lá ra thành nón Trung/Nhật.
3. **Negative prompt luôn có `text, letters, words, watermark`** để model chừa chỗ trống
   thay vì tự bịa chữ vào.

---

## Chống lệch văn hoá — dùng đúng cụm tiếng Anh

| Tiếng Việt | ✅ Viết thế này | ❌ Đừng viết |
|---|---|---|
| Áo dài | `Vietnamese ao dai, long silk tunic over trousers` | `traditional asian dress` → ra sườn xám |
| Nón lá | `Vietnamese conical palm-leaf hat (non la)` | `conical hat` → ra nón Trung Quốc |
| Phố cổ Hà Nội | `Hanoi Old Quarter, narrow tube houses, French-colonial shutters` | `old asian street` |
| Phở | `Vietnamese pho, flat rice noodles in clear beef broth, herbs on the side` | `noodle soup` → ra ramen |
| Cà phê sữa đá | `Vietnamese iced milk coffee, metal phin filter over condensed milk` | `iced coffee` |
| Người Việt | `Vietnamese woman / Vietnamese man` | `asian woman` → lệch sang Đông Á |
| Chợ nổi | `Mekong Delta floating market, wooden sampan boats` | `floating market` → ra Thái Lan |
| Tết | `Vietnamese Lunar New Year (Tet), yellow apricot blossom (hoa mai), red envelopes` | `chinese new year` |
| Xe máy phố | `dense Vietnamese motorbike traffic, Honda Cub scooters` | `asian traffic` |
| Bánh mì | `Vietnamese banh mi baguette sandwich, pickled carrot and daikon, cilantro` | `sandwich` |

---

## Mẫu 1 — Poster / banner marketing

```
poster quảng cáo <sản phẩm>, chữ "<CÂU CHÍNH>" ở <vị trí>,
<mô tả cảnh>, bố cục <dọc/ngang>, phong cách <tối giản/sang trọng/trẻ trung>,
chừa khoảng trống phía <trên/dưới> cho chữ
```

Ví dụ:
```
poster quán cà phê, chữ "Khuyến mãi 50%" ở giữa,
tách cà phê sữa đá trên bàn gỗ, ánh sáng ấm buổi sáng,
bố cục dọc, phong cách tối giản, chừa khoảng trống phía trên cho chữ
```
→ Model sinh nền có khoảng trống · `render_text.py` dựng chữ · W2B ghép lại.

## Mẫu 2 — Ảnh sản phẩm / TMĐT

```
<sản phẩm> trên nền <màu/chất liệu>, chụp studio, ánh sáng mềm ba điểm,
đổ bóng nhẹ, độ nét cao, không có chữ
```
Dùng **W3** (Qwen-Image-Edit-2511) nếu đã có ảnh sản phẩm và chỉ cần đổi nền —
giữ nguyên sản phẩm chính xác hơn nhiều so với sinh mới.

## Mẫu 3 — Minh hoạ / nội dung sáng tạo

```
<cảnh>, <thời điểm trong ngày>, <phong cách nghệ thuật>,
<góc máy>, <tâm trạng>
```
Ví dụ:
```
cô gái mặc áo dài trắng đi xe đạp qua phố cổ Hà Nội, sáng sớm sương mù,
tranh màu nước, góc máy ngang tầm mắt, yên bình hoài niệm
```

## Mẫu 4 — Sửa ảnh theo yêu cầu (W3/W4)

Câu lệnh sửa nên **ngắn, một việc một lần**:
```
đổi nền thành phòng khách hiện đại, giữ nguyên sản phẩm
xoá người phía sau, giữ nguyên bố cục
đổi áo sang màu đỏ, giữ nguyên khuôn mặt và dáng
ghép người ở ảnh 1 vào bối cảnh ảnh 2
```
Nhiều yêu cầu cùng lúc → chạy nhiều lượt, đừng nhồi vào một câu.

## Mẫu 5 — Video (W5A/W5B)

Wan2.2 cần mô tả **chuyển động**, không chỉ mô tả cảnh tĩnh:
```
<chủ thể> <đang làm gì>, camera <đứng yên/lia ngang/tiến vào>,
<tốc độ chuyển động>, <ánh sáng>
```
Ví dụ:
```
hơi nước bốc lên từ bát phở, camera tiến vào chậm,
chuyển động nhẹ nhàng, ánh sáng ấm buổi sáng
```
⚠️ Đừng yêu cầu chữ trong video — Wan2.2 không làm được. Ghép sau bằng `burn_text_video.sh`.

---

## Negative prompt sẵn dùng

| Loại | Negative |
|---|---|
| Mặc định | `text, watermark, signature, letters, words, caption, logo, blurry, low quality, distorted` |
| Có người | thêm `extra fingers, deformed hands, extra limbs, bad anatomy` |
| Ảnh sản phẩm | thêm `cluttered background, harsh shadows, reflection of photographer` |
| Chống lệch văn hoá | thêm `chinese style, japanese style, qipao, kimono, chinese characters` |
