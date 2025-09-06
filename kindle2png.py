# kindle2png.py
import re
import time
import random
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchFrameException,
    StaleElementReferenceException,
)
from selenium.webdriver import ActionChains
from selenium.webdriver.common.keys import Keys

# ===== 設定 =====
URL = "https://read.amazon.co.jp/?asin=B0DK6LZRMP&ref_=kwl_kr_iv_rec_1"
PAGE_INFO_SEL = ".text-div"  # Location情報
BOOK_TITLE_SEL = "ion-title.top-chrome__book-title"
LOGIN_OK_SEL = PAGE_INFO_SEL
LOGIN_WAIT_SEC = 600
CHROME_USER_DATA_DIR = r"C:\dev\chrome-profile"

DELAY_BASE_SEC = 5
JITTER_SEC = 0.7


def human_sleep():
    t = max(
        4.5, random.uniform(DELAY_BASE_SEC - JITTER_SEC, DELAY_BASE_SEC + JITTER_SEC)
    )
    time.sleep(t)


def wait_manual_login(driver, wait_sel: str | None, max_wait: int):
    print("\n==== 手動ログインタイム ====")
    print("Amazon にログインしてください（2FA含む）。")
    input("ログイン完了後、ここで Enter を押すと続行します >> ")
    if wait_sel:
        print(f"ログイン後の要素 {wait_sel} を検知中…（最大 {max_wait} 秒）")
        WebDriverWait(driver, max_wait).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, wait_sel))
        )
        print("ログイン検知OK。続行します。")


def try_switch_to_kindle_iframe(driver):
    try:
        driver.switch_to.default_content()
        iframe = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    "iframe#KindleReaderIFrame, iframe[name='KindleReaderIFrame']",
                )
            )
        )
        driver.switch_to.frame(iframe)
        print("[info] KindleReaderIFrame に切り替えました。")
    except (TimeoutException, NoSuchFrameException):
        pass


def page_changed(driver, selector, prev_text):
    try:
        return driver.find_element(By.CSS_SELECTOR, selector).text != prev_text
    except StaleElementReferenceException:
        return False


def main():
    opts = Options()
    opts.add_argument(f"--user-data-dir={CHROME_USER_DATA_DIR}")
    driver = webdriver.Chrome(options=opts)
    wait = WebDriverWait(driver, 30)

    try:
        driver.get(URL)
        wait_manual_login(driver, LOGIN_OK_SEL, LOGIN_WAIT_SEC)
        try_switch_to_kindle_iframe(driver)

        # 書籍タイトル取得
        title_el = wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, BOOK_TITLE_SEL))
        )
        book_title = title_el.text.strip()
        safe_title = re.sub(r'[\\/:*?"<>|]', "_", book_title)  # 禁止文字を置換
        OUT_DIR = Path("./shots") / safe_title
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        print(f"[info] 保存先フォルダ: {OUT_DIR}")

        actions = ActionChains(driver)
        counter = 1

        while True:
            info_el = wait.until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, PAGE_INFO_SEL))
            )
            info_text = info_el.text
            m = re.search(r"Location\s+(\d+)\s+of\s+(\d+)", info_text)
            if not m:
                raise RuntimeError(f"ページ情報の抽出に失敗: {info_text!r}")
            current, total = int(m.group(1)), int(m.group(2))

            fname = OUT_DIR / f"{counter:04d}.png"
            driver.save_screenshot(str(fname))
            print(f"[{current}/{total}] -> {fname.name}")

            if current >= total:
                print("最終ページに到達。終了します。")
                break

            prev_info = info_text
            actions.key_down(Keys.CONTROL).send_keys(Keys.ARROW_RIGHT).key_up(
                Keys.CONTROL
            ).perform()
            wait.until(lambda d: page_changed(d, PAGE_INFO_SEL, prev_info))

            counter += 1
            human_sleep()

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
