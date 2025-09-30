
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
import argparse


chrome_options = Options()
chrome_options.add_argument("--headless")           # GUIなしで実行
chrome_options.add_argument("--no-sandbox")         # Docker向け
chrome_options.add_argument("--disable-dev-shm-usage") # メモリ対策
chrome_options.add_argument("--disable-gpu")        # GPU無効化
chrome_options.add_argument("--remote-debugging-port=9222") # デバッグ用
chrome_options.add_argument(f"--user-data-dir=/tmp/selenium_user_data_{os.getpid()}")  # ユニークなプロファイル
chrome_options.add_argument("--window-size=1920,1500") # ウィンドウサイズ指定(ヘッドレスモードで必要)
chrome_options.add_argument("--lang=ja-JP")  # 日本語対応

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


def save_screenshot_png(driver, file_name_png):
    png_dir = "/app/media/png"
    os.makedirs(png_dir, exist_ok=True)
    # os.makedirs(zip_dir, exist_ok=True)

    png_path = os.path.join(png_dir, os.path.basename(file_name_png))
    driver.save_screenshot(png_path)
    print(f"スクショ保存: {png_path}")

def save_screenshot_zip(driver, TempFile_results, csv_filename): 
    zipfileList = []
    # TempFile_results = json.loads(TempFile_results)
    print(TempFile_results)
    for i, row in enumerate(TempFile_results):
        for j, value in enumerate(row):
            zipfileName = TempFile_results[i][j]
            print(f"Type of value at [{i}][{j}]: {type(zipfileName)}")
            if isinstance(value, str) and value.endswith(".png"):
                zipfileList.append(TempFile_results[i][j])
    # ZIP化
    zip_dir = "/app/media/zip"
    png_dir = "/app/media/png/"
    os.makedirs(zip_dir, exist_ok=True)
    
    zip_path = os.path.join(zip_dir, csv_filename + ".zip")
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for filename in zipfileList:
            png_path = os.path.join(png_dir, filename)
            if os.path.exists(png_path):  # ファイルが存在するか確認
                zipf.write(png_path, arcname=filename)  # arcnameでZIP内の名前を指定
            else:
                print(f"ファイルが見つかりません: {png_path}")




    # zip_path = os.path.join(zip_dir, os.path.basename(file_name_png).replace(".png", ".zip"))
    # with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
    #     zipf.write(png_path, arcname=os.path.basename(png_path))
    print(f"ZIP作成完了: {zip_path}")


#リストから代入すること
# KansokuName = "国上"
# ObsrvId = "384100100039"
# ObsrvId = "0" + ObsrvId
# SuikeiName = "北陸その他"
# RiverName = "その他"
# KanriKbn = "自治体"
# Syubetu = "雨量"
# ChihouCD = "84"

# DateNo = "20250918-001"
# 近傍観測所をループでまとめる
kinbou_data = []
for i in range(1, 4):
    KinbouName = test_csv_row.get(f"近傍観測所{i}の名称")
    KinbouObsrvId = test_csv_row.get(f"近傍観測所{i}のID")
    KinbouFlag = test_csv_row.get(f"近傍観測所{i}フラグ")
    if KinbouObsrvId and not KinbouObsrvId.startswith("0"):
        KinbouObsrvId = "0" + KinbouObsrvId
    kinbou_data.append({
        "KansokuName": KinbouName,
        "ObsrvId": KinbouObsrvId, 
        "Flag": KinbouFlag
    })



KansokuName = test_csv_row.get("観測所名")
ObsrvId = test_csv_row.get("統一ID")
if ObsrvId and not ObsrvId.startswith("0"):
    ObsrvId = "0" + ObsrvId  # 先頭に0を付与
SuikeiName = test_csv_row.get("水系名")
RiverName = test_csv_row.get("河川名")
KanriKbn = test_csv_row.get("管理区分")
Syubetu = test_csv_row.get("項目種別")
Kinbou1_KansokuName = kinbou_data[0]["KansokuName"] # 近傍観測所1の名称
Kinbou1_ObsrvId = kinbou_data[0]["ObsrvId"] # 近傍観測所1のID
Kinbou1_Flag = kinbou_data[0]["Flag"] # 近傍観測所1のフラグ
Kinbou2_KansokuName = kinbou_data[1]["KansokuName"] # 近傍観測所2の名称
Kinbou2_ObsrvId = kinbou_data[1]["ObsrvId"] # 近傍観測所2のID
Kinbou2_Flag = kinbou_data[1]["Flag"] # 近傍観測所2のフラグ
Kinbou3_KansokuName = kinbou_data[2]["KansokuName"] # 近傍観測所3の名称
Kinbou3_ObsrvId = kinbou_data[2]["ObsrvId"] # 近傍観測所3のID
Kinbou3_Flag = kinbou_data[2]["Flag"] # 近傍観測所3のフラグ
DateNo = test_csv_row.get("DateNo") # View 側で生成した DateNo をそのまま使用
clat = test_csv_row.get("緯度") # View 側(MS_Kansokujoの緯度) をそのまま使用
clon = test_csv_row.get("経度") # View 側(MS_Kansokujoの経度) をそのまま使用
ChihouCD = test_csv_row.get("地方CD") # View 側(MS_Kansokujoの地方CD) をそのまま使用

# キャプチャ処理用の時刻を取得
Year, Month, Day, Hour, Minute = get_rireki_date(test_csv_row)

# parsed = json.loads(TempFile_results)
parsed = json.loads(sys.argv[2])
TempFile_results = parsed.get("TempFile_results") 
csv_filename = sys.argv[3]
# csv_filename = csv_filename.get("csv_filename")

h = 0
z = 1
for i in range(len(TempFile_results)):
    print(i)
    print(TempFile_results[i][0])
    if TempFile_results[i][0] == DateNo:  # 2列目以降を初期化
        h = i
        break 


# メイン観測所のリスト(辞書の作成(近傍観測所を追加))
obsrvId_list = [
    {"ObsrvId":ObsrvId,"KansokuName":KansokuName, "Flag": True, "Type": "main"}, # メイン観測所
    {"ObsrvId": Kinbou1_ObsrvId, "KansokuName": Kinbou1_KansokuName, "Flag": Kinbou1_Flag, "Type": "kinbou"}, # 近傍観測所1
    {"ObsrvId": Kinbou2_ObsrvId, "KansokuName": Kinbou2_KansokuName, "Flag": Kinbou2_Flag, "Type": "kinbou"}, # 近傍観測所2
    {"ObsrvId": Kinbou3_ObsrvId, "KansokuName": Kinbou3_KansokuName, "Flag": Kinbou3_Flag, "Type": "kinbou"}, # 近傍観測所3
]

#水位グラフキャプチャ処理
TempFileNo = "10"
# ファイル名用にDateNoから日付部分を抽出
FileDateParts = DateNo[4:8] # "20250918-001" から "0918" を抽出

# # 近傍観測所だけを抽出して、番号を振る
# kinbou_obsrvs = [obsrv for obsrv in obsrvId_list if obsrv["Flag"] and obsrv["Type"] == "kinbou"]
# for idx, obsrv in enumerate(kinbou_obsrvs, start=1):
#     obsrv["KinbouIndex"] = idx  # 実際の順番で番号を振る


for obsrv in obsrvId_list:
    if obsrv["Flag"]:  # FlagがTrueのものだけ処理
        ObsrvId = obsrv["ObsrvId"]
        # KansokuName = obsrv["KansokuName"]
        # # ファイル名 観測所名 + 日付 + "_" + 10
        # FileName1 = KansokuName + FileDateParts + "_" + TempFileNo

        if obsrv["Type"] == "main":
            # メイン観測所のファイル名
            FileName1 = KansokuName + FileDateParts + "_" + TempFileNo
        else:
            # 近傍観測所 → 動的に番号を付ける
            FileName1 = f"【近傍】" + obsrv["KansokuName"] + FileDateParts + "_" + TempFileNo

        URL1 = "https://city.river.go.jp/kawabou/cityRainKobetu.do?init=init&obsrvId="
        URL2 = "&gamenId=02-0904&timeType=60&requestType=1"


        URL = URL1 + ObsrvId + URL2


        driver.get(URL)

        print(FileName1)


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
        save_path = FileName1 + ".png"
        # driver.save_screenshot(save_path)
        save_screenshot_png(driver, save_path)

        TempFile_results[h][z] = FileName1 + ".png"  # 2列目に水位グラフのパスをセット
z=z+1




#レーダー累加Cバンドキャプチャ処理
TempFileNo = "20"


for obsrv in obsrvId_list:
    if obsrv["Flag"]:  # FlagがTrueのものだけ処理
        ObsrvId = obsrv["ObsrvId"]
        # KansokuName = obsrv["KansokuName"]

        # ファイル名 観測所名 + 日付 + "_" + 10
        # FileName2 = KansokuName + FileDateParts + "_" + TempFileNo

        if obsrv["Type"] == "main":
            # メイン観測所のファイル名
            FileName1 = KansokuName + FileDateParts + "_" + TempFileNo
        else:
            FileName1 = f"【近傍】" + obsrv["KansokuName"] + FileDateParts + "_" + TempFileNo

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
        save_path = FileName1 + ".png"
        # driver.save_screenshot(save_path)
        save_screenshot_png(driver, save_path)
        TempFile_results[h][z] = FileName1 + ".png"
z=z+1


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


# ファイル名 観測所名 + 日付 + "_" + 10
FileName1 = KansokuName + FileDateParts + "_" + TempFileNo
URL1 = "https://www.river.go.jp/kawabou/pc/rd?zm=12&clat="
URL2 = "&clon="
URL3 ="&fld=0&mapType=0&viewGrpStg=0&viewRd=1&viewRW=1&viewRiver=1&viewPoint=1&ext=0&rdtype=xrain&rdnum=4&rdopa=50&rdint=5&rdtime="
URL = URL1 + clat + URL2 + clon + URL3 + Rdtime
driver.get(URL)

time.sleep(1)

save_path = FileName1 + ".png"
# driver.save_screenshot(save_path)
save_screenshot_png(driver, save_path)
TempFile_results[h][z] = FileName1 + ".png"
z=z+1

print(TempFile_results)

# json.dumps(TempFile_results, ensure_ascii=False)

save_screenshot_zip(driver, TempFile_results, csv_filename)


time.sleep(1)

# =============================
# 出力パス生成処理
# =============================

# 保存ベースディレクトリ
Temp_base_dir = os.path.join("Temp", "調査書", "判断者", DateNo)

# # ディレクトリを作成（存在しない場合のみ）
# os.makedirs(Temp_base_dir, exist_ok=True)

# # "0829" のような月日を生成
md_str = Month + Day   # "08" + "29" → "0829"

# 拡張子なしのファイル名
base_name_no_ext = f"{KansokuName}{md_str}"

# FileName1, FileName2, FileName3 のパスを生成
TempFilePath1 = os.path.join(Temp_base_dir, f"{base_name_no_ext}_10.png")
TempFilePath2 = os.path.join(Temp_base_dir, f"{base_name_no_ext}_20.png")
TempFilePath3 = os.path.join(Temp_base_dir, f"{base_name_no_ext}_30.png")

# print("生成ファイルパス:")
print(TempFilePath1)
print(TempFilePath2)
print(TempFilePath3)

# 添付ファイル生成のパスを標準出力へ
temp_result_paths = {
    "TempFilePath1": TempFilePath1,
    "TempFilePath2": TempFilePath2,
    "TempFilePath3": TempFilePath3,
}
print(json.dumps(TempFile_results, ensure_ascii=False)) # JSON形式で出力
print(json.dumps(temp_result_paths, ensure_ascii=False)) # JSON形式で出力
# =============================
# 終了
driver.quit()



