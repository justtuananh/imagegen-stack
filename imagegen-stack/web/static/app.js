/* app.js — giao diện Auralis, dựng lại từ bản thiết kế Claude Design bằng JS thường.
 *
 * Bản thiết kế chạy trên dc-runtime (React) với dữ liệu giả. Ở đây giữ NGUYÊN bố cục,
 * màu và chuyển động của thiết kế, nhưng thay:
 *   - ô gradient nhấp nháy      -> ảnh thật từ ComfyUI
 *   - tiến độ giả (timer 340ms) -> tiến độ THẬT theo từng bước lấy mẫu (SSE)
 *   - SEED_CHATS/SEED_MESSAGES  -> hội thoại của người dùng, lưu localStorage
 *   - credits: 12               -> bỏ hẳn, vì không có thật
 *
 * Tên biến trạng thái cố ý giữ giống bản thiết kế (view, activeChat, messages, gen,
 * editFor, lightbox, filter…) để đối chiếu hai bên cho nhanh.
 */
"use strict";

let STYLES = ["Ảnh thật", "Điện ảnh", "Tranh vẽ", "3D"];
let RATIOS = [
  { label: "Vuông", ar: "1/1" },
  { label: "Ngang", ar: "1664/928" },
  { label: "Dọc", ar: "928/1664" },
];
let EDIT_CHIPS = ["Đổi nền", "Xoá vật thể phía sau", "Sáng hơn", "Chụp gần hơn", "Tông màu ấm hơn"];
let FILTERS = ["Tất cả", "Ảnh mới", "Bản sửa"];

let SUGGESTIONS = [
  { tag: "bán hàng", text: "Ảnh sản phẩm ly sứ trắng trên nền gỗ, ánh sáng tự nhiên" },
  { tag: "mạng xã hội", text: "Bó hoa hướng dương trên bàn ăn, nắng buổi sáng" },
  { tag: "chân dung", text: "Chân dung ánh sáng cửa sổ, nền tối giản, tông điện ảnh" },
  { tag: "hình nền", text: "Dãy núi mù sương lúc bình minh, tông xanh lam nhẹ" },
];

let QUOTES = [
  { t: "Mọi thứ bạn có thể tưởng tượng đều là thật.", a: "Pablo Picasso" },
  { t: "Tôi mơ về tranh của mình, rồi tôi vẽ giấc mơ ấy.", a: "Vincent van Gogh" },
  { t: "Nghệ thuật không phải điều bạn thấy, mà là điều bạn khiến người khác thấy.", a: "Edgar Degas" },
  { t: "Nghệ thuật không tái tạo cái hữu hình; nó khiến ta thấy được cái vô hình.", a: "Paul Klee" },
  { t: "Sáng tạo là dám dấn thân.", a: "Henri Matisse" },
  { t: "Sự đơn giản là đỉnh cao của tinh tế.", a: "Leonardo da Vinci" },
];

let HELP = [
  { n: "1", title: "Viết điều bạn muốn thấy", body: "Gõ vào ô ở cuối màn hình bằng tiếng Việt bình thường: có gì trong ảnh, ở đâu, ánh sáng ra sao. Không cần từ khoá kỹ thuật." },
  { n: "2", title: "Chọn thêm nếu muốn", body: "Mở “Tùy chỉnh nâng cao” để chọn phong cách, khung ảnh và số lượng ảnh. Bỏ qua cũng được — Auralis tự chọn giúp bạn." },
  { n: "3", title: "Chờ vài giây", body: "Thanh tiến trình cho biết ảnh đang được vẽ tới đâu. Ảnh xong sẽ hiện ngay trong khung trò chuyện." },
  { n: "4", title: "Sửa cho vừa ý", body: "Bấm “Sửa ảnh này” rồi nói điều muốn thay đổi, hoặc bấm vào ảnh để xem lớn và ghi yêu cầu ngay bên cạnh. Mọi ảnh đều được lưu trong Thư viện ảnh." },
];

const PICK = { bd: "var(--accent)", bg: "var(--accent-soft)", fg: "var(--accent-ink)" };
const IDLE = { bd: "var(--line)", bg: "var(--card)", fg: "var(--fg2)" };
const chipOf = on => (on ? PICK : IDLE);

const ICON = {
  collapse: '<svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M9.6 4.6 6.2 8l3.4 3.4M13.2 4.6 9.8 8l3.4 3.4"></path></svg>',
  expand: '<svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M6.4 4.6 9.8 8l-3.4 3.4M2.8 4.6 6.2 8l-3.4 3.4"></path></svg>',
  plus: '<svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M8 3.2v9.6M3.2 8h9.6"></path></svg>',
  chat: '<svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2.8" width="12" height="9" rx="2.6"></rect><path d="M5.6 11.9 5.1 14l2.7-2.1"></path></svg>',
  grid: '<svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.25"><rect x="2.2" y="2.2" width="5" height="5" rx="1.2"></rect><rect x="8.8" y="2.2" width="5" height="5" rx="1.2"></rect><rect x="2.2" y="8.8" width="5" height="5" rx="1.2"></rect><rect x="8.8" y="8.8" width="5" height="5" rx="1.2"></rect></svg>',
  x: '<svg width="11" height="11" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.25" stroke-linecap="round"><path d="M3 3l6 6M9 3l-6 6"></path></svg>',
  xBig: '<svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"><path d="M4.4 4.4l7.2 7.2M11.6 4.4l-7.2 7.2"></path></svg>',
  help: '<svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="8" r="6.2"></circle><path d="M6.3 6.2a1.75 1.75 0 1 1 2.6 1.7c-.6.3-.9.7-.9 1.4"></path><path d="M8 11.6h.01"></path></svg>',
  moon: '<svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"><path d="M13.2 9.7A5.7 5.7 0 0 1 6.3 2.8a5.8 5.8 0 1 0 6.9 6.9z"></path></svg>',
  sun: '<svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"><circle cx="8" cy="8" r="3.1"></circle><path d="M8 1.2v1.5M8 13.3v1.5M1.2 8h1.5M13.3 8h1.5M3.3 3.3l1.1 1.1M11.6 11.6l1.1 1.1M12.7 3.3l-1.1 1.1M4.4 11.6l-1.1 1.1"></path></svg>',
  pencil: '<svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.35" stroke-linecap="round" stroke-linejoin="round"><path d="M2.8 13.4h5.4"></path><path d="M4.6 10.8 11 4.4"></path><rect x="10.5" y="2" width="4" height="4" rx="0.7" transform="rotate(45 12.5 4)"></rect></svg>',
  redo: '<svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.35" stroke-linecap="round"><circle cx="8" cy="8" r="5.5" stroke-dasharray="23 8"></circle><rect x="11.1" y="1.1" width="3.2" height="3.2" rx="0.6" transform="rotate(45 12.7 2.7)" fill="currentColor" stroke="none"></rect></svg>',
  download: '<svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.35" stroke-linecap="round" stroke-linejoin="round"><path d="M8 2.6v7.4M5.2 7.4 8 10.2l2.8-2.8"></path><path d="M3 13.2h10"></path></svg>',
  gear: '<svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.3"><circle cx="8" cy="8" r="5.7"></circle><rect x="8" y="3.5" width="4.4" height="4.4" rx="0.7" transform="rotate(45 8 3.5)" fill="currentColor" stroke="none" opacity="0.9"></rect></svg>',
  caretUp: '<svg width="9" height="9" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M2.6 7.4 6 4l3.4 3.4"></path></svg>',
  caretDown: '<svg width="9" height="9" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M2.6 4.6 6 8l3.4-3.4"></path></svg>',
  send: '<svg width="17" height="17" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 14.4V4.2"></path><path d="M4.7 8.5 9 4.2l4.3 4.3"></path></svg>',
  clip: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.35" stroke-linecap="round" stroke-linejoin="round"><path d="M10.9 5.2 5.8 10.3a1.9 1.9 0 0 0 2.7 2.7l5.1-5.1a3.4 3.4 0 0 0-4.8-4.8L3.4 8.5a4.9 4.9 0 0 0 6.9 6.9"></path></svg>',
  mark: '<svg width="30" height="30" viewBox="0 0 32 32" aria-hidden="true" style="flex:0 0 30px; margin-top:2px;"><circle cx="16" cy="16" r="14.2" fill="none" stroke="var(--line2)" stroke-width="1.3"></circle><rect x="16" y="8.2" width="11" height="11" rx="1.4" transform="rotate(45 16 8.2)" fill="var(--accent)"></rect></svg>',
  logo: '<svg width="32" height="32" viewBox="0 0 32 32" aria-hidden="true" style="flex:0 0 32px;"><circle cx="16" cy="16" r="14.2" fill="none" stroke="var(--accent)" stroke-width="1.4" opacity=".45"></circle><circle cx="16" cy="16" r="9.5" fill="none" stroke="var(--accent)" stroke-width="1.1" opacity=".3"></circle><rect x="16" y="8.2" width="11" height="11" rx="1.4" transform="rotate(45 16 8.2)" fill="var(--accent)"></rect></svg>',
};

/* ── tiện ích ────────────────────────────────────────────────────────────── */
const esc = s => String(s ?? "").replace(/[&<>"']/g, c =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const shortLabel = p => { const t = (p || "").trim(); return t.length > 46 ? t.slice(0, 46) + "…" : t; };
const arOf = name => (RATIOS.find(x => x.label === name) || RATIOS[0]).ar;
const uid = p => p + Math.random().toString(36).slice(2, 9);

function whenLabel(ts) {
  const d = new Date(ts), now = new Date();
  const hh = String(d.getHours()).padStart(2, "0") + ":" + String(d.getMinutes()).padStart(2, "0");
  if (d.toDateString() === now.toDateString()) return "Hôm nay, " + hh;
  return String(d.getDate()).padStart(2, "0") + "/" + String(d.getMonth() + 1).padStart(2, "0") + ", " + hh;
}

/* ── trạng thái ──────────────────────────────────────────────────────────── */
const S = {
  theme: "light", rail: true, adv: false, qi: 0, help: false,
  view: "chat", activeChat: null, chats: [], messages: {},
  input: "", style: "Ảnh thật", ratio: "Vuông", count: 1,
  gen: null, editFor: null, editText: "", lightbox: null, lbText: "",
  filter: "Tất cả", attach: [], toast: null, galleryItems: [],
};

/* Chỉ tuỳ chọn hiển thị mới nằm ở trình duyệt. Hội thoại và ảnh do server giữ —
   xem web/store.py — nên đổi máy vẫn còn, và thư viện luôn khớp với ảnh có thật. */
function savePrefs() {
  try {
    localStorage.setItem("auralis-theme", S.theme);
    localStorage.setItem("auralis-prefs", JSON.stringify(
      { style: S.style, ratio: S.ratio, count: S.count }));
  } catch (e) { /* trình duyệt chặn localStorage — bỏ qua, không làm hỏng app */ }
}
function loadPrefs() {
  try {
    const t = localStorage.getItem("auralis-theme");
    if (t === "dark" || t === "light") S.theme = t;
    const p = JSON.parse(localStorage.getItem("auralis-prefs") || "{}");
    if (p.style) S.style = p.style;
    if (p.ratio) S.ratio = p.ratio;
    if (p.count) S.count = p.count;
  } catch (e) { /* dữ liệu hỏng thì dùng mặc định */ }
}
const save = savePrefs;

const msgs = () => S.messages[S.activeChat] || [];

async function newChat() {
  const c = await api("/api/chats", { method: "POST" });
  S.chats.unshift(c);
  S.messages[c.id] = [];
  S.activeChat = c.id; S.view = "chat"; S.input = ""; S.editFor = null; S.attach = [];
  render();
}

async function removeChat(id) {
  await api("/api/chats/" + id, { method: "DELETE" });
  S.chats = S.chats.filter(c => c.id !== id);
  delete S.messages[id];
  S.editFor = null; S.lightbox = null;
  if (S.activeChat === id) {
    S.activeChat = S.chats[0] ? S.chats[0].id : null;
    if (!S.activeChat) return newChat();
    await loadMessages(S.activeChat);
  }
  await loadGallery();
  render();
}

async function loadMessages(cid) {
  if (!cid) return;
  S.messages[cid] = (await api("/api/chats/" + cid + "/messages")).messages;
}

async function loadGallery() {
  S.galleryItems = (await api("/api/gallery?filter=" + encodeURIComponent(S.filter))).images;
}

async function boot() {
  loadPrefs();
  render();                                   // vẽ khung trước cho đỡ trắng màn hình
  try {
    const o = await api("/api/options");
    STYLES = o.styles;
    RATIOS = o.ratios.map(r => ({ label: r.label, ar: r.ar }));
    EDIT_CHIPS = o.editChips; FILTERS = o.filters;
    SUGGESTIONS = o.suggestions; QUOTES = o.quotes; HELP = o.help;

    S.chats = (await api("/api/chats")).chats;
    if (!S.chats.length) { await newChat(); }
    else { S.activeChat = S.chats[0].id; await loadMessages(S.activeChat); }
    await loadGallery();
  } catch (e) {
    toast("❌ Không đọc được dữ liệu từ server: " + e.message);
  }
  render();
}

/* ── gọi backend ─────────────────────────────────────────────────────────── */
async function api(path, opts) {
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
  return r.json();
}

async function uploadFile(file) {
  const fd = new FormData();
  fd.append("file", file);
  const r = await fetch("/api/upload", { method: "POST", body: fd });
  if (!r.ok) throw new Error("Tải ảnh lên thất bại");
  return (await r.json()).id;
}

/* Sinh ảnh. Server đã ghi sẵn tin nhắn người dùng + tin nhắn AI rỗng vào store,
   nên ở đây chỉ việc nghe SSE và gắn ảnh vào đúng tin nhắn đó khi từng ảnh ra lò. */
async function startGen(prompt, kind, baseImage) {
  if (!prompt || !prompt.trim() || S.gen) return;
  const count = kind === "edit" ? Math.min(2, S.count || 1) : S.count;
  const attachIds = S.attach.map(a => a.id);

  S.gen = { prompt, kind, count, ar: arOf(S.ratio), style: S.style,
            pct: 0, step: "Đang gửi yêu cầu…", images: [] };
  S.input = ""; S.editFor = null; S.editText = ""; S.attach = [];
  render(); scrollBottom();

  let res;
  try {
    res = await api("/api/generate", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, kind, chat: S.activeChat, style: S.style,
                             ratio: S.ratio, count, images: attachIds,
                             base_image: baseImage || null }),
    });
  } catch (e) {
    S.gen = null; toast("❌ " + e.message); render(); return;
  }

  S.activeChat = res.chat;
  await loadMessages(res.chat);              // lấy tin nhắn server vừa ghi
  S.chats = (await api("/api/chats")).chats; // tên cuộc trò chuyện có thể vừa đổi
  render(); scrollBottom();

  const es = new EventSource("/api/progress/" + res.job);
  const done = [];
  es.onmessage = ev => {
    const d = JSON.parse(ev.data);
    if (d.type === "start") { S.gen.ar = d.ar; S.gen.count = d.count; }
    else if (d.type === "progress") {
      const per = 100 / S.gen.count;
      const inner = d.total ? (d.step / d.total) : 0;
      S.gen.pct = Math.min(100, Math.round(d.index * per + inner * per));
      S.gen.step = d.total
        ? `Đang vẽ ảnh ${d.index + 1}/${S.gen.count} — bước ${d.step}/${d.total}`
        : "Đang nạp model vào GPU…";
    } else if (d.type === "image") {
      done.push(d.id);
      S.gen.images = done.slice();
      S.gen.pct = Math.round((done.length / S.gen.count) * 100);
    } else if (d.type === "error") {
      toast("❌ " + d.message);
    }
    render();
  };
  const finish = async () => {
    es.close();
    S.gen = null;
    await loadMessages(res.chat);
    await loadGallery();
    render(); scrollBottom();
  };
  es.onerror = finish;
  es.addEventListener("end", finish);
}

let toastTimer = null;
function toast(msg) {
  S.toast = msg; clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { S.toast = null; render(); }, 5200);
}

/* ── mảnh giao diện ──────────────────────────────────────────────────────── */
const MONO = "font-family:'JetBrains Mono', ui-monospace, monospace;";
const SERIF = "font-family:'Playfair Display', Georgia, serif;";
const LABEL = MONO + "font-size:9.5px; letter-spacing:.16em; text-transform:uppercase; color:var(--muted);";
const BTN_GHOST = "border:1px solid var(--line); border-radius:11px; background:var(--card); color:var(--fg); font-size:13px; font-weight:500; cursor:pointer;";
const HOVER_ACCENT = "border-color:var(--accent); color:var(--accent-ink)";

const tile = (inner, ar, extra = "") =>
  `<div style="position:absolute; inset:0; background:repeating-linear-gradient(135deg, var(--tile-a) 0 9px, var(--tile-b) 9px 18px);${extra}"></div>${inner}`;

const imgTag = id =>
  `<img src="/api/image/${esc(id)}" alt="" loading="lazy" style="position:absolute; inset:0; width:100%; height:100%; object-fit:cover; display:block;">`;

function sectionHead(text) {
  return `<div style="display:flex; align-items:center; gap:9px; padding:12px 10px 8px;">
    <span style="${LABEL} white-space:nowrap;">${esc(text)}</span>
    <span style="flex:1; height:1px; background:var(--line);"></span>
    <span style="width:4px; height:4px; background:var(--accent); opacity:.5; transform:rotate(45deg);"></span></div>`;
}

function chatRow(c) {
  const on = c.id === S.activeChat && S.view === "chat";
  return `<div style="display:flex; align-items:center; gap:2px; border-radius:10px; background:${on ? "var(--hover)" : "transparent"};" data-hover="background:var(--hover)">
    <button data-act="openChat" data-id="${c.id}" style="flex:1; min-width:0; padding:9px 4px 9px 11px; border:0; border-radius:10px 0 0 10px; background:transparent; color:var(--fg2); text-align:left; font-size:13.5px; line-height:1.35; cursor:pointer; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" data-hover="color:var(--fg)">${esc(c.title)}</button>
    <button data-act="delChat" data-id="${c.id}" title="Xoá cuộc trò chuyện" style="flex:0 0 22px; width:22px; height:22px; margin-right:7px; border:0; border-radius:6px; background:transparent; color:var(--line2); line-height:1; cursor:pointer; opacity:.7;" data-hover="color:var(--accent); opacity:1">${ICON.x}</button>
  </div>`;
}

function railOpen() {
  const today = [], earlier = [];
  const dayAgo = Date.now() - 864e5;
  S.chats.forEach(c => ((c.ts || 0) > dayAgo ? today : earlier).push(c));
  return `<aside style="width:288px; flex:0 0 288px; height:100%; display:flex; flex-direction:column; background:var(--panel); border-right:1px solid var(--line); overflow:hidden;">
    <div style="display:flex; align-items:center; gap:12px; padding:22px 16px 18px 20px;">
      ${ICON.logo}
      <div style="min-width:0;">
        <div style="${SERIF} font-size:23px; letter-spacing:.03em; line-height:1;">Auralis</div>
        <div style="${LABEL} margin-top:4px; white-space:nowrap;">prompt to picture</div>
      </div>
      <button data-act="toggleRail" title="Thu gọn thanh bên" style="margin-left:auto; flex:0 0 30px; width:30px; height:30px; display:flex; align-items:center; justify-content:center; border-radius:9px; border:1px solid var(--line); background:var(--card); color:var(--muted); cursor:pointer;" data-hover="color:var(--fg); border-color:var(--line2)">${ICON.collapse}</button>
    </div>
    <div style="padding:0 16px 14px;">
      <button data-act="newChat" style="width:100%; display:flex; align-items:center; justify-content:center; gap:9px; padding:12px 14px; border-radius:13px; border:0; background:var(--accent); color:#fff; font-weight:600; font-size:14px; cursor:pointer; white-space:nowrap;" data-hover="background:var(--accent-h)">
        <span style="display:flex; align-items:center; line-height:0;">${ICON.plus}</span><span>Tạo ảnh mới</span></button>
    </div>
    <div style="padding:0 16px 16px; display:flex; flex-direction:column; gap:2px;">
      <button data-act="goChat" style="display:flex; align-items:center; gap:11px; width:100%; padding:9px 10px; border:0; border-radius:10px; background:transparent; color:var(--fg); text-align:left; font-size:14px; cursor:pointer;" data-hover="background:var(--hover)">
        <span style="display:flex; width:16px; justify-content:center; color:var(--muted);">${ICON.chat}</span><span>Cuộc trò chuyện</span></button>
      <button data-act="goGallery" style="display:flex; align-items:center; gap:11px; width:100%; padding:9px 10px; border:0; border-radius:10px; background:transparent; color:var(--fg); text-align:left; font-size:14px; cursor:pointer;" data-hover="background:var(--hover)">
        <span style="display:flex; width:16px; justify-content:center; color:var(--muted);">${ICON.grid}</span><span>Thư viện ảnh</span>
        <span style="margin-left:auto; ${MONO} font-size:11px; color:var(--muted);">${allImages().length}</span></button>
    </div>
    <div style="flex:1; min-height:0; overflow-y:auto; padding:0 16px 8px;">
      ${today.length ? sectionHead("hôm nay") + today.map(chatRow).join("") : ""}
      ${earlier.length ? sectionHead("trước đó") + earlier.map(chatRow).join("") : ""}
    </div>
    <div style="border-top:1px solid var(--line); padding:14px 18px 16px; display:flex; align-items:center; gap:11px;">
      <div style="width:30px; height:30px; border-radius:50%; background:var(--chip); border:1px solid var(--line); display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:600; color:var(--fg2); flex:0 0 30px;">DE</div>
      <div style="font-size:13.5px; font-weight:500; white-space:nowrap;">Duy Em</div>
    </div>
  </aside>`;
}

function railClosed() {
  const sq = bg => `width:38px; height:38px; border-radius:11px; border:1px solid var(--line); background:${bg}; color:var(--fg2); font-size:14px; cursor:pointer; display:flex; align-items:center; justify-content:center;`;
  return `<aside style="width:66px; flex:0 0 66px; height:100%; display:flex; flex-direction:column; align-items:center; gap:8px; padding:22px 0 16px; background:var(--panel); border-right:1px solid var(--line);">
    <button data-act="toggleRail" title="Mở rộng thanh bên" style="width:30px; height:30px; margin-bottom:20px; display:flex; align-items:center; justify-content:center; border-radius:9px; border:1px solid var(--line); background:var(--card); color:var(--muted); cursor:pointer;" data-hover="color:var(--fg); border-color:var(--line2)">${ICON.expand}</button>
    <button data-act="newChat" title="Tạo ảnh mới" style="width:38px; height:38px; border-radius:11px; border:0; background:var(--accent); color:#fff; cursor:pointer; display:flex; align-items:center; justify-content:center;" data-hover="background:var(--accent-h)">${ICON.plus}</button>
    <button data-act="goChat" title="Cuộc trò chuyện" style="${sq(S.view === "chat" ? "var(--hover)" : "var(--card)")}" data-hover="color:var(--fg); border-color:var(--line2)">${ICON.chat}</button>
    <button data-act="goGallery" title="Thư viện ảnh" style="${sq(S.view === "gallery" ? "var(--hover)" : "var(--card)")}" data-hover="color:var(--fg); border-color:var(--line2)">${ICON.grid}</button>
    <div style="margin-top:auto; width:30px; height:30px; border-radius:50%; background:var(--chip); border:1px solid var(--line); display:flex; align-items:center; justify-content:center; font-size:11.5px; font-weight:600; color:var(--fg2);">DE</div>
  </aside>`;
}

function header() {
  const gal = S.view === "gallery";
  const title = gal ? "Thư viện ảnh"
    : ((S.chats.find(c => c.id === S.activeChat) || {}).title || "Trò chuyện mới");
  const sub = gal ? allImages().length + " ảnh đã tạo" : "Mô tả một câu, nhận ảnh trong ít giây";
  const tab = (on, act, txt) => `<button data-act="${act}" style="padding:7px 15px; border:0; border-radius:9px; font-size:13.5px; font-weight:500; white-space:nowrap; cursor:pointer; background:${on ? "var(--card)" : "transparent"}; color:${on ? "var(--fg)" : "var(--muted)"};">${txt}</button>`;
  const pill = "display:flex; flex:0 0 auto; align-items:center; gap:8px; height:38px; padding:0 14px; border-radius:11px; border:1px solid var(--line); background:var(--card); color:var(--fg2); font-size:13px; font-weight:500; white-space:nowrap; cursor:pointer;";
  return `<header style="flex:0 0 auto; display:flex; align-items:center; gap:16px; padding:15px 30px; border-bottom:1px solid var(--line);">
    <div style="flex:1 1 auto; min-width:0; overflow:hidden;">
      <div style="${SERIF} font-size:19px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${esc(title)}</div>
      <div style="font-size:12.5px; color:var(--muted); margin-top:3px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${esc(sub)}</div>
    </div>
    <div style="margin-left:auto; flex:0 0 auto; display:flex; align-items:center; gap:10px;">
      <div style="display:flex; flex:0 0 auto; padding:3px; background:var(--chip); border-radius:11px; border:1px solid var(--line);">
        ${tab(!gal, "goChat", "Trò chuyện")}${tab(gal, "goGallery", "Ảnh đã tạo")}
      </div>
      <button data-act="openHelp" title="Hướng dẫn sử dụng" style="${pill}" data-hover="${HOVER_ACCENT}">
        <span style="display:flex; align-items:center; line-height:0;">${ICON.help}</span><span>Hướng dẫn</span></button>
      <button data-act="toggleTheme" title="Đổi nền sáng / tối" style="${pill}" data-hover="${HOVER_ACCENT}">
        <span style="display:flex; align-items:center; line-height:0;">${S.theme === "dark" ? ICON.moon : ICON.sun}</span>
        <span>${S.theme === "dark" ? "Nền tối" : "Nền sáng"}</span></button>
    </div>
  </header>`;
}

/* ── màn hình trò chuyện ─────────────────────────────────────────────────── */
function emptyState() {
  const q = QUOTES[S.qi % QUOTES.length];
  return `<div style="padding:46px 0 24px; animation:om-rise .45s ease both;">
    <svg width="52" height="52" viewBox="0 0 32 32" aria-hidden="true" style="margin-bottom:20px;">
      <circle cx="16" cy="16" r="14.2" fill="none" stroke="var(--line2)" stroke-width="1.2"></circle>
      <circle cx="16" cy="16" r="9.5" fill="none" stroke="var(--line2)" stroke-width="1"></circle>
      <rect x="16" y="8.2" width="11" height="11" rx="1.4" transform="rotate(45 16 8.2)" fill="var(--accent)" style="transform-origin:16px 16px; animation:om-float 3.4s ease-in-out infinite;"></rect>
    </svg>
    <div style="${SERIF} font-size:46px; line-height:1.08; letter-spacing:-0.01em;">Bạn muốn tạo <em style="color:var(--accent);">ảnh gì</em>?</div>
    <div style="margin-top:18px; max-width:540px; min-height:96px; display:flex; gap:14px;">
      <span style="flex:0 0 4px; width:4px; height:4px; margin-top:11px; background:var(--accent); opacity:.6; transform:rotate(45deg);"></span>
      <div style="flex:1; min-width:0;"><div key="${S.qi}" style="animation:om-rise .6s ease both;">
        <div style="${SERIF} font-style:italic; font-size:22px; line-height:1.45; color:var(--fg); text-wrap:pretty;">“${esc(q.t)}”</div>
        <div style="${LABEL} margin-top:10px;">${esc(q.a)}</div>
      </div></div>
    </div>
    <button data-act="openHelp" style="display:flex; align-items:center; gap:8px; margin-top:22px; padding:8px 14px 8px 12px; border:1px solid var(--line); border-radius:99px; background:var(--card); color:var(--fg2); font-size:12.5px; font-weight:500; cursor:pointer;" data-hover="${HOVER_ACCENT}">
      <span style="display:flex; align-items:center; line-height:0;">${ICON.help}</span><span>Lần đầu dùng? Xem hướng dẫn 4 bước</span></button>
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:26px;">
      ${SUGGESTIONS.map((s, i) => `<button data-act="useSuggestion" data-i="${i}" style="text-align:left; padding:15px 17px; border:1px solid var(--line); border-radius:15px; background:var(--card); color:var(--fg); cursor:pointer; display:flex; flex-direction:column; gap:7px;" data-hover="border-color:var(--accent); background:var(--accent-soft)">
        <span style="${MONO} font-size:9.5px; letter-spacing:.14em; text-transform:uppercase; color:var(--accent-ink);">${esc(s.tag)}</span>
        <span style="font-size:13.5px; line-height:1.5; color:var(--fg2);">${esc(s.text)}</span></button>`).join("")}
    </div>
  </div>`;
}

function userMsg(m) {
  const thumbs = (m.attach || []).map(id =>
    `<div style="width:64px; height:64px; border-radius:10px; overflow:hidden; border:1px solid var(--line); position:relative;">${imgTag(id)}</div>`).join("");
  return `<div style="display:flex; justify-content:flex-end;">
    <div style="max-width:78%; display:flex; flex-direction:column; align-items:flex-end; gap:7px;">
      ${thumbs ? `<div style="display:flex; gap:7px;">${thumbs}</div>` : ""}
      <div style="background:var(--chip); border:1px solid var(--line); border-radius:17px 17px 5px 17px; padding:12px 17px; font-size:14.5px; line-height:1.6;">${esc(m.text)}</div>
      <div style="${MONO} font-size:10px; letter-spacing:.08em; color:var(--muted);">${esc(m.meta || "")}</div>
    </div></div>`;
}

function aiMsg(m) {
  const n = (m.images || []).length;
  const cols = n === 1 ? "minmax(0, 420px)" : "1fr 1fr";
  const maxw = n === 1 ? "420px" : "568px";
  const caption = (m.kind === "edit"
    ? `Đã sửa xong — đây là ${n} phương án cho bạn chọn.`
    : `Xong rồi! Đây là ${n} ảnh theo yêu cầu của bạn.`) +
    " Chưa vừa ý thì bấm “Tạo lại bộ khác”, hoặc tả thêm để sửa.";

  const tiles = (m.images || []).map((id, i) =>
    `<button data-act="openLb" data-mid="${m.id}" data-img="${esc(id)}" style="position:relative; padding:0; border:1px solid var(--line); border-radius:15px; overflow:hidden; cursor:zoom-in; background:var(--tile-a); aspect-ratio:${m.ar}; display:block; width:100%;" data-hover="border-color:var(--accent)">
      ${imgTag(id)}
      <div style="position:absolute; left:9px; bottom:9px; padding:3px 9px; border-radius:7px; background:var(--scrim); color:#fff; ${MONO} font-size:9.5px; letter-spacing:.06em;">${m.kind === "edit" ? "bản sửa " : "ảnh "}${i + 1}</div>
    </button>`).join("");

  const act = (a, icon, txt, extra = "") =>
    `<button data-act="${a}" data-mid="${m.id}" ${extra} style="display:flex; align-items:center; gap:7px; padding:9px 14px; ${BTN_GHOST}" data-hover="${HOVER_ACCENT}"><span style="display:flex; align-items:center; line-height:0;">${icon}</span><span>${txt}</span></button>`;

  let editor = "";
  if (S.editFor === m.id) {
    editor = `<div style="margin-top:15px; border:1px solid var(--accent-line); background:var(--accent-soft); border-radius:17px; padding:16px 18px;">
      <div style="${SERIF} font-size:19px; margin-bottom:5px;">Bạn muốn sửa gì trên ảnh?</div>
      <div style="font-size:13px; color:var(--fg2); line-height:1.6;">Bấm một gợi ý bên dưới, hoặc tự viết ra. Ảnh cũ vẫn được giữ nguyên.</div>
      <div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:14px;">
        ${EDIT_CHIPS.map((l, i) => `<button data-act="editChip" data-i="${i}" style="padding:7px 13px; border:1px solid var(--accent-line); border-radius:99px; background:var(--card); font-size:12.5px; cursor:pointer; color:var(--accent-ink);" data-hover="background:var(--accent); color:#fff; border-color:var(--accent)">${esc(l)}</button>`).join("")}
      </div>
      <div style="display:flex; gap:8px; margin-top:14px;">
        <input id="editInput" value="${esc(S.editText)}" placeholder="Ví dụ: đổi nền thành bãi biển lúc chiều" style="flex:1; min-width:0; padding:11px 15px; border:1px solid var(--accent-line); border-radius:11px; background:var(--card); color:var(--fg); font-size:13.5px; outline:none;">
        <button data-act="submitEdit" data-mid="${m.id}" style="padding:11px 19px; border:0; border-radius:11px; background:var(--accent); color:#fff; font-size:13.5px; font-weight:600; cursor:pointer; white-space:nowrap;" data-hover="background:var(--accent-h)">Sửa ảnh</button>
        <button data-act="cancelEdit" style="padding:11px 15px; border:1px solid var(--line); border-radius:11px; background:var(--card); font-size:13.5px; color:var(--muted); cursor:pointer;" data-hover="color:var(--fg)">Bỏ qua</button>
      </div></div>`;
  }

  return `<div style="display:flex; gap:15px;">${ICON.mark}
    <div style="min-width:0; flex:1;">
      <div style="font-size:14px; color:var(--fg2); line-height:1.6; margin-bottom:14px; text-wrap:pretty;">${esc(caption)}</div>
      <div style="display:grid; gap:11px; grid-template-columns:${cols}; max-width:${maxw};">${tiles}</div>
      <div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:15px;">
        ${act("editMsg", ICON.pencil, "Sửa ảnh này")}
        ${act("againMsg", ICON.redo, "Tạo lại bộ khác")}
        ${act("dlMsg", ICON.download, "Tải về", `data-img="${esc(m.images[0] || "")}"`)}
      </div>${editor}
    </div></div>`;
}

function generatingBlock() {
  const g = S.gen;
  const cols = g.count === 1 ? "minmax(0, 420px)" : "1fr 1fr";
  const tiles = Array.from({ length: g.count }, (_, i) => {
    const id = g.images[i];
    return `<div style="position:relative; overflow:hidden; border-radius:15px; border:1px solid var(--line); background:var(--tile-a); aspect-ratio:${g.ar};">
      ${id ? imgTag(id) : `${tile("", g.ar, " animation:om-pulse 2s ease-in-out infinite;")}
        <div style="position:absolute; inset:0; background:linear-gradient(100deg, transparent 20%, var(--sheen) 50%, transparent 80%); animation:om-shimmer 1.7s linear infinite;"></div>`}
    </div>`;
  }).join("");
  return `<div style="display:flex; gap:15px; margin-bottom:28px;">
    <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden="true" style="flex:0 0 30px; margin-top:2px; animation:om-pulse 1.5s ease-in-out infinite;">
      <circle cx="16" cy="16" r="14.2" fill="none" stroke="var(--line2)" stroke-width="1.3"></circle>
      <rect x="16" y="8.2" width="11" height="11" rx="1.4" transform="rotate(45 16 8.2)" fill="var(--accent)"></rect></svg>
    <div style="flex:1; min-width:0;">
      <div style="display:flex; align-items:center; gap:11px; margin-bottom:13px;">
        <div style="width:14px; height:14px; border-radius:50%; border:2px solid var(--accent-line); border-top-color:var(--accent); animation:om-spin .8s linear infinite;"></div>
        <div style="font-size:14px; font-weight:500;">${esc(g.step)}</div>
        <div style="${MONO} font-size:11.5px; color:var(--muted);">${g.pct}%</div>
      </div>
      <div style="height:4px; border-radius:99px; background:var(--line); overflow:hidden; max-width:568px;">
        <div style="height:100%; border-radius:99px; background:var(--accent); transition:width .35s ease; width:${g.pct}%;"></div></div>
      <div style="display:grid; gap:11px; grid-template-columns:${cols}; max-width:568px; margin-top:15px;">${tiles}</div>
      <div style="font-size:12.5px; color:var(--muted); margin-top:13px; line-height:1.55;">Ảnh đầu tiên thường lâu hơn vì phải nạp model 20B vào GPU. Bạn có thể ngồi chờ hoặc mở tab khác.</div>
    </div></div>`;
}

function composer() {
  const chip = (o, label, act, data, mono) =>
    `<button data-act="${act}" ${data} style="${mono ? "min-width:32px; padding:6px 11px; " + MONO + " font-size:12px;" : "padding:6px 13px; font-size:12.5px;"} border-radius:99px; cursor:pointer; border:1px solid ${o.bd}; background:${o.bg}; color:${o.fg};">${esc(label)}</button>`;

  const adv = S.adv ? `<div style="display:flex; flex-direction:column; gap:9px; padding:12px 14px; border:1px solid var(--line); border-radius:14px; background:var(--chip);">
      <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
        <span style="${MONO} font-size:9.5px; letter-spacing:.14em; text-transform:uppercase; color:var(--muted); width:76px;">phong cách</span>
        ${STYLES.map(s => chip(chipOf(S.style === s), s, "pickStyle", `data-v="${esc(s)}"`)).join("")}
      </div>
      <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
        <span style="${MONO} font-size:9.5px; letter-spacing:.14em; text-transform:uppercase; color:var(--muted); width:76px;">khung ảnh</span>
        ${RATIOS.map(r => chip(chipOf(S.ratio === r.label), r.label, "pickRatio", `data-v="${esc(r.label)}"`)).join("")}
        <span style="${MONO} font-size:9.5px; letter-spacing:.14em; text-transform:uppercase; color:var(--muted); margin-left:12px;">số ảnh</span>
        ${[1, 2, 4].map(n => chip(chipOf(S.count === n), String(n), "pickCount", `data-v="${n}"`, true)).join("")}
      </div></div>` : "";

  const attachStrip = S.attach.length ? `<div style="display:flex; gap:8px; margin-bottom:9px; flex-wrap:wrap;">
    ${S.attach.map((a, i) => `<div style="position:relative; width:56px; height:56px; border-radius:10px; overflow:hidden; border:1px solid var(--line);">
      ${imgTag(a.id)}
      <button data-act="unattach" data-i="${i}" title="Bỏ ảnh này" style="position:absolute; right:3px; top:3px; width:18px; height:18px; border:0; border-radius:50%; background:var(--scrim); color:#fff; cursor:pointer; display:flex; align-items:center; justify-content:center; padding:0;">${ICON.x}</button>
    </div>`).join("")}
    <div style="align-self:center; font-size:12px; color:var(--muted);">${S.attach.length >= 2 ? "2 ảnh → ghép lại" : "1 ảnh → sửa ảnh này"}</div></div>` : "";

  const sendBg = S.input.trim() && !S.gen ? "var(--accent)" : "var(--line2)";
  return `<div style="flex:0 0 auto; padding:4px 30px 18px;">
    <div style="max-width:768px; margin:0 auto;">
      <div style="border:1px solid var(--line); border-radius:18px; background:var(--card); box-shadow:var(--shadow); padding:11px 13px 10px;">
        ${attachStrip}
        <textarea id="mainInput" rows="2" placeholder="Tả bằng lời ảnh bạn muốn — ví dụ: bó hoa hướng dương trên bàn ăn, nắng buổi sáng" style="width:100%; border:0; outline:none; resize:none; overflow:hidden; font-size:14.5px; line-height:1.55; background:transparent; color:var(--fg); min-height:52px; max-height:180px; padding:2px 4px;">${esc(S.input)}</textarea>
        <div style="display:flex; align-items:flex-end; gap:10px; margin-top:2px;">
          <div style="flex:1; min-width:0; display:flex; flex-direction:column; gap:11px;">
            ${adv}
            <div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap;">
              <button data-act="attach" title="Đính kèm ảnh để sửa hoặc ghép" style="display:flex; align-items:center; gap:7px; padding:6px 12px; border-radius:99px; border:1px solid ${S.attach.length ? "var(--accent)" : "var(--line)"}; background:${S.attach.length ? "var(--accent-soft)" : "var(--card)"}; color:${S.attach.length ? "var(--accent-ink)" : "var(--fg2)"}; font-size:12.5px; font-weight:500; cursor:pointer;" data-hover="border-color:var(--accent)">
                <span style="display:flex; align-items:center; line-height:0;">${ICON.clip}</span><span>Đính kèm ảnh</span></button>
              <button data-act="toggleAdv" style="display:flex; align-items:center; gap:7px; padding:6px 12px; border-radius:99px; border:1px solid ${S.adv ? "var(--accent)" : "var(--line)"}; background:${S.adv ? "var(--accent-soft)" : "var(--card)"}; color:${S.adv ? "var(--accent-ink)" : "var(--fg2)"}; font-size:12.5px; font-weight:500; white-space:nowrap; cursor:pointer;" data-hover="border-color:var(--accent)">
                <span style="display:flex; align-items:center; line-height:0;">${ICON.gear}</span><span>Tùy chỉnh nâng cao</span>
                <span style="display:flex; align-items:center; line-height:0; opacity:.75;">${S.adv ? ICON.caretUp : ICON.caretDown}</span></button>
              <div style="font-size:11.5px; color:var(--muted);">Nhấn Enter để tạo ảnh · Shift + Enter để xuống dòng</div>
            </div>
          </div>
          <button data-act="send" title="Tạo ảnh" style="flex:0 0 auto; width:44px; height:44px; border-radius:50%; border:0; background:${sendBg}; color:#fff; cursor:pointer; display:flex; align-items:center; justify-content:center;" data-hover="opacity:.86">${ICON.send}</button>
        </div>
      </div>
      <input type="file" id="filePicker" accept="image/*" multiple hidden>
    </div></div>`;
}

function chatView() {
  // Tin nhắn AI chưa có ảnh nào = đang chờ hoặc đã hỏng. Khối "đang vẽ" ở dưới lo
  // phần hiển thị rồi, nên đừng vẽ thêm một bong bóng rỗng ghi "đây là 0 ảnh".
  const list = msgs().filter(m => m.role !== "ai" || (m.images || []).length);
  const body = list.map(m =>
    `<div data-msg="${m.id}" style="margin-bottom:28px; animation:om-rise .35s ease both;">${m.role === "user" ? userMsg(m) : aiMsg(m)}</div>`).join("");
  return `<div style="flex:1; min-height:0; display:flex; flex-direction:column;">
    <div id="scroller" style="flex:1; min-height:0; overflow-y:auto; scroll-behavior:smooth;">
      <div style="max-width:768px; margin:0 auto; padding:30px 30px 8px;">
        ${!list.length && !S.gen ? emptyState() : ""}
        ${body}
        ${S.gen ? generatingBlock() : ""}
      </div>
    </div>
    ${composer()}
  </div>`;
}

/* ── thư viện ảnh ────────────────────────────────────────────────────────── */
function allImages() {
  return S.galleryItems || [];
}

function galleryView() {
  const items = allImages();   // /api/gallery đã lọc theo S.filter và sắp mới nhất trước
  const cards = items.map(g => `<div style="display:flex; flex-direction:column; gap:9px;">
      <button data-act="openLb" data-mid="${g.mid}" data-img="${esc(g.id)}" style="position:relative; width:100%; padding:0; border:1px solid var(--line); border-radius:15px; overflow:hidden; background:var(--tile-a); cursor:zoom-in; aspect-ratio:${g.ar}; display:block;" data-hover="border-color:var(--accent)">
        ${imgTag(g.id)}
        <div style="position:absolute; left:9px; top:9px; padding:3px 9px; border-radius:7px; background:var(--scrim); color:#fff; ${MONO} font-size:9.5px; letter-spacing:.06em;">${esc(g.badge)}</div>
      </button>
      <div style="font-size:12.5px; color:var(--fg2); line-height:1.5; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;">${esc(g.prompt)}</div>
      <div style="display:flex; align-items:center; gap:8px;">
        <div style="${MONO} font-size:9.5px; letter-spacing:.08em; color:var(--muted);">${esc(whenLabel(g.ts) + " · " + (g.style || ""))}</div>
        <button data-act="delImg" data-img="${esc(g.id)}" title="Xoá ảnh này" style="margin-left:auto; width:22px; height:22px; border:0; border-radius:6px; background:transparent; color:var(--line2); cursor:pointer; display:flex; align-items:center; justify-content:center;" data-hover="color:var(--accent)">${ICON.x}</button>
      </div>
    </div>`).join("");

  return `<div style="flex:1; min-height:0; overflow-y:auto; padding:28px 30px 44px;">
    <div style="max-width:1180px; margin:0 auto;">
      <div style="display:flex; align-items:flex-end; gap:18px; flex-wrap:wrap; margin-bottom:24px;">
        <div>
          <div style="${SERIF} font-size:34px; line-height:1.15;">Thư viện ảnh của bạn</div>
          <div style="font-size:13.5px; color:var(--fg2); margin-top:8px;">Tất cả ảnh đã tạo đều lưu ở đây. Bấm vào ảnh để xem lớn, tải về hoặc sửa tiếp.</div>
        </div>
        <div style="margin-left:auto; display:flex; gap:8px;">
          ${FILTERS.map(f => { const o = chipOf(S.filter === f); return `<button data-act="pickFilter" data-v="${esc(f)}" style="padding:8px 15px; border-radius:99px; font-size:13px; cursor:pointer; border:1px solid ${o.bd}; background:${o.bg}; color:${o.fg};">${esc(f)}</button>`; }).join("")}
        </div>
      </div>
      ${items.length ? `<div style="display:grid; gap:18px; grid-template-columns:repeat(4, minmax(0, 1fr));">${cards}</div>`
        : `<div style="padding:70px 0; text-align:center; color:var(--muted); font-size:14px;">Chưa có ảnh nào. Quay lại tab Trò chuyện và tả ảnh bạn muốn.</div>`}
    </div></div>`;
}

/* ── lớp phủ ─────────────────────────────────────────────────────────────── */
function helpModal() {
  return `<div data-act="closeHelp" style="position:fixed; inset:0; z-index:60; background:var(--scrim); backdrop-filter:blur(7px); display:flex; align-items:center; justify-content:center; padding:44px; animation:om-rise .22s ease both;">
    <div data-stop="1" style="width:100%; max-width:620px; max-height:100%; overflow-y:auto; background:var(--bg); border:1px solid var(--line); border-radius:22px; box-shadow:0 28px 70px rgba(0,0,0,.35); padding:32px 34px 28px;">
      <div style="display:flex; align-items:flex-start; gap:16px;">
        <div style="min-width:0;">
          <div style="${LABEL}">hướng dẫn nhanh</div>
          <div style="${SERIF} font-size:32px; line-height:1.2; margin-top:8px;">Tạo ảnh trong <em style="color:var(--accent);">bốn bước</em></div>
        </div>
        <button data-act="closeHelp" style="margin-left:auto; flex:0 0 31px; width:31px; height:31px; display:flex; align-items:center; justify-content:center; border-radius:50%; border:1px solid var(--line); background:var(--card); color:var(--muted); cursor:pointer;" data-hover="color:var(--fg); border-color:var(--line2)">${ICON.xBig}</button>
      </div>
      <div style="display:flex; flex-direction:column; margin-top:24px;">
        ${HELP.map(h => `<div style="display:flex; gap:16px; padding:16px 0; border-top:1px solid var(--line);">
          <div style="flex:0 0 30px; display:flex; justify-content:center; padding-top:3px;">
            <div style="width:25px; height:25px; display:flex; align-items:center; justify-content:center; background:var(--accent-soft); border:1px solid var(--accent-line); transform:rotate(45deg);">
              <span style="${MONO} font-size:11px; color:var(--accent-ink); transform:rotate(-45deg);">${h.n}</span></div></div>
          <div style="flex:1; min-width:0;">
            <div style="font-size:14.5px; font-weight:600;">${esc(h.title)}</div>
            <div style="font-size:13.5px; color:var(--fg2); line-height:1.7; margin-top:5px; text-wrap:pretty;">${esc(h.body)}</div>
          </div></div>`).join("")}
      </div>
      <div style="display:flex; gap:12px; align-items:flex-start; margin-top:20px; padding:14px 16px; border:1px solid var(--accent-line); background:var(--accent-soft); border-radius:14px;">
        <span style="flex:0 0 4px; width:4px; height:4px; margin-top:8px; background:var(--accent); transform:rotate(45deg);"></span>
        <div style="font-size:13px; color:var(--fg2); line-height:1.7;">Mẹo: tả theo thứ tự <strong style="color:var(--fg); font-weight:600;">vật thể → bối cảnh → ánh sáng</strong>. Ví dụ: “bó hoa hướng dương / trên bàn gỗ cạnh cửa sổ / nắng sớm dịu”.</div>
      </div>
      <button data-act="closeHelp" style="width:100%; margin-top:18px; padding:13px; border:0; border-radius:13px; background:var(--accent); color:#fff; font-size:14px; font-weight:600; cursor:pointer;" data-hover="background:var(--accent-h)">Tôi đã hiểu, bắt đầu tạo ảnh</button>
    </div></div>`;
}

function lightbox() {
  const lb = S.lightbox;
  const sendBg = (S.lbText || "").trim() ? "var(--accent)" : "var(--line2)";
  return `<div data-act="closeLb" style="position:fixed; inset:0; z-index:50; background:var(--scrim); backdrop-filter:blur(7px); display:flex; align-items:center; justify-content:center; padding:44px; animation:om-rise .22s ease both;">
    <div data-stop="1" style="display:flex; background:var(--bg); border:1px solid var(--line); border-radius:22px; overflow:hidden; max-width:1180px; width:100%; max-height:100%; box-shadow:0 28px 70px rgba(0,0,0,.35);">
      <div style="flex:1; min-width:0; background:var(--panel); display:flex; align-items:center; justify-content:center; padding:34px;">
        <div style="position:relative; width:100%; max-width:660px; aspect-ratio:${lb.ar}; border-radius:13px; overflow:hidden; border:1px solid var(--line);">${imgTag(lb.id)}</div>
      </div>
      <div style="flex:0 0 328px; padding:26px; display:flex; flex-direction:column; gap:18px; border-left:1px solid var(--line); overflow-y:auto;">
        <div style="display:flex; align-items:center;">
          <div style="${SERIF} font-size:22px;">Chi tiết ảnh</div>
          <button data-act="closeLb" style="margin-left:auto; width:31px; height:31px; border-radius:50%; border:1px solid var(--line); background:var(--card); color:var(--muted); cursor:pointer;" data-hover="color:var(--fg); border-color:var(--line2)">${ICON.xBig}</button>
        </div>
        <div>
          <div style="${MONO} font-size:9.5px; letter-spacing:.14em; text-transform:uppercase; color:var(--muted); margin-bottom:8px;">yêu cầu của bạn</div>
          <div style="font-size:13.5px; line-height:1.65; color:var(--fg); text-wrap:pretty;">${esc(lb.prompt)}</div>
        </div>
        <div style="display:flex; gap:8px; flex-wrap:wrap;">
          <span style="padding:5px 11px; border-radius:99px; background:var(--chip); border:1px solid var(--line); font-size:11.5px; color:var(--fg2);">${esc(lb.badge)}</span>
          <span style="padding:5px 11px; border-radius:99px; background:var(--chip); border:1px solid var(--line); font-size:11.5px; color:var(--fg2);">${esc(lb.when)}</span>
        </div>
        <div style="border-top:1px solid var(--line); padding-top:18px; display:flex; flex-direction:column; gap:11px;">
          <div style="${SERIF} font-size:19px; line-height:1.25;">Muốn sửa gì trên ảnh này?</div>
          <div style="display:flex; flex-wrap:wrap; gap:7px;">
            ${EDIT_CHIPS.slice(0, 4).map((l, i) => `<button data-act="lbChip" data-i="${i}" style="padding:6px 11px; border:1px solid var(--line); border-radius:99px; background:var(--card); font-size:12px; cursor:pointer; color:var(--fg2);" data-hover="border-color:var(--accent); color:var(--accent-ink); background:var(--accent-soft)">${esc(l)}</button>`).join("")}
          </div>
          <textarea id="lbInput" rows="2" placeholder="Viết yêu cầu của bạn — ví dụ: bỏ chiếc ly phía sau, làm nền sáng hơn" style="width:100%; border:1px solid var(--line); border-radius:12px; background:var(--card); color:var(--fg); padding:11px 13px; font-size:13px; line-height:1.55; resize:none; outline:none; min-height:64px;">${esc(S.lbText)}</textarea>
          <button data-act="submitLb" style="width:100%; padding:12px; border:0; border-radius:12px; background:${sendBg}; color:#fff; font-size:13.5px; font-weight:600; cursor:pointer;" data-hover="opacity:.9">Sửa ảnh theo yêu cầu</button>
        </div>
        <div style="margin-top:auto; display:flex; gap:9px;">
          <button data-act="moreLike" style="flex:1; padding:11px; ${BTN_GHOST} font-size:12.5px;" data-hover="${HOVER_ACCENT}">Ảnh tương tự</button>
          <button data-act="dlLb" style="flex:1; padding:11px; ${BTN_GHOST} font-size:12.5px;" data-hover="${HOVER_ACCENT}">Tải về máy</button>
        </div>
      </div></div></div>`;
}

function toastEl() {
  return `<div style="position:fixed; left:50%; top:78px; transform:translateX(-50%); z-index:80; max-width:640px; padding:12px 18px; border-radius:13px; border:1px solid var(--accent-line); background:var(--accent-soft); color:var(--accent-ink); font-size:13.5px; box-shadow:var(--shadow); animation:om-rise .2s ease both;">${esc(S.toast)}</div>`;
}

/* ── render ──────────────────────────────────────────────────────────────── */
function render() {
  const root = document.getElementById("root");
  const sc = document.getElementById("scroller");
  const keepTop = sc ? sc.scrollTop : null;
  const atBottom = sc ? (sc.scrollHeight - sc.scrollTop - sc.clientHeight < 60) : true;

  root.innerHTML = `<div data-theme="${S.theme}" style="display:flex; height:100vh; width:100%; overflow:hidden; background:var(--bg); color:var(--fg); font-family:'Be Vietnam Pro', 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size:15px; -webkit-font-smoothing:antialiased;">
    ${S.rail ? railOpen() : railClosed()}
    <main style="flex:1; min-width:0; height:100%; display:flex; flex-direction:column; background:var(--bg);">
      ${header()}
      ${S.view === "chat" ? chatView() : galleryView()}
    </main>
    ${S.help ? helpModal() : ""}
    ${S.lightbox ? lightbox() : ""}
    ${S.toast ? toastEl() : ""}
  </div>`;
  document.documentElement.setAttribute("data-theme", S.theme);

  const sc2 = document.getElementById("scroller");
  if (sc2 && keepTop !== null) sc2.scrollTop = atBottom ? sc2.scrollHeight : keepTop;

  const ta = document.getElementById("mainInput");
  if (ta) { autoGrow(ta); if (document.activeElement === document.body) ta.focus(); }
}

function autoGrow(el) {
  el.style.height = "auto";
  el.style.height = Math.min(180, Math.max(52, el.scrollHeight)) + "px";
}

function scrollBottom() {
  requestAnimationFrame(() => {
    const sc = document.getElementById("scroller");
    if (sc) sc.scrollTop = sc.scrollHeight;
  });
}

/* ── hover: thiết kế dùng thuộc tính style-hover, ở đây là data-hover ────── */
document.addEventListener("mouseover", e => {
  const el = e.target.closest("[data-hover]");
  if (!el || el._hoverOn) return;
  el._hoverOn = true;
  el._styleBefore = el.getAttribute("style") || "";
  el.setAttribute("style", el._styleBefore + ";" + el.getAttribute("data-hover"));
});
document.addEventListener("mouseout", e => {
  const el = e.target.closest("[data-hover]");
  if (!el || !el._hoverOn) return;
  if (el.contains(e.relatedTarget)) return;
  el._hoverOn = false;
  el.setAttribute("style", el._styleBefore);
});

/* ── ảnh đang được thao tác trong một tin nhắn ───────────────────────────── */
function msgById(id) {
  for (const cid of Object.keys(S.messages)) {
    const m = (S.messages[cid] || []).find(x => x.id === id);
    if (m) return m;
  }
  return null;
}

function download(id) {
  const a = document.createElement("a");
  a.href = "/api/image/" + id + "?download=1";
  a.download = id;
  document.body.appendChild(a); a.click(); a.remove();
}

/* ── sự kiện ─────────────────────────────────────────────────────────────── */
const ACTS = {
  toggleRail: () => { S.rail = !S.rail; render(); },
  newChat: () => newChat(),
  openChat: el => { S.activeChat = el.dataset.id; S.view = "chat"; S.editFor = null; save(); render(); },
  delChat: el => removeChat(el.dataset.id),
  goChat: () => { S.view = "chat"; render(); },
  goGallery: () => { S.view = "gallery"; render(); },
  openHelp: () => { S.help = true; render(); },
  closeHelp: () => { S.help = false; render(); },
  toggleTheme: () => { S.theme = S.theme === "dark" ? "light" : "dark"; save(); render(); },
  toggleAdv: () => { S.adv = !S.adv; render(); },
  pickStyle: el => { S.style = el.dataset.v; save(); render(); },
  pickRatio: el => { S.ratio = el.dataset.v; save(); render(); },
  pickCount: el => { S.count = parseInt(el.dataset.v, 10); save(); render(); },
  pickFilter: async el => { S.filter = el.dataset.v; await loadGallery(); render(); },
  delImg: async el => {
    await api("/api/image/" + el.dataset.img, { method: "DELETE" });
    await loadGallery();
    if (S.activeChat) await loadMessages(S.activeChat);
    render();
  },
  useSuggestion: el => { S.input = SUGGESTIONS[+el.dataset.i].text; render(); },
  send: () => submitMain(),

  attach: () => document.getElementById("filePicker")?.click(),
  unattach: el => { S.attach.splice(+el.dataset.i, 1); render(); },

  editMsg: el => { S.editFor = el.dataset.mid; S.editText = ""; render(); },
  cancelEdit: () => { S.editFor = null; S.editText = ""; render(); },
  editChip: el => { S.editText = EDIT_CHIPS[+el.dataset.i]; render(); },
  submitEdit: el => {
    const m = msgById(el.dataset.mid);
    const txt = (document.getElementById("editInput")?.value || S.editText).trim();
    if (!txt || !m) return;
    S.editText = "";
    startGen(txt, "edit", m.images[0]);
  },
  againMsg: el => { const m = msgById(el.dataset.mid); if (m) startGen(m.prompt, m.kind || "new", m.kind === "edit" ? m.images[0] : null); },
  dlMsg: el => download(el.dataset.img),

  openLb: el => {
    const id = el.dataset.img;
    const m = msgById(el.dataset.mid) ||
              (S.galleryItems || []).find(g => g.id === id);
    if (!m) return;
    S.lightbox = { id, mid: el.dataset.mid, ar: m.ar, prompt: m.prompt,
                   badge: (m.style || "") + " · " + (m.kind === "edit" ? "bản sửa" : "ảnh mới"),
                   when: whenLabel(m.ts) };
    S.lbText = ""; render();
  },
  closeLb: () => { S.lightbox = null; S.lbText = ""; render(); },
  lbChip: el => { S.lbText = EDIT_CHIPS[+el.dataset.i]; render(); },
  submitLb: () => {
    const txt = (document.getElementById("lbInput")?.value || S.lbText).trim();
    if (!txt || !S.lightbox) return;
    const base = S.lightbox.id;
    S.lightbox = null; S.lbText = ""; S.view = "chat";
    startGen(txt, "edit", base);
  },
  moreLike: () => { const p = S.lightbox.prompt; S.lightbox = null; S.view = "chat"; startGen(p, "new"); },
  dlLb: () => download(S.lightbox.id),
};

document.addEventListener("click", e => {
  const stop = e.target.closest("[data-stop]");
  const el = e.target.closest("[data-act]");
  if (!el) return;
  // bấm vào ruột hộp thoại thì đừng đóng lớp phủ
  if (stop && stop.contains(el) === false) return;
  if (stop && (el.dataset.act === "closeLb" || el.dataset.act === "closeHelp") && el === stop) return;
  const fn = ACTS[el.dataset.act];
  if (fn) { e.preventDefault(); fn(el); }
});

function submitMain() {
  const ta = document.getElementById("mainInput");
  const txt = (ta ? ta.value : S.input).trim();
  if (!txt) return;
  S.input = txt;
  startGen(txt, S.attach.length ? "edit" : "new", null);
}

document.addEventListener("input", e => {
  if (e.target.id === "mainInput") { S.input = e.target.value; autoGrow(e.target); syncSend(); }
  if (e.target.id === "editInput") S.editText = e.target.value;
  if (e.target.id === "lbInput") S.lbText = e.target.value;
});

/* Đổi màu nút gửi mà không render lại — render lại sẽ cướp con trỏ đang gõ. */
function syncSend() {
  const b = document.querySelector('[data-act="send"]');
  if (b) b.style.background = S.input.trim() && !S.gen ? "var(--accent)" : "var(--line2)";
}

document.addEventListener("keydown", e => {
  if (e.target.id === "mainInput" && e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submitMain(); }
  if (e.target.id === "editInput" && e.key === "Enter") {
    e.preventDefault();
    const mid = e.target.closest("[data-msg]")?.dataset.msg;
    if (mid) ACTS.submitEdit({ dataset: { mid } });
  }
  if (e.target.id === "lbInput" && e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ACTS.submitLb(); }
  if (e.key === "Escape") {
    if (S.lightbox) ACTS.closeLb();
    else if (S.help) ACTS.closeHelp();
  }
});

document.addEventListener("change", async e => {
  if (e.target.id !== "filePicker") return;
  const files = [...e.target.files].slice(0, 2 - S.attach.length);
  for (const f of files) {
    try { S.attach.push({ id: await uploadFile(f) }); }
    catch (err) { toast("❌ " + err.message); }
  }
  render();
});

/* ── khởi động ───────────────────────────────────────────────────────────── */
boot();
setInterval(() => { if (!msgs().length && !S.gen && S.view === "chat") { S.qi++; render(); } }, 7000);

fetch("/api/health").then(r => r.json()).then(d => {
  if (!d.comfy) toast("⚠️ Chưa kết nối được ComfyUI ở cổng 18188 — hãy khởi động ComfyUI rồi tải lại trang.");
}).catch(() => toast("⚠️ Không gọi được backend."));
