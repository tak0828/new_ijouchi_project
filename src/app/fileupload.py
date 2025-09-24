import os
import json
import argparse
import configparser
import paramiko
from pathlib import Path


# -------------------------------
# 引数受け取り(CSVファイル名 + Excel情報)
# -------------------------------
csv_parser = argparse.ArgumentParser()
csv_parser.add_argument("--csv_name", required=True)
csv_parser.add_argument("csv_row_json", help="JSON文字列で1行分のデータ")
csv_args = csv_parser.parse_args()
csv_name =csv_args.csv_name
excel_data_name = csv_args.excel_data
csv_row_json = csv_args.csv_row_json
upload_csv_row = json.loads(csv_row_json) # JSONを辞書に変換

print(f"受け取ったCSVファイル名: {csv_name}")
print(f"受け取ったCSV行データ(JSON): {csv_row_json}")


# -------------------------------
# ini の読み込み（絶対パスで）
# -------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # /app/app
ini_path = os.path.join(BASE_DIR, "config", "config.ini")   # 設定ファイル　/app/config/config.ini
print(f"config.ini のパス: {ini_path}")

ini = configparser.ConfigParser()
ret = ini.read(ini_path, 'UTF-8')
if not ret:
    print("config.ini が読み込めませんでした")




# csvから取得予定
DateNo = upload_csv_row.get("DateNo", "")
print(f"DateNo: {DateNo}")

# サーバー情報（config.ini から取得予定）
# ServPathK = "Temp/*****/"

ServPathK = ini['upload_info']['Kanshi_Path']
ServPathH = ini['upload_info']['Handan_Path']

# アップロードファイル名(CSVもしくは生成状況から取得予定)
UpFileName = "*****"
HostName = ini['upload_info']['Host_Server']
UserName = ini['upload_info']['Host_User']
PassWD = ini['upload_info']['Host_Pass']



# 監視者のPath
ServPath = ServPathK + DateNo
# 判断者のPath
ServPath = ServPathK + DateNo

# Fileアップロード
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HostName, username=UserName, password=PassWD)
sftp = ssh.open_sftp()
# Path の確認*******************************
dir_path = Path(ServPath)
# ディレクトリが存在しない場合は作成
dir_path.mkdir(parents=True, exist_ok=True)
# ここまで**********************************

sftp.put(UpFileName, ServPath+UpFileName)

sftp.close()
ssh.close()