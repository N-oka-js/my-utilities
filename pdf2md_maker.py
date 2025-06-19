# https://github.com/datalab-to/marker

import os
from datetime import datetime
from dotenv import load_dotenv
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
import time

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
languages = "ja,en"             # 日本語 + 英語対応
force_ocr = True                # スキャンPDF対応（全ページを画像としてOCR）
format_lines = True             # 改行・インライン数式の補正
use_llm = True                  # LLMを使って表・数式・レイアウトを補正
strip_existing_ocr = True       # 既存の誤OCRを捨てて再処理する  
redo_inline_math = True         # 数式再解釈（Markdown整形）     
disable_image_extraction = False # 図のaltテキスト化をする場合はTrue  
page_range = None               # "0,2-5" のように一部ページだけ処理したいとき  

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

# --- コンバータを準備 ---
print("🟡 モデルとOCR設定の準備中...")
start_time = time.time()
converter = PdfConverter(
    artifact_dict=create_model_dict(),
    force_ocr=force_ocr,
    format_lines=format_lines,
    use_llm=use_llm,
    languages=languages,
    strip_existing_ocr=strip_existing_ocr,    
    redo_inline_math=redo_inline_math,        
    disable_image_extraction=disable_image_extraction,  
    page_range=page_range                     
)

# --- 実行 ---
print("🟡 変換中...")
result = converter(pdf_path, output_format=output_format)

# --- 出力保存（Markdownの例） ---
print("🟡 出力保存中...")
output_file = os.path.join(output_dir, "converted.md")
with open(output_file, "w", encoding="utf-8") as f:
    f.write(front_matter + result)

print(f"✅ Done: {output_file}")
end_time = time.time()
print(f"🟢 処理時間: {end_time - start_time:.2f}秒")
