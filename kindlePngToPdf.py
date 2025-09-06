#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# jpegToPdf (PNG対応版)

指定した親ディレクトリ内の各フォルダを対象に、JPEG/PNG 画像をまとめて 1 冊の PDF に変換します。

## 機能
- フォルダ単位で JPEG/PNG を結合し、同名の PDF を出力
- 壊れた画像（読み込み不能、CMYK/インデックス/透過 等）を自動修復
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
DEFAULT_ROOT = Path(r"C:\dev\tools\shots")
DEFAULT_OUT = Path(r"C:\dev\tools\shots")
MAX_W, MAX_H = None, None  # ←長辺がこれより大きければ縮小（不要なら None）
JPEG_QUALITY = 100  # 再保存時の画質（JPEGのみ）
# -----------------------------------------------------------

IMG_EXTS = {".jpg", ".jpeg", ".png"}  # 対象拡張子（小文字で比較）


def _has_alpha(im: Image.Image) -> bool:
    # RGBA/LA/P(透過) はアルファあり
    if im.mode in ("RGBA", "LA"):
        return True
    if im.mode == "P":
        # Pモードでも透過情報が埋まっている場合あり
        return "transparency" in im.info
    return False


def _to_rgb_without_alpha(im: Image.Image) -> Image.Image:
    """アルファを白背景に合成してRGBへ"""
    if im.mode in ("RGBA", "LA") or _has_alpha(im):
        bg = Image.new("RGB", im.size, (255, 255, 255))
        # RGBA以外のケースは一旦RGBAへ
        if im.mode not in ("RGBA", "LA"):
            im = im.convert("RGBA")
        bg.paste(im, mask=im.split()[-1])
        return bg
    # RGB/L はそのまま/変換
    return im.convert("RGB") if im.mode != "RGB" else im


def prepare_for_pdf(p: Path) -> str:
    """
    p が正常画像(JPEG/PNG)ならそのままパスを返す。
    読めない / 非RGB / 透過 / 巨大サイズなら
    一時ファイルに再保存してそのパスを返す（フォーマットは元に準拠）。
    """
    try:
        with Image.open(p) as im:
            im.verify()  # 壊れ・誤拡張子ならここで例外
        with Image.open(p) as im:
            orig_format = (im.format or "").upper()  # 'JPEG' / 'PNG' など
            need_rewrite = False
            work = im

            # 透過や非RGBなどは再保存対象
            if orig_format == "PNG":
                if _has_alpha(work) or work.mode not in ("RGB", "L"):
                    need_rewrite = True
                    work = _to_rgb_without_alpha(
                        work
                    )  # PNGでもPDFでは透過不可のため除去
            else:
                # JPEGやその他（基本はJPEG想定）
                if work.mode not in ("RGB", "L"):
                    need_rewrite = True
                    work = work.convert("RGB")

            # 巨大なら縮小
            if MAX_W and MAX_H and (work.width > MAX_W or work.height > MAX_H):
                need_rewrite = True
                work.thumbnail((MAX_W, MAX_H), Image.LANCZOS)

            if need_rewrite:
                # 元がPNGならPNGで、JPEGならJPEGで保存（PNGは可逆/透過除去済み）
                if orig_format == "PNG":
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                    # optimizeで少しサイズ削減、透過は既に除去済み
                    work.save(tmp.name, "PNG", optimize=True)
                else:
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                    work = work.convert("RGB")  # 念のため
                    work.save(tmp.name, "JPEG", quality=JPEG_QUALITY)
                return tmp.name
            else:
                return str(p)
    except (UnidentifiedImageError, OSError):
        # verifyで読めない → 強制再保存（拡張子に依らずRGBで）
        try:
            with Image.open(p) as im:
                im = _to_rgb_without_alpha(im)
                # 元がPNGならPNG、そうでなければJPEGにしておく
                suffix = ".png" if (p.suffix.lower() == ".png") else ".jpg"
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                if suffix == ".png":
                    im.save(tmp.name, "PNG", optimize=True)
                else:
                    im.save(tmp.name, "JPEG", quality=JPEG_QUALITY)
                return tmp.name
        except Exception:
            raise  # ここまで来たら完全に壊れ


def _iter_images(dirpath: Path):
    # 大文字拡張子も拾えるように自前フィルタ
    for p in dirpath.iterdir():
        if p.is_file() and p.suffix.lower() in IMG_EXTS:
            yield p


def volume_to_pdf(volume_dir: Path, out_dir: Path):
    out_path = out_dir / f"{volume_dir.name}.pdf"
    if out_path.exists():
        print(f"[SKIP] {out_path.name} は既に存在します")
        return

    good, failed = [], []

    for p in natsorted(_iter_images(volume_dir), key=lambda x: x.name):
        try:
            good.append(prepare_for_pdf(p))
        except Exception:
            failed.append(p.name)

    if failed:
        print(f"[WARN] {volume_dir.name}: 修復不能 {len(failed)} 枚 → 巻ごとスキップ")
        for f in failed:
            print(f"   - {f}")
        return

    if not good:
        print(f"[SKIP] {volume_dir}: 有効な JPEG/PNG なし")
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
