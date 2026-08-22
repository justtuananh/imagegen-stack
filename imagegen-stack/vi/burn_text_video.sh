#!/usr/bin/env bash
# burn_text_video.sh — ghép chữ tiếng Việt lên video do Wan2.2 sinh ra.
#
# Wan2.2 không render được chữ (model card ghi rõ language: en, zh, và không có
# tuyên bố nào về text trong video). Nên chữ phải ghép sau bằng ffmpeg.
#
#   ./burn_text_video.sh -i in.webm -o out.mp4 -t "Khuyến mãi 50%" -f fonts/BeVietnamPro-Bold.ttf
#   ./burn_text_video.sh -i in.webm -o out.mp4 -s phude.ass          # phụ đề có định dạng
#
set -euo pipefail

IN=""; OUT=""; TEXT=""; FONT=""; ASS=""
SIZE=64; COLOR="white"; POS="bottom"; BOX=1; START=""; END=""

usage() { sed -n '2,12p' "$0"; exit 1; }

while getopts "i:o:t:f:s:z:c:p:b:S:E:h" o; do
  case "$o" in
    i) IN=$OPTARG ;;   o) OUT=$OPTARG ;;  t) TEXT=$OPTARG ;;
    f) FONT=$OPTARG ;; s) ASS=$OPTARG ;;  z) SIZE=$OPTARG ;;
    c) COLOR=$OPTARG ;; p) POS=$OPTARG ;; b) BOX=$OPTARG ;;
    S) START=$OPTARG ;; E) END=$OPTARG ;;
    *) usage ;;
  esac
done
[ -z "$IN" ] || [ -z "$OUT" ] && usage
command -v ffmpeg >/dev/null || { echo "Thiếu ffmpeg"; exit 1; }

# --- Đường phụ đề: dùng file .ass, kiểm soát style tốt hơn hẳn drawtext
if [ -n "$ASS" ]; then
  ffmpeg -y -i "$IN" -vf "subtitles=${ASS}" -c:a copy "$OUT"
  echo "Xong: $OUT"; exit 0
fi

[ -z "$TEXT" ] && usage
[ -z "$FONT" ] && { echo "Cần -f <font.ttf> có đủ dấu tiếng Việt"; exit 1; }
[ -f "$FONT" ] || { echo "Không tìm thấy font: $FONT"; exit 1; }

# --- Chuẩn hoá NFC + ghi ra file.
# BẮT BUỘC với tiếng Việt: chuỗi NFD (dấu tách rời) trông y hệt nhưng ffmpeg dựng sai dấu.
# Dùng textfile= thay vì text= để khỏi phải escape : ' % \ — nguồn lỗi kinh điển của drawtext.
TXTFILE=$(mktemp /tmp/vitext.XXXXXX)
trap 'rm -f "$TXTFILE"' EXIT
python3 -c "
import sys, unicodedata, pathlib
pathlib.Path(sys.argv[2]).write_text(unicodedata.normalize('NFC', sys.argv[1]), encoding='utf-8')
" "$TEXT" "$TXTFILE"

case "$POS" in
  top)    XY="x=(w-text_w)/2:y=h*0.08" ;;
  center) XY="x=(w-text_w)/2:y=(h-text_h)/2" ;;
  *)      XY="x=(w-text_w)/2:y=h*0.85-text_h" ;;
esac

BOXOPT=""
[ "$BOX" = "1" ] && BOXOPT=":box=1:boxcolor=black@0.55:boxborderw=18"

ENABLE=""
if [ -n "$START" ] && [ -n "$END" ]; then
  ENABLE=":enable='between(t,${START},${END})'"
fi

ffmpeg -y -i "$IN" -vf \
  "drawtext=fontfile='${FONT}':textfile='${TXTFILE}':fontsize=${SIZE}:fontcolor=${COLOR}:${XY}${BOXOPT}${ENABLE}" \
  -c:a copy "$OUT"

echo "Xong: $OUT"
