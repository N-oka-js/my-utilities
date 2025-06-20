# https://github.com/datalab-to/marker

import os
from datetime import datetime
from dotenv import load_dotenv
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
import time
import subprocess, shlex, textwrap

# --- .env 読み込み ---
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")

# --- 設定 ---
pdf_path = input(
    "変換したいPDFファイルの絶対パスを入力してください：\n"
    "例：C:\\Users\\yu_yu\\OneDrive\\PDF\\自動同期\\雑誌\\Webを支える技術.pdf\n> "
).strip().strip('"')
output_dir = r"C:\dev\obsidian\Zettelkasten\LiteratureNote"
output_format = "markdown"      # 他に json, html など

# --- Obsidianのフロントマターの作成 ---
pdf_name = os.path.basename(pdf_path)                       # ファイル名（例: Webを支える技術.pdf）
title = os.path.splitext(pdf_name)[0]                       # 拡張子なしのファイル名
created = datetime.now().strftime("%Y-%m-%d")               # 日付（例: 2025-06-18）

front_matter = f"""---
title: "{title}"
author: ""
created: {created}
tags:
  - "pdf"
---

"""

# --- CLI コマンド組み立て ---
cmd = textwrap.dedent(f"""
  marker_single "{pdf_path}"
    --output_format {output_format}
    --force_ocr
    --format_lines
    --use_llm
    --strip_existing_ocr
    --redo_inline_math
    --gemini_api_key {gemini_api_key}
    --output_dir "{output_dir}"
""").strip().replace("\n", " ")

print("🚀 marker_single を実行します…")
start_time = time.time()
subprocess.run(shlex.split(cmd), check=True)
print("✅ marker_single 完了")
end_time = time.time()
print(f"🟢 処理時間: {end_time - start_time:.2f}秒")


# --- フロントマターを追加 ---
converted_md = os.path.join(
    output_dir,
    title,                       
    f"{title}.md"                     # marker_single が付けたファイル名
)
print("🟡 フロントマターを追加...")
with open(converted_md, "r", encoding="utf-8") as rf:
    body = rf.read()

# すでに front_matter 変数は作ってある
with open(converted_md, "w", encoding="utf-8") as wf:
    wf.write(front_matter + body)
print(f"✅ Done: {title}")

