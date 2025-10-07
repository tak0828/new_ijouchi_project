
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


def execute_attached_file_processing(csv_rows, csv_filename, TempFile_results):

    try:
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
        driver.find_element(By.NAME, "userId").send_keys("CFRICSTEST4")
        driver.find_element(By.NAME, "password").send_keys("fricstest4")
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

        # キャプチャ処理用の時刻を取得
        csv_rows, Year, Month, Day, Hour, Minute = get_rireki_date(csv_rows)

        result1 = capture_water_level(driver, csv_rows,  csv_filename, TempFile_results, TempFileNo="10")
        result2 = capture_radar_ruika(driver, csv_rows,  csv_filename, TempFile_results, TempFileNo="20")
        result3 = capture_xrain_four(driver, csv_rows,  csv_filename, TempFile_results, TempFileNo="30")

        #=============================
        # 終了
        driver.quit()

        TempFile_results, temp_result_paths = generate_temp_file(csv_rows, TempFile_results)

        return TempFile_results, temp_result_paths


    except Exception as e:
        print("=== 例外発生 ===")
        print("エラー内容:", e)

def get_rireki_date(csv_rows):
    """
    CSVの観測日時をそのまま取得し、観測日時を文字列化
    csv_rows の各行に 'Year', 'Month', 'Day', 'Hour', 'Minute' を追加する
    """

    Year = []
    Month = []
    Day = []
    Hour = []
    Minute = []

    for row in csv_rows:
        if "観測日時" not in row:
            raise ValueError("観測日時が存在しません")

        dt = row["観測日時"]
        if not isinstance(dt, datetime):
        # CSVの文字列形式が "YYYY-MM-DD HH:MM:SS" の場合
            dt = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
            # 上書きして csv_rows に保存
            row["観測日時"] = dt

        row["Year"] = dt.strftime("%Y")
        row["Month"] = dt.strftime("%m")
        row["Day"] = dt.strftime("%d")
        row["Hour"] = dt.strftime("%H")
        row["Minute"] = dt.strftime("%M")

        # 関数としてリストに追加
        Year.append(row["Year"])
        Month.append(row["Month"])
        Day.append(row["Day"])
        Hour.append(row["Hour"])
        Minute.append(row["Minute"])

    return csv_rows, Year, Month, Day, Hour, Minute


def save_screenshot_png(driver, file_name_png):
    png_dir = "/app/media/png"
    os.makedirs(png_dir, exist_ok=True)
    # os.makedirs(zip_dir, exist_ok=True)

    png_path = os.path.join(png_dir, os.path.basename(file_name_png))
    driver.save_screenshot(png_path)
    print(f"スクショ保存: {png_path}")

def save_screenshot_zip(driver, TempFile_results, csv_filename): 
    zipfileList = []
    print(TempFile_results)
    
    # 新しい辞書形式のTempFile_resultsからPNGファイルを抽出
    # for date_no, entry in TempFile_results.items():
    #     TempFile_results = entry.get("TempFile_results", [])
    #     for filename in TempFile_results:
    #         if isinstance(filename, str) and filename.endswith(".png") and filename != "0":
    #             zipfileList.append(filename)
    #             print(f"ZIPに追加: {filename}")

    # TempFile_results がリストなので変更する(1番最初の列だけ除外する)
    for row in TempFile_results:
        # 1列目（日付）を除いて PNG だけを処理
        for filename in row[1:]:
            if isinstance(filename, str) and filename.endswith(".png") and filename != "0":
                zipfileList.append(filename)
                print(f"ZIPに追加: {filename}")        
            
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

    print(f"ZIP作成完了: {zip_path}")

def capture_water_level(driver, csv_rows,  csv_filename, TempFile_results, TempFileNo="10"):
    """
    CSV行(複数行)の情報から水位グラフを取得してPNG保存
    """
    # TempFile_results索引用
    i = 0
    # ファイル名用にDateNoから日付部分を抽出
    for rows in csv_rows:
        FileDateParts = rows["DateNo"][4:8]  # 例: "20250918-001" -> "0918"
        KansokuName = rows["観測所名"] # 観測所名
        ObsrvId = rows["統一ID"]
        # 値が存在し、13桁でない場合は先頭に0を追加
        if ObsrvId and len(ObsrvId) != 13:
            ObsrvId = ObsrvId.zfill(13)  # 全体を13桁にゼロ埋め

        # ファイル名作成
        FileName1 = KansokuName + FileDateParts + "_" + TempFileNo

        URL1 = "https://city.river.go.jp/kawabou/cityRainKobetu.do?init=init&obsrvId="
        URL2 = "&gamenId=02-0904&timeType=60&requestType=1"

        URL = URL1 + ObsrvId + URL2
        driver.get(URL)

        print(FileName1)

        #*****************************************************
        #指定時刻を表示する処理
        Year = rows["Year"]
        Month = rows["Month"]
        Day = rows["Day"]
        Hour = rows["Hour"]
        Minute = rows["Minute"]

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

        TempFile_results[i][1] = FileName1 + ".png"  # 2列目に水位グラフのパスをセット
        i += 1


    return save_path

def capture_radar_ruika(driver, csv_rows,  csv_filename, TempFile_results,  TempFileNo="20"):
    
    #レーダー累加Cバンドキャプチャ処理
    """
    CSV行(複数行)の情報からレーダー累加Cバンドを取得してPNG保存
    """
    # TempFile_results索引用
    i = 0

    for rows in csv_rows:
        # ファイル名 観測所名 + 日付 + "_" + 10
        FileDateParts = rows["DateNo"][4:8]  # 例: "20250918-001" -> "0918"
        KansokuName = rows["観測所名"] # 観測所名
        ObsrvId = rows["統一ID"]
        # 値が存在し、13桁でない場合は先頭に0を追加
        if ObsrvId and len(ObsrvId) != 13:
            ObsrvId = ObsrvId.zfill(13)  # 全体を13桁にゼロ埋め
        ChihouCD = rows["地方CD"] #地方CD

        # メイン観測所のファイル名
        FileName1 = KansokuName + FileDateParts + "_" + TempFileNo

        URL1 = "https://city.river.go.jp/kawabou/cityRadarRuika.do?init=init&areaCd="
        URL2 = "&gamenId=02-1802"
        URL = URL1 + str(ChihouCD) + URL2

        driver.get(URL)

        #*****************************************************
        #指定時刻を表示する処理
        Year = rows["Year"]
        Month = rows["Month"]
        Day = rows["Day"]
        Hour = rows["Hour"]
        Minute = rows["Minute"]

        # selectタグを取得

        WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located)
        iframe = driver.find_element(By.ID, "ctrlTimeFrm")
        driver.switch_to.frame(iframe)
        #***************
        # From
        #***************
        date_obj = rows["観測日時"]   # ここで date_obj を定義
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
        TempFile_results[i][2] = FileName1 + ".png"
        i += 1
    
    return save_path

def capture_xrain_four(driver, csv_rows,  csv_filename, TempFile_results,  TempFileNo="30"):

    # 一般向け川の防災情報(XRAIN4分割)キャプチャ処理
    """
    CSV行(複数行)の情報から一般向け川の防災情報(XRAIN4分割)を取得してPNG保存
    """
    # TempFile_results索引用
    i = 0
    for rows in csv_rows:
        # ファイル名 観測所名 + 日付 + "_" + 10
        FileDateParts = rows["DateNo"][4:8]  # 例: "20250918-001" -> "0918"
        KansokuName = rows["観測所名"] # 観測所名
        ObsrvId = rows["統一ID"]
        # 値が存在し、13桁でない場合は先頭に0を追加
        if ObsrvId and len(ObsrvId) != 13:
            ObsrvId = ObsrvId.zfill(13)  # 全体を13桁にゼロ埋め

        clat = rows["緯度"] # View 側(MS_Kansokujoの緯度) 
        clon = rows["経度"] # View 側(MS_Kansokujoの経度) 
        # 指定日時の取得
        Year = rows["Year"]
        Month = rows["Month"]
        Day = rows["Day"]
        Hour = rows["Hour"]
        Minute = rows["Minute"]

        Rdtime = Year + "%2F" + Month + "%2F" + Day + "%20" + Hour + "%3A" + Minute

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
        TempFile_results[i][3] = FileName1 + ".png"

        # TempFile_resultsを更新
        TempFile_results[i][0] = rows["DateNo"]

        i += 1
    print(TempFile_results)
    save_screenshot_zip(driver, TempFile_results, csv_filename)

    time.sleep(1)

def generate_temp_file(csv_rows, TempFile_results):
    # =============================
    # 出力パス生成処理
    # =============================

    temp_result_paths = []

    for temp_files in TempFile_results:

        Date = temp_files[0]          # "20250921-001"
        DateNo  = Date.split("-")[1]    # "001"
        MD = Date[4:8]            #"0921"
        # KansokuName = temp_files[:-9] # 末尾 9文字除外 "+MMDD_10.png" は除外

        # ファイル名部分だけ取り出す（0は除外）(temp_files2列目以降)
        file_names = [f for f in temp_files[1:] if f != "0" and f]

        temp_paths = []

        for filename in file_names:
            # 保存ベースディレクトリ
            Temp_base_dir = os.path.join("Temp", "調査書", "判断者", DateNo)

            # ファイルパスを生成してリストに追加
            Temp_path = os.path.join(Temp_base_dir, filename)
            temp_paths.append(Temp_path)

        # この日付分のファイルパスリストをまとめて temp_result_paths に追加
        temp_result_paths.append([Date] + temp_paths)



    return TempFile_results, temp_result_paths




