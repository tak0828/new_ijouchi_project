import json
import glob
import os
import configparser
import argparse
import smtplib
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from os.path import basename
from openpyxl import Workbook  # Excel生成用

# -------------------------------
# 引数受け取り(CSVファイル名 + Excel情報)
# -------------------------------
csv_parser = argparse.ArgumentParser()
csv_parser.add_argument("--csv_name", required=True)
csv_parser.add_argument("--excel_data", required=False, help="カンマ区切りでExcelに書き込むデータ")
csv_parser.add_argument("csv_row_json", help="JSON文字列で1行分のデータ")
csv_args = csv_parser.parse_args()
csv_name =csv_args.csv_name
excel_data_name = csv_args.excel_data
csv_row_json = csv_args.csv_row_json
temp_csv_row = json.loads(csv_row_json) # JSONを辞書に変換

print(f"受け取ったCSVファイル名: {csv_name}")
print(f"受け取ったExcelデータ名: {excel_data_name}")
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


# -------------------------------
# Excel作成関数
# -------------------------------
def create_excel_file(temp_csv_row, excel_path):
    """
    temp_csv_row: dict (1行分のデータ)
    excel_path: 保存する Excel ファイルパス
    """

    # 更新内容「ヘッダー行」
    headers = ["DateNo", "観測日時", "項目種別", "観測所名", "水系名", "管理者", "管理区分"]

    wb = Workbook()
    ws = wb.active
    ws.title = "更新内容"

    # ヘッダー書き込み
    ws.append(headers)

    # 値を抽出して2行目に書き込み
    excel_row_values = [
        temp_csv_row.get("DateNo", ""),
        temp_csv_row.get("観測日時", ""),
        temp_csv_row.get("項目種別", ""),
        temp_csv_row.get("観測所名", ""),
        temp_csv_row.get("水系名", ""),
        temp_csv_row.get("管理者", ""),
        temp_csv_row.get("管理区分", "")
    ]
    ws.append(excel_row_values)

    # 更新内容エクセル保存
    wb.save(excel_path)
    print(f"Excel作成完了: {excel_path}")




# -------------------------------
# メール送信関数
# -------------------------------
def send_mail():
    try: 
        flg_mail=0
        # SMTP認証情報
        account = ini['mail_info']['FROM_ADDRESS']
        password = ini['mail_info']['MY_PASSWORD']
        # 送受信先
        to_email = ini['mail_info']['to_email']
        from_email = ini['mail_info']['from_email']

        #************************************************
        # MIMEの作成 (件名・本文に CSV名を追加)
        #************************************************
        subject = f"{csv_name}：{ini['Mail_sbj']['Mail_subject']}"
        message = f"{csv_name}：{ini['Mail_sbj']['Mail_message']}"
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["To"] = to_email
        msg["From"] = from_email
        msg.attach(MIMEText(message))
        


        # ここでメール送信処理（MIMEText 等）
        print(f"送信先: {to_email}")
        print(f"件名: {subject}")
        print(f"本文: {message}")

        #ファイル添付
        #for分により添付ファイルを設定
        #****************************************
        # 添付ファイル名のセット(添付ファイルの準備)
        mail_attach_files = []

        # 1. zipファイル（既存すべて）
        zip_filepath = ini['File_Path']['zip_filepath']
        for zip_path in glob.glob(os.path.join(zip_filepath, "*.zip")):
            if os.path.isfile(zip_path):
                mail_attach_files.append(zip_path)

        # # 確認用
        # print("添付ファイル一覧:")
        # for f in mail_attach_files:
        #     print(f)


        # 2. Excelファイル（生成）
        excel_filepath = ini['File_Path']['excel_filepath']

        if excel_data_name:
            os.makedirs(excel_filepath, exist_ok=True)
            excel_path = os.path.join(excel_filepath, f"{excel_data_name}.xlsx")
            create_excel_file(temp_csv_row, excel_path)
            mail_attach_files.append(excel_path)

        # 添付処理
        for path in mail_attach_files:
            with open(path, "rb") as f:
                part = MIMEApplication(f.read(), Name=basename(path))
                part['Content-Disposition'] = f'attachment; filename="{basename(path)}"'
                msg.attach(part)
            print(f"添付: {path}")

        
        # T_filename = 
        # path = filepath + T_filename
        
        #****************************************

        # with open(path, "rb") as e:
        #     part = MIMEApplication(
        #         e.read(),
        #         Name=basename(path)
        #     )
        #     # zip, excel等の圧縮ファイルを送る場合は以下のコメントアウトを外す(ファイルパスから)


        # part['Content-Disposition'] = 'attachment; filename="%s"' % basename(path)
        # msg.attach(part)
        #ここまで************************************************
          
        #(3) SMTPクライアントインスタンスを作成する
        servSMTP='mail.biglobe.ne.jp' #SMTPサーバー
        portNo=('starttls',587) #通信方式、ポート番号

        smtp = smtplib.SMTP(servSMTP, portNo[1])
        smtp.set_debuglevel(True) # サーバとの通信内容を表示する
        # SMTP サーバへの接続とメールの送信
        smtp.ehlo()
            # (250, ...
        smtp.starttls()  # TLS の開始（以降の通信は暗号化される）
        #     (220, b'2.0.0 SMTP server ready') 
        smtp.ehlo()
        #     (250, ...
        smtp.login(account, password)  # SMTP サーバにログイン
            # (235, ...
        smtp.send_message(msg)  # メッセージの送信
            # {}
        smtp.quit()  # SMTP セッションの終了と TCP コネクションの切断
            # (221, b'2.0.0 Service closing transmission channel')

        # smtpclient.send_message(msg)
        # smtpclient.quit()
        
    except Exception as e:
        print(f"メール送信でエラー発生: {e}")
        return False


send_mail()


if __name__ == "__main__":
    send_mail()
    print("メール送信が完了しました")
