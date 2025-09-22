
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from datetime import datetime , timedelta
import sys
import json
import os
import time
import configparser # iniファイル読み込み
import zipfile


chrome_options = Options()
chrome_options.add_argument("--headless")           # GUIなしで実行
chrome_options.add_argument("--no-sandbox")         # Docker向け
chrome_options.add_argument("--disable-dev-shm-usage") # メモリ対策
chrome_options.add_argument("--disable-gpu")        # GPU無効化
chrome_options.add_argument("--remote-debugging-port=9222") # デバッグ用
chrome_options.add_argument(f"--user-data-dir=/tmp/selenium_user_data_{os.getpid()}")  # ユニークなプロファイル

# Chromeドライバーのパス（必要に応じて変更）
driver = webdriver.Chrome(options=chrome_options)

# driver = webdriver.Chrome()
# ログインページを開く
driver.get("https://city.river.go.jp/kawabou/cityLogin.do")
# 適切な待機（必要に応じてWebDriverWaitに変更）
time.sleep(2)

# ログイン操作
# def login():

# ログインIDとパスワードを入力
driver.find_element(By.NAME, "userId").send_keys("CFRICSTEST5")
driver.find_element(By.NAME, "password").send_keys("fricstest5")
# ログインボタンをクリック
driver.find_element(By.ID, "login").click()
# 必要に応じてログイン後の処理を追加
time.sleep(1)


# ログイン前の URL(ログイン失敗時の URL)と比較してログイン成功を確認
# ＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊
login_url = "https://city.river.go.jp/kawabou/cityLogin.do"
current_url = driver.current_url

if current_url != login_url:
    print(f"ログイン成功 現在のURL: {current_url}")
else:
    print(f"ログイン失敗 現在のURL: {current_url}")

# ＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊

# CSV行を受け取る
if len(sys.argv) > 1:
    test_csv_row = json.loads(sys.argv[1])
else:
    test_csv_row = {}

# datetime に戻したい場合
if "観測日時" in test_csv_row:
    test_csv_row["観測日時"] = datetime.strptime(test_csv_row["観測日時"], "%Y/%m/%d %H:%M")
if "1年前日時" in test_csv_row:
    test_csv_row["1年前日時"] = datetime.strptime(test_csv_row["1年前日時"], "%Y/%m/%d %H:%M")


print("受け取りCSV:", test_csv_row)




#リストから代入すること
# KansokuName = "国上"
# ObsrvId = "384100100039"
# ObsrvId = "0" + ObsrvId
# SuikeiName = "北陸その他"
# RiverName = "その他"
# KanriKbn = "自治体"
# Syubetu = "雨量"
# ChihouCD = "84"

# DateNO = "20250918-001"

KansokuName = test_csv_row.get("観測所名")
ObsrvId = test_csv_row.get("統一ID")
if ObsrvId and not ObsrvId.startswith("0"):
    ObsrvId = "0" + ObsrvId  # 先頭に0を付与
SuikeiName = test_csv_row.get("水系名")
RiverName = test_csv_row.get("河川名")
KanriKbn = test_csv_row.get("管理区分")
Syubetu = test_csv_row.get("項目種別")
ChihouCD = test_csv_row.get("地方名")
DateNO = test_csv_row.get("DateNo") # View 側で生成した DateNo をそのまま使用


# 確認用
print("KansokuName:", KansokuName)
print("ObsrvId:", ObsrvId)
print("SuikeiName:", SuikeiName)
print("RiverName:", RiverName)
print("KanriKbn:", KanriKbn)
print("Syubetu:", Syubetu)
print("ChihouCD:", ChihouCD)
print("DateNO:", DateNO)



#水位グラフキャプチャ処理
TempFileNo = "10"
FileName = DateNO + "_" + TempFileNo
URL1 = "https://city.river.go.jp/kawabou/cityRainKobetu.do?init=init&obsrvId="
URL2 = "&gamenId=02-0904&timeType=60&requestType=1"
URL = URL1 + ObsrvId + URL2

driver.get(URL)

#*****************************************************
#指定時刻を表示する処理を入れること



#*****************************************************


# 画面を最大化
driver.maximize_window()
time.sleep(2)
# スクリーンショットを保存
driver.save_screenshot(FileName + ".png")
# 画面を戻す
driver.minimize_window()



# # テーブルを取得
# table = driver.find_element(By.ID, "hyou")
# # テーブル内の<tr>タグをすべて取得
# rows = table.find_elements(By.TAG_NAME, "tr")
# # 行数（インデックス数）
# RowCntTr = len(rows)


#レーダー累加Cバンドキャプチャ処理
TempFileNo = "20"
FileName = DateNO + "_" + TempFileNo
URL1 = "https://city.river.go.jp/kawabou/cityRadarRuika.do?init=init&areaCd="
URL2 = "&gamenId=02-1802"
URL = URL1 + ChihouCD + URL2

driver.get(URL)

#*****************************************************
#指定時刻を表示する処理を入れること



#*****************************************************

# 画面を最大化
driver.maximize_window()
time.sleep(2)
# スクリーンショットを保存
driver.save_screenshot(FileName + ".png")
# 画面を戻す
driver.minimize_window()

# 一般向け川の防災情報(XRAIN4分割)キャプチャ処理
clat = "37.661679492823"
clon = "138.888006215311"
Year = "2025"
Month = "09"
Hour = "01"
Minute = "10"

Rdtime = Year + "%2F" + Month + "%20" + Hour + "%3A" + Minute


TempFileNo = "30"
FileName = DateNO + "_" + TempFileNo
URL1 = "https://www.river.go.jp/kawabou/pc/rd?zm=12&clat="
URL2 = "&clon="
URL3 ="&fld=0&mapType=0&viewGrpStg=0&viewRd=1&viewRW=1&viewRiver=1&viewPoint=1&ext=0&rdtype=xrain&rdnum=4&rdopa=50&rdint=5&rdtime="
URL = URL1 + clat + URL2 + clon + URL3 + Rdtime
driver.get(URL)

# 画面を最大化
driver.maximize_window()
time.sleep(1)
# スクリーンショットを保存
driver.save_screenshot(FileName + ".png")

# 既存の ZIP ファイル名(DateNO_screenshot.zip)
zip_filename = f"{DateNO}_screenshot.zip"



# 画面を戻す
driver.minimize_window()




time.sleep(1)






# 終了
driver.quit()