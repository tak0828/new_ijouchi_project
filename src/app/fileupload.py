import os
import json
import argparse
import configparser
import paramiko
import sys
from pathlib import Path



# # -------------------------------
# # 引数受け取り(CSVファイル名 + Excel情報)
# # -------------------------------
# csv_parser = argparse.ArgumentParser()
# csv_parser.add_argument("--csv_name", required=True)
# csv_parser.add_argument("csv_row_json", help="JSON文字列で1行分のデータ")
# csv_args = csv_parser.parse_args()
# csv_name =csv_args.csv_name
# csv_row_json = csv_args.csv_row_json
# upload_csv_row = json.loads(csv_row_json) # JSONを辞書に変換

# print(f"受け取ったCSVファイル名: {csv_name}")
# print(f"受け取ったCSV行データ(JSON): {csv_row_json}")

parser = argparse.ArgumentParser()
parser.add_argument("--csv_name", required=True)
parser.add_argument("--excel_data", required=True)
parser.add_argument("csv_row_json", help="JSON文字列で1行分のデータ")
parser.add_argument("TempFile_results", help="JSON文字列でTempFile_results")
args = parser.parse_args()

csv_name = args.csv_name
# excel_data = args.excel_data

# JSON文字列を辞書に変換
upload_csv_row = json.loads(args.csv_row_json)
# TempFile_results = json.loads(json.loads(args.tempfile_results_json))["TempFile_results"]
TempFile_results = json.loads(args.TempFile_results)


print(f"受け取ったCSVファイル名: {csv_name}")
print(f"受け取ったCSV行データ(JSON): {upload_csv_row}")
print(f"受け取ったTempFile_results(JSON): {TempFile_results}")


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


# args.csv_row_json が二重JSONの場合
try:
    upload_csv_row = json.loads(args.csv_row_json)
    if isinstance(upload_csv_row, str):
        upload_csv_row = json.loads(upload_csv_row)
except json.JSONDecodeError as e:
    print("CSV行JSONの読み込みに失敗:", e)
    upload_csv_row = {}


# csvから取得予定
DateNo = upload_csv_row.get("DateNo", "")
print(f"DateNo: {DateNo}")

# サーバー情報（config.ini から取得予定）
# ServPathK = "Temp/*****/"

ServPathK = ini['upload_info']['Kanshi_Path']
ServPathH = ini['upload_info']['Handan_Path']

# 保存添付ファイルのディレクトリ(そのままだとカレントディレクトリでしかファイルを探せないのでconfig.ini から取得予定)
TempPath_dir= ini['File_Path']['png_filepath']

# アップロードファイル名(CSVもしくは生成状況から取得予定)
UpFileName = csv_name
HostName = ini['upload_info']['Host_Server']
UserName = ini['upload_info']['Host_User']
PassWD = ini['upload_info']['Host_Pass']

# Fileアップロード
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HostName, username=UserName, password=PassWD)
sftp = ssh.open_sftp()

# 新しい辞書形式のTempFile_resultsを処理
for date_no, entry in TempFile_results.items():
    if date_no == DateNo:
        print(f"Match found for DateNo: {date_no}")
        
        # Pathの作成
        PathDateNo = date_no.replace("/", "")
        
        # 監視者のPath
        UpServPathK = ServPathK + PathDateNo + "/"
        # ディレクトリが存在しない場合は作成
        stdin, stdout, stderr = ssh.exec_command(f'mkdir -p {UpServPathK}')
        print(stdout.read().decode())
        print(stderr.read().decode())

        # 判断者のPath
        UpServPathH = ServPathH + PathDateNo + "/"
        # ディレクトリが存在しない場合は作成
        stdin, stdout, stderr = ssh.exec_command(f'mkdir -p {UpServPathH}')
        print(stdout.read().decode())
        print(stderr.read().decode())
        
        # 添付ファイルの処理
        attached_files = entry.get("attached_files", [])
        for filename in attached_files:
            if isinstance(filename, str) and filename != "0":
                print(f"Uploading file: {filename}")
                
                # ローカルファイルパス
                TempPath_local = os.path.join(TempPath_dir, filename)
                print(f"Local file path to upload: {TempPath_local}")
                
                # 判断者のPathへアップロード
                sftp.put(TempPath_local, UpServPathH + filename)
                print(f"Uploaded {filename} to {UpServPathH}")
            elif isinstance(filename, str) and filename == "0":
                print(f"No file to upload: {filename}")
                continue



sftp.close()
ssh.close()