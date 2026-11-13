#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地 PDF 页面尺寸统一工具（Python 标准库 + PyMuPDF）。"""

from __future__ import annotations

import io
import json
import os
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote
from zipfile import ZipFile, ZIP_DEFLATED
import secrets
import threading
import webbrowser

try:
    import fitz  # PyMuPDF
except ImportError as exc:
    raise SystemExit("缺少 PyMuPDF：请通过 启动PDF工具.command 启动，或执行 python3 -m pip install pymupdf") from exc

A4_PORTRAIT = (595.2756, 841.8898)
MAX_TOTAL_UPLOAD = 160 * 1024 * 1024  # 160 MB
MAX_FILES = 30
TOKEN = secrets.token_urlsafe(32)

PAGE_HTML = r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>PDF 页面统一工具 · 免费本地版</title>
<style>
:root {
  color-scheme: light;
  font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", sans-serif;
  color: #3e2826;
  background: #f1d9d2;
  accent-color: #8d483e;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  min-height: 100vh;
  padding: clamp(28px, 7vh, 76px) 20px 32px;
  background:
    radial-gradient(ellipse at 8% 5%, #fff6eb 0, transparent 54%),
    radial-gradient(ellipse at 95% 20%, #ecc5bc 0, transparent 57%),
    linear-gradient(135deg, #f2d5cd, #f9eeea 75%);
}
main { position: relative; max-width: 740px; margin: auto; }
.ambient {
  position: fixed;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}
.orb {
  position: absolute;
  top: -9rem;
  left: 46%;
  width: clamp(24rem, 62vw, 52rem);
  aspect-ratio: 1;
  border-radius: 46% 54% 61% 39%;
  background:
    radial-gradient(ellipse at 32% 31%, #fff1e5 0, transparent 52%),
    radial-gradient(ellipse at 65% 49%, #d4988c 0, transparent 62%),
    radial-gradient(ellipse at 40% 67%, #e6aaa3 0, transparent 65%);
  opacity: .52;
  filter: blur(42px);
  animation: orb-drift 19s ease-in-out infinite alternate;
}
@keyframes orb-drift {
  from { transform: translate(-8%, 0) rotate(-18deg) scale(.94); }
  to { transform: translate(12%, 18%) rotate(24deg) scale(1.13); }
}
h1 span { display: inline-block; animation: title-pop .52s both; }
h1 span + span { animation-delay: .08s; }
@keyframes title-pop {
  0% { opacity: 0; transform: translateY(5px) scale(.93); }
  74% { opacity: 1; transform: scale(1.018); }
  100% { transform: scale(1); }
}
h1 { margin: 0 0 8px; font-size: clamp(30px, 5vw, 44px); letter-spacing: -.04em; font-weight: 650; }
p { margin: 0 0 26px; line-height: 1.6; color: #674944; }
.panel {
  padding: clamp(18px, 4vw, 32px);
  border: 1px solid #fff9;
  border-radius: 28px;
  background: #fff7f2e8;
  box-shadow: inset 0 1px 0 #fff9, 0 20px 60px #6e33241e;
}
@supports (backdrop-filter: blur(24px)) or (-webkit-backdrop-filter: blur(24px)) {
  .panel {
    background: linear-gradient(145deg, #fffaf6b8, #fff5f18c);
    -webkit-backdrop-filter: blur(24px);
    backdrop-filter: blur(24px);
  }
}
h2 { font-size: 16px; margin: 0 0 12px; }
small, .tip { color: #694c47; }
.drop {
  display: block;
  border: 1px dashed #aa746a;
  border-radius: 18px;
  padding: 24px 16px;
  text-align: center;
  background: #fffbf869;
  cursor: pointer;
}
.drop:hover, .drop.hover, .drop:focus-within { border-color: #8d483e; background: #fff8f3df; }
.drop .tip { margin-top: 5px; }
input[type=file] { width: 100%; max-width: 270px; margin-top: 13px; color: inherit; font: inherit; font-size: 13px; }
input::file-selector-button, select {
  border: 1px solid #a6746966;
  border-radius: 9px;
  padding: 8px 11px;
  background: #fff8f3;
  color: #563630;
  font: inherit;
  cursor: pointer;
}
.options { position: relative; display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.option {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 14px 10px;
  border: 1px solid #ad796b55;
  border-radius: 14px;
  background: #fffaf674;
  font-size: 14px;
  line-height: 1.6;
  cursor: pointer;
}
.option:hover { background: #fff9f5; }
.option:has(input:checked) { border-color: #a4675c; background: #f5d9d1; }
.choice-highlight {
  position: absolute;
  top: 0;
  left: 0;
  border: 1px solid #a4675c;
  border-radius: 14px;
  background: #f5d9d1;
  pointer-events: none;
}
.options.has-highlight .option { background: transparent; }
.options.has-highlight .option:hover:not(:has(input:checked)) { background: #fff9f57a; }
.options.has-highlight .option:has(input:checked) { border-color: transparent; }
@media (prefers-reduced-motion: reduce) {
  .orb, h1 span { animation: none; }
}
input[type=radio] { margin: 4px 0 0; }
.row { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; font-size: 14px; }
button {
  border: 1px solid #783b32;
  border-radius: 13px;
  padding: 12px 20px;
  background: linear-gradient(#a55c4f, #864238);
  box-shadow: inset 0 1px 0 #fff3, 0 4px 12px #773a3029;
  color: white;
  font: inherit;
  font-weight: 650;
  cursor: pointer;
}
button:hover:not(:disabled) { background: #783b32; }
button:disabled { opacity: .65; cursor: wait; }
:focus-visible { outline: 2px solid #803e35; outline-offset: 3px; }
.status { margin-top: 14px; font-size: 14px; white-space: pre-wrap; line-height: 1.6; }
.status:empty { display: none; }
#selection { overflow-wrap: anywhere; font-size: 13px; }
.success { color: #205c42; }
.error { color: #962c30; }
.foot { font-size: 12px; line-height: 1.65; color: #694c47; margin: 16px 4px 0; }
@media (max-width: 570px) { .options { grid-template-columns: 1fr; } }
</style></head>
<body><div class="ambient" aria-hidden="true"><div class="orb"></div></div><main>
<h1><span>PDF</span> <span>页面统一工具</span></h1>
<p>把 PDF 页面统一为 A4，保持内容比例。</p>
<div class="panel">
<h2>选择 PDF</h2>
<label class="drop" id="drop"><strong>拖入 PDF 文件到这里</strong><div class="tip">或点击下方选择文件（最多 30 个）</div>
<input id="files" type="file" accept=".pdf,application/pdf" multiple></label>
<div id="selection" class="tip" style="margin-top:9px">尚未选择文件</div>
<h2 style="margin-top:25px">页面尺寸</h2>
<div class="options">
<div class="choice-highlight" aria-hidden="true" hidden></div>
<label class="option"><input type="radio" name="mode" value="portrait" checked><span><strong>全部 A4 竖版</strong><br><small>210 × 297 mm</small></span></label>
<label class="option"><input type="radio" name="mode" value="landscape"><span><strong>全部 A4 横版</strong><br><small>297 × 210 mm</small></span></label>
<label class="option"><input type="radio" name="mode" value="preserve"><span><strong>按原方向转为 A4</strong><br><small>横竖混排时仍有两种宽高</small></span></label>
</div>
<div class="row" style="margin-top:22px"><label for="margin"><strong>页面留白：</strong></label><select id="margin"><option value="0">0 mm</option><option value="5" selected>5 mm（推荐）</option><option value="10">10 mm</option><option value="15">15 mm</option></select></div>
<div class="row" style="margin-top:24px"><button type="button" id="go">开始处理并下载</button><span class="tip">原文件会保留</span></div>
<div class="status" id="status" role="status" aria-live="polite"></div>
</div>
<div class="foot">文件在本机处理。多个文件会打包成 ZIP。<br>处理含交互表单、电子签章或特殊注释的 PDF 时，请检查输出文件。</div>
</main>
<script>
const TOKEN = __TOKEN__;
const fileInput = document.getElementById('files');
const selection = document.getElementById('selection');
const status = document.getElementById('status');
const go = document.getElementById('go');
const drop = document.getElementById('drop');
const options = document.querySelector('.options');
const highlight = options.querySelector('.choice-highlight');
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
let highlightAnimation;
function moveHighlight(animate = false) {
  const card = options.querySelector('input:checked').closest('.option');
  const group = options.getBoundingClientRect();
  const target = card.getBoundingClientRect();
  const previous = highlight.getBoundingClientRect();
  const wasVisible = !highlight.hidden;
  highlightAnimation?.cancel();
  const x = target.left - group.left;
  const y = target.top - group.top;
  highlight.style.width = `${target.width}px`;
  highlight.style.height = `${target.height}px`;
  highlight.style.transform = `translate(${x}px, ${y}px)`;
  highlight.hidden = false;
  options.classList.add('has-highlight');
  if (animate && wasVisible && !reducedMotion.matches && highlight.animate) {
    const dx = x - (previous.left - group.left);
    const dy = y - (previous.top - group.top);
    highlightAnimation = highlight.animate([
      { transform: `translate(${x - dx}px, ${y - dy}px)` },
      { transform: `translate(${x + dx * .035}px, ${y + dy * .035}px) scale(1.025, .975)`, offset: .76 },
      { transform: `translate(${x}px, ${y}px)` }
    ], { duration: 400, easing: 'cubic-bezier(.22,.75,.26,1)' });
  }
}
options.addEventListener('change', () => moveHighlight(true));
reducedMotion.addEventListener('change', () => moveHighlight());
new ResizeObserver(() => moveHighlight()).observe(options);
moveHighlight();
function updateSelection(){const files=Array.from(fileInput.files);selection.textContent=files.length ? `已选择 ${files.length} 个文件：${files.map(f=>f.name).join('、')}` : '尚未选择文件';}
fileInput.addEventListener('change',updateSelection);
for(const event of ['dragover','dragenter'])drop.addEventListener(event,e=>{e.preventDefault();drop.classList.add('hover');});
for(const event of ['dragleave','drop'])drop.addEventListener(event,e=>{e.preventDefault();drop.classList.remove('hover');});
drop.addEventListener('drop',e=>{if(e.dataTransfer.files.length){fileInput.files=e.dataTransfer.files;updateSelection();}});
function download(blob, filename){const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=filename;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),120000);}
function resultName(fileName,mode){const stem=fileName.replace(/\.pdf$/i,'');const suffix={portrait:'统一A4竖版',landscape:'统一A4横版',preserve:'统一A4保留方向'}[mode];return `${stem}_${suffix}.pdf`;}
go.addEventListener('click', async ()=>{
  const files=Array.from(fileInput.files);if(!files.length){status.className='status error';status.textContent='请先选择至少一个 PDF 文件。';return;}
  if(files.length>30){status.className='status error';status.textContent='一次最多处理 30 个文件。';return;}
  const mode=document.querySelector('input[name=mode]:checked').value;
  const margin=document.getElementById('margin').value;
  const data=new FormData();data.append('mode',mode);data.append('margin',margin);
  files.forEach(file=>data.append('files',file,file.name));
  go.disabled=true;go.textContent='正在处理...';status.className='status';status.textContent=`正在处理 ${files.length} 个 PDF，请保持本页打开。`;
  try{
    const response=await fetch('/convert',{method:'POST',headers:{'X-PDF-Tool-Token':TOKEN},body:data});
    if(!response.ok){let message=await response.text();throw new Error(message||`服务器错误 ${response.status}`);}
    const blob=await response.blob();
    download(blob,files.length===1?resultName(files[0].name,mode):'PDF批量统一A4.zip');
    status.className='status success';status.textContent=`处理完成！已触发下载（${files.length} 个文件）。请查看浏览器“下载”文件夹。`;
  }catch(err){status.className='status error';status.textContent=`处理失败：${err.message}`;}
  finally{go.disabled=false;go.textContent='开始处理并下载';}
});
</script></body></html>'''


def normalize_pdf(data: bytes, mode: str = "portrait", margin_mm: float = 5.0) -> bytes:
    """将一个 PDF 的每一页等比例缩放并居中至目标 A4。"""
    if mode not in {"portrait", "landscape", "preserve"}:
        raise ValueError("页面模式无效")
    if not 0 <= margin_mm <= 30:
        raise ValueError("留白必须在 0～30 mm 之间")
    source = fitz.open(stream=data, filetype="pdf")
    result = fitz.open()
    try:
        if source.needs_pass:
            raise ValueError("PDF 已加密，请先使用原始密码解锁后处理")
        if not source.page_count:
            raise ValueError("PDF 中没有页面")
        pad = margin_mm * 72.0 / 25.4
        for idx in range(source.page_count):
            page = source[idx]
            src_w, src_h = page.rect.width, page.rect.height
            if src_w <= 0 or src_h <= 0:
                raise ValueError(f"第 {idx + 1} 页的尺寸无效")
            landscape = mode == "landscape" or (mode == "preserve" and src_w > src_h)
            target_w, target_h = A4_PORTRAIT[::-1] if landscape else A4_PORTRAIT
            available_w, available_h = target_w - pad * 2, target_h - pad * 2
            scale = min(available_w / src_w, available_h / src_h)
            actual_w, actual_h = src_w * scale, src_h * scale
            x = (target_w - actual_w) / 2
            y = (target_h - actual_h) / 2
            output_page = result.new_page(width=target_w, height=target_h)
            rect = fitz.Rect(x, y, x + actual_w, y + actual_h)
            output_page.show_pdf_page(rect, source, idx, keep_proportion=True)
        return result.tobytes(garbage=3, deflate=True)
    finally:
        result.close()
        source.close()


def parse_form(content_type: str, body: bytes):
    # Python 3.13 移除了 cgi：使用标准库 email 解析 multipart。
    header = f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode()
    message = BytesParser(policy=policy.default).parsebytes(header + body)
    if not message.is_multipart():
        raise ValueError("请使用文件上传表单")
    values, files = {}, []
    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue
        name = part.get_param("name", header="content-disposition")
        payload = part.get_payload(decode=True) or b""
        if name == "files":
            filename = part.get_filename() or "未命名.pdf"
            files.append((Path(filename.replace("\\", "/")).name, payload))
        else:
            values[name] = payload.decode("utf-8", errors="replace")
    return values, files


def unique_name(name: str, used: set) -> str:
    candidate = name
    n = 2
    while candidate in used:
        base, ext = os.path.splitext(name)
        candidate = f"{base}_{n}{ext}"
        n += 1
    used.add(candidate)
    return candidate


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # 不记录用户文件名或内容。
        print(f"[本地服务] {self.address_string()} {format % args}")

    def _send(self, status: int, data: bytes, mime: str = "text/plain; charset=utf-8", filename=None):
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Access-Control-Allow-Origin", "null") if False else None
        if filename:
            self.send_header("Content-Disposition", f"attachment; filename=download; filename*=UTF-8''{quote(filename)}")
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        if self.path != "/":
            self._send(404, "页面不存在".encode())
            return
        page = PAGE_HTML.replace("__TOKEN__", json.dumps(TOKEN)).encode("utf-8")
        self._send(200, page, "text/html; charset=utf-8")

    def do_POST(self):
        if self.path != "/convert":
            self._send(404, b"Not found")
            return
        if self.headers.get("X-PDF-Tool-Token") != TOKEN:
            self._send(403, "请求未通过本地校验，请刷新网页重试".encode("utf-8"))
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_TOTAL_UPLOAD:
                raise ValueError("文件总大小不得超过 160 MB")
            values, files = parse_form(self.headers.get("Content-Type", ""), self.rfile.read(length))
            if not files or len(files) > MAX_FILES:
                raise ValueError("请提供 1～30 个 PDF 文件")
            mode = values.get("mode", "portrait")
            margin = float(values.get("margin", "5"))
            output_items = []
            seen = set()
            suffix = {"portrait": "统一A4竖版", "landscape": "统一A4横版", "preserve": "统一A4保留方向"}.get(mode)
            if suffix is None:
                raise ValueError("未知页面模式")
            for name, data in files:
                if not name.lower().endswith(".pdf"):
                    raise ValueError(f"不是 PDF 文件：{name}")
                try:
                    output = normalize_pdf(data, mode, margin)
                except Exception as error:
                    raise ValueError(f"文件“{name}”处理失败：{error}") from error
                base = name[:-4]
                output_name = unique_name(f"{base}_{suffix}.pdf", seen)
                output_items.append((output_name, output))
            if len(output_items) == 1:
                name, data = output_items[0]
                self._send(200, data, "application/pdf", name)
            else:
                result = io.BytesIO()
                with ZipFile(result, "w", ZIP_DEFLATED) as archive:
                    for name, data in output_items:
                        archive.writestr(name, data)
                self._send(200, result.getvalue(), "application/zip", "PDF批量统一A4.zip")
        except (ValueError, TypeError, RuntimeError, OSError) as exc:
            self._send(400, str(exc).encode("utf-8"))
        except Exception as exc:
            self._send(500, f"出现意外错误：{exc}".encode("utf-8"))


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    url = f"http://127.0.0.1:{server.server_port}/"
    print("\n✅ PDF 页面统一工具启动成功")
    print(f"🌐 请在浏览器打开：{url}")
    print("🔒 PDF 只在本机处理，不上传到云端")
    print("🛑 关闭这个终端窗口，或者按 Ctrl+C，就能停止工具\n")
    threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n工具已关闭")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
