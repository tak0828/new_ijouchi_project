
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
import time

# iniファイル読み込み
import configparser

# Chromeドライバーのパス（必要に応じて変更）
driver = webdriver.Chrome()
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



#リストから代入すること
KansokuName = "国上"
ObsrvId = "384100100039"
ObsrvId = "0" + ObsrvId
SuikeiName = "北陸その他"
RiverName = "その他"
KanriKbn = "自治体"
Syubetu = "雨量"
ChihouCD = "84"

DateNO = "20250918-001"



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
# 画面を戻す
driver.minimize_window()




time.sleep(1)






# 終了
driver.quit()