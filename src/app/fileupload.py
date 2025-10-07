import os
import json
import argparse
import configparser
import paramiko
import sys
from pathlib import Path



def execute_fileupload_processing(csv_rows, csv_file_name, TempFile_results):
    try:
        # -------------------------------
        # ini の読み込み
        # -------------------------------
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        ini_path = os.path.join(BASE_DIR, "config", "config.ini")
        print(f"config.ini のパス: {ini_path}")

        ini = configparser.ConfigParser()
        if not ini.read(ini_path, 'UTF-8'):
            print("config.ini が読み込めませんでした")
            return False

        # サーバー情報
        ServPathK = ini['upload_info']['Kanshi_Path']
        ServPathH = ini['upload_info']['Handan_Path']
        TempPath_dir = ini['File_Path']['png_filepath']
        HostName = ini['upload_info']['Host_Server']
        UserName = ini['upload_info']['Host_User']
        PassWD = ini['upload_info']['Host_Pass']

        # SSH/SFTP 接続
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(HostName, username=UserName, password=PassWD)
        sftp = ssh.open_sftp()

        for rows in csv_rows:
            # csvのDateNo
            DateNo = str(rows.get("DateNo", ""))
            print(f"\nProcessing DateNo: {DateNo}")

            for i, row in enumerate(TempFile_results):
                # TempFile_resultsのDateNo
                PathDateNo = str(row[0]).replace("/", "")
                if PathDateNo != DateNo:
                    continue  # DateNoが一致しない場合はスキップ

                # アップロード先ディレクトリ作成
                UpServPathK = ServPathK + PathDateNo + "/"
                UpServPathH = ServPathH + PathDateNo + "/"

                ssh.exec_command(f'mkdir -p {UpServPathK}')
                ssh.exec_command(f'mkdir -p {UpServPathH}')

                # 1列目以降はファイル名
                for j, value in enumerate(row[1:], start=1):
                    if value == "0":
                        continue

                    TempPath_local = os.path.join(TempPath_dir, value)
                    if not os.path.exists(TempPath_local):
                        continue

                    # 判断者ディレクトリへアップロード
                    # 判断者のPath　/home/surveydb/SurveyDB/media/Temp/調査書/判断者/
                    remote_path = UpServPathH + value

                    # 判断者のPathへアップロード(今回は判断者のみにアップロード(下段)）
                    sftp.put(TempPath_local, remote_path)

        print("ファイルアップロード完了")

        sftp.close()
        ssh.close()

        return True

    except Exception as e:
        print(f"ファイルアップロードでエラー: {e}")
        return False
