#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# jpegToPdf

指定した親ディレクトリ内の各フォルダを対象に、JPEG 画像をまとめて 1 冊の PDF に変換するツールです。

## 機能

- フォルダ単位で JPEG を結合し、同名の PDF を出力
- 壊れた JPEG（読み込み不能、CMYK 等）を自動修復
- 超高解像度画像は自動で縮小（設定可能）
- 変換済みの PDF が存在する場合はスキップ
- 処理結果はコンソールに出力（失敗ファイルも表示）

## 使用方法

1. Python がインストールされた環境で本スクリプトを実行
2. 第1引数に変換対象の親フォルダ、第2引数に出力先フォルダを指定
"""

import sys, tempfile
from pathlib import Path

import img2pdf
from PIL import Image, ImageFile, UnidentifiedImageError
from natsort import natsorted

# Pillow 設定
ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = None  # サイズ制限オフ

# ------ ここを自分の環境に合わせる --------------------------
DEFAULT_ROOT = Path(r"C:\Users")
DEFAULT_OUT = Path(r"C:\Users")
MAX_W, MAX_H = None, None  # ←長辺がこれより大きければ縮小（不要なら None）
JPEG_QUALITY = 100  # 再保存時の画質
# -----------------------------------------------------------


def repair_if_needed(p: Path) -> str:
    """
    p が正常 JPEG ならそのままパスを返す。
    読めない / CMYK / プログレッシブ / 巨大サイズなら
    一時 JPEG に再保存してそのパスを返す。
    """
    try:
        with Image.open(p) as im:
            im.verify()  # 壊れ・誤拡張子ならここで例外
            im.close()  # verify() の後は再 open が必要
        with Image.open(p) as im:
            need_rewrite = False

            # CMYK など RGB 以外なら再保存
            if im.mode not in ("RGB", "L"):
                need_rewrite = True
                im = im.convert("RGB")

            # 巨大なら縮小
            if MAX_W and MAX_H and (im.width > MAX_W or im.height > MAX_H):
                need_rewrite = True
                im.thumbnail((MAX_W, MAX_H), Image.LANCZOS)

            if need_rewrite:
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                im.save(tmp.name, "JPEG", quality=JPEG_QUALITY)
                return tmp.name  # 修復済みパス
            else:
                return str(p)  # そのままOK
    except (UnidentifiedImageError, OSError):
        # verify で読めない → 強制再保存にチャレンジ
        try:
            with Image.open(p) as im:
                im = im.convert("RGB")
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                im.save(tmp.name, "JPEG", quality=JPEG_QUALITY)
                return tmp.name
        except Exception:
            raise  # ここまで来たら完全に壊れ


def volume_to_pdf(volume_dir: Path, out_dir: Path):
    out_path = out_dir / f"{volume_dir.name}.pdf"
    if out_path.exists():
        print(f"[SKIP] {out_path.name} は既に存在します")
        return

    good, failed = [], []

    for p in natsorted(volume_dir.glob("*.jp*g")):
        try:
            good.append(repair_if_needed(p))
        except Exception as e:
            failed.append(p.name)

    if failed:
        print(f"[WARN] {volume_dir.name}: 修復不能 {len(failed)} 枚 → 巻ごとスキップ")
        for f in failed:
            print(f"   - {f}")
        return

    if not good:
        print(f"[SKIP] {volume_dir}: 有効な JPEG なし")
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as f_out:
        f_out.write(img2pdf.convert(good))
    print(f"[MAKE] {out_path} ({len(good)} pages)")


def main(root_dir: Path, out_dir: Path):
    for child in sorted(root_dir.iterdir()):
        if child.is_dir():
            volume_to_pdf(child, out_dir)


if __name__ == "__main__":
    if len(sys.argv) == 3:
        main(Path(sys.argv[1]), Path(sys.argv[2]))
    else:
        main(DEFAULT_ROOT, DEFAULT_OUT)
