
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
chrome_options.add_argument("--window-size=1920,1500") # ウィンドウサイズ指定(ヘッドレスモードで必要)

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
# if "1年前日時" in test_csv_row:
#     test_csv_row["1年前日時"] = datetime.strptime(test_csv_row["1年前日時"], "%Y/%m/%d %H:%M")


print("受け取りCSV:", test_csv_row)

def get_rireki_date(test_csv_row):
    """
    CSVの観測日時をそのまま取得し、
    Year, Month, Day, Hour, Minute を返す
    """
    if "観測日時" not in test_csv_row:
        raise ValueError("観測日時が存在しません")

    dt = test_csv_row["観測日時"]
    if not isinstance(dt, datetime):
        # CSVの文字列形式が "YYYY-MM-DD HH:MM:SS" の場合
        dt = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")

    Year = dt.strftime("%Y")
    Month = dt.strftime("%m")
    Day = dt.strftime("%d")
    Hour = dt.strftime("%H")
    Minute = dt.strftime("%M")

    return Year, Month, Day, Hour, Minute

# スクリーンショットを保存＆ZIP化（両方残す）
def save_screenshot_and_zip(driver, file_name_png):
    # PNG保存
    driver.save_screenshot(file_name_png)
    print(f"スクショ保存: {file_name_png}")
    
    # ZIP化
    zip_filename = file_name_png.replace(".png", ".zip")
    with zipfile.ZipFile(zip_filename, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(file_name_png)
    print(f"ZIP作成完了: {zip_filename}")


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
# 近傍観測所をループでまとめる
kinbou_data = []
for i in range(1, 4):
    KinbouName = test_csv_row.get(f"近傍観測所{i}の名称")
    KinbouObsrvId = test_csv_row.get(f"近傍観測所{i}のID")
    if KinbouObsrvId and not KinbouObsrvId.startswith("0"):
        KinbouObsrvId = "0" + KinbouObsrvId
    kinbou_data.append({
        "KansokuName": KinbouName,
        "ObsrvId": KinbouObsrvId 
    })



KansokuName = test_csv_row.get("観測所名")
ObsrvId = test_csv_row.get("統一ID")
if ObsrvId and not ObsrvId.startswith("0"):
    ObsrvId = "0" + ObsrvId  # 先頭に0を付与
SuikeiName = test_csv_row.get("水系名")
RiverName = test_csv_row.get("河川名")
KanriKbn = test_csv_row.get("管理区分")
Syubetu = test_csv_row.get("項目種別")
Kinbou1_KansokuName = kinbou_data[0]["KansokuName"]
Kinbou1_ObsrvId = kinbou_data[0]["ObsrvId"]
Kinbou2_KansokuName = kinbou_data[1]["KansokuName"]
Kinbou2_ObsrvId = kinbou_data[1]["ObsrvId"]
Kinbou3_KansokuName = kinbou_data[2]["KansokuName"]
Kinbou3_ObsrvId = kinbou_data[2]["ObsrvId"]
DateNO = test_csv_row.get("DateNo") # View 側で生成した DateNo をそのまま使用
clat = test_csv_row.get("緯度") # View 側(MS_Kansokujoの緯度) をそのまま使用
clon = test_csv_row.get("経度") # View 側(MS_Kansokujoの経度) をそのまま使用
ChihouCD = test_csv_row.get("地方CD") # View 側(MS_Kansokujoの地方CD) をそのまま使用

# キャプチャ処理用の時刻を取得
Year, Month, Day, Hour, Minute = get_rireki_date(test_csv_row)



#水位グラフキャプチャ処理
TempFileNo = "10"
FileName = DateNO + "_" + TempFileNo
URL1 = "https://city.river.go.jp/kawabou/cityRainKobetu.do?init=init&obsrvId="
URL2 = "&gamenId=02-0904&timeType=60&requestType=1"
URL = URL1 + ObsrvId + URL2

driver.get(URL)

#*****************************************************
#指定時刻を表示する処理
# selectタグを取得
dropdown = driver.find_element(By.ID, "cityRainKobetu_commonForm_yearMonthString") 
# Selectオブジェクトを生成
select = Select(dropdown)
if Month[0] == "0":
    YM = Year + "年" + Month[1] + "月"
else:
    YM = Year + "年" + Month + "月"
# 選択方法③：表示テキストで選択
select.select_by_visible_text(YM)  # 表示されているテキストで選択


dropdown = driver.find_element(By.ID, "cityRainKobetu_commonForm_dayString")
select = Select(dropdown)
if Day[0] == "0":
    DD = Day[1] + "日"
else:
    DD = Day + "日"
select.select_by_visible_text(DD)  # 表示されているテキストで選択

dropdown = driver.find_element(By.ID, "cityRainKobetu_commonForm_hourString")
select = Select(dropdown)

if len(Hour) == 1:
    HH = "0" + Hour[0] + "時"
else:
    HH = Hour + "時"
select.select_by_visible_text(HH)  # 表示されているテキストで選択

dropdown = driver.find_element(By.ID, "cityRainKobetu_commonForm_minuteString")
select = Select(dropdown)
MM = Minute + "分"
select.select_by_visible_text(MM)  # 表示されているテキストで選択

driver.find_element(By.XPATH, '//*[@id="mainHeadDiv"]/div[3]/div/table/tbody/tr/td/table/tbody/tr[3]/td/table/tbody/tr/td[2]/a/img').click()
#*****************************************************


time.sleep(3)
# スクリーンショットを保存
save_path = FileName + ".png"
driver.save_screenshot(save_path)
save_screenshot_and_zip(driver, save_path)


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
URL = URL1 + str(ChihouCD) + URL2

driver.get(URL)

#*****************************************************
#指定時刻を表示する処理
# selectタグを取得

WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located)
iframe = driver.find_element(By.ID, "ctrlTimeFrm")
driver.switch_to.frame(iframe)
#***************
# From
#***************
date_obj = test_csv_row["観測日時"]   # ここで date_obj を定義
#3時間前を設定
Fdate_obj = date_obj - timedelta(hours=3)
FYY =  str(Fdate_obj.year)
FMounth =  str(Fdate_obj.month)
FDD = str(Fdate_obj.day)
FHH = str(Fdate_obj.hour)
FMM = str(Fdate_obj.minute)

dropdown = driver.find_element(By.XPATH, "/html/body/form/table/tbody/tr[1]/td[1]/select") 
select = Select(dropdown)
YYM = select.select_by_value
if FMounth[0] == "0":
    YM = FYY + "年" + FMounth[1] + "月"
else:
    YM = FYY + "年" + FMounth + "月"
# 選択方法③：表示テキストで選択
select.select_by_visible_text(YM)
# YM = "202508"
# select.select_by_value(YM)  # 表示されているテキストで選択
dropdown = driver.find_element(By.XPATH, "/html/body/form/table/tbody/tr[1]/td[2]/span/select")
select = Select(dropdown)
if FDD[0] == "0":
    DD = FDD[1] + "日"
else:
    DD = FDD + "日"
select.select_by_visible_text(DD)  # 表示されているテキストで選択
dropdown = driver.find_element(By.XPATH, "/html/body/form/table/tbody/tr[1]/td[3]/select")
select = Select(dropdown)

if len(FHH) == 1:
    HH = "0" + FHH[0] + "時"
else:
    HH = FHH + "時"
select.select_by_visible_text(HH)  # 表示されているテキストで選択
dropdown = driver.find_element(By.XPATH, "/html/body/form/table/tbody/tr[1]/td[4]/select")
select = Select(dropdown)
MM = Minute + "分"
select.select_by_visible_text(MM)  # 表示されているテキストで選択


#***************
# To
#***************
# データの作成 要素の直接指定でクリック
dropdown = driver.find_element(By.XPATH,'/html/body/form/table/tbody/tr[2]/td[1]/select')
# Selectオブジェクトを生成
select = Select(dropdown)

if Month[0] == "0":
    YM = Year + "年" + Month[1] + "月"
else:
    YM = Year + "年" + Month + "月"
# 選択方法③：表示テキストで選択
select.select_by_visible_text(YM)  # 表示されているテキストで選択
dropdown = driver.find_element(By.XPATH,'/html/body/form/table/tbody/tr[2]/td[2]/span/select')
select = Select(dropdown)
if Day[0] == "0":
    DD = Day[1] + "日"
else:
    DD = Day + "日"
select.select_by_visible_text(DD)  # 表示されているテキストで選択
dropdown = driver.find_element(By.XPATH,'/html/body/form/table/tbody/tr[2]/td[3]/select')
select = Select(dropdown)
if len(Hour) == 1:
    HH = "0" + Hour[0] + "時"
else:
    HH = Hour + "時"
select.select_by_visible_text(HH)  # 表示されているテキストで選択
dropdown = driver.find_element(By.XPATH, "/html/body/form/table/tbody/tr[2]/td[4]/select")
select = Select(dropdown)
MM = Minute + "分"
select.select_by_visible_text(MM)  # 表示されているテキストで選択

driver.find_element(By.XPATH, '//*[@id="form1"]/table/tbody/tr[2]/td[5]/a/img').click()



#*****************************************************




time.sleep(3)
# スクリーンショットを保存
save_path = FileName + ".png"
driver.save_screenshot(save_path)
save_screenshot_and_zip(driver, save_path)

# 画面を戻す
# driver.minimize_window()

# 一般向け川の防災情報(XRAIN4分割)キャプチャ処理


# clat = "37.661679492823"
# clon = "138.888006215311"
# Year = "2025"
# Month = "09"
# Hour = "01"
# Minute = "10"

# Rdtime = Year + "%2F" + Month + "%20" + Hour + "%3A" + Minute
Rdtime = Year + "%2F" + Month + "%2F" + Day + "%20" + Hour + "%3A" + Minute



TempFileNo = "30"
FileName = DateNO + "_" + TempFileNo
URL1 = "https://www.river.go.jp/kawabou/pc/rd?zm=12&clat="
URL2 = "&clon="
URL3 ="&fld=0&mapType=0&viewGrpStg=0&viewRd=1&viewRW=1&viewRiver=1&viewPoint=1&ext=0&rdtype=xrain&rdnum=4&rdopa=50&rdint=5&rdtime="
URL = URL1 + clat + URL2 + clon + URL3 + Rdtime
driver.get(URL)

time.sleep(1)

save_path = FileName + ".png"
driver.save_screenshot(save_path)
save_screenshot_and_zip(driver, save_path)



time.sleep(1)

# 終了
driver.quit()

