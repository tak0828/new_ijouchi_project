import os
import configparser
import smtplib
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from os.path import basename


# -------------------------------
# ini の読み込み（絶対パスで）
# -------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # /app
ini_path = os.path.join(BASE_DIR, "config", "config.ini")               # /app/config/config.ini
print(f"config.ini のパス: {ini_path}")

ini = configparser.ConfigParser()
ret = ini.read(ini_path, 'UTF-8')
if not ret:
    print("config.ini が読み込めませんでした")


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
            # MIMEの作成
        subject = ini['Mail_sbj']['Mail_subject']
        message = ini['Mail_sbj']['Mail_message']
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["To"] = to_email
        msg["From"] = from_email
        msg.attach(MIMEText(message))
        
        filepath = ini['File_Path']['filepath']

        #ファイル添付
        #for分により添付ファイルを設定
        #****************************************
        # 添付ファイル名のセット
        
        # T_filename = 
        # path = filepath + T_filename
        
        #****************************************
        with open(path, "rb") as e:
            part = MIMEApplication(
                e.read(),
                Name=basename(path)
            )
            # zip, excel等の圧縮ファイルを送る場合は以下のコメントアウトを外す
        part['Content-Disposition'] = 'attachment; filename="%s"' % basename(path)
        msg.attach(part)
        #ここまで************************************************
          
        #(3) SMTPクライアントインスタンスを作成する
        servSMTP='smtp.office365.com'
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
        
    except:
        return False

#result=send_mail()
#print(result)

if __name__ == "__main__":
    send_mail()
    print("メール送信が完了しました")
