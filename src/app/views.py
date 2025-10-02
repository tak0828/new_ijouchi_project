from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from app.models import  WatchStatus
from datetime import datetime, timedelta

import json
import sys
import os
import subprocess
import csv
import pymysql


def login_view(request):
    message = ""
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)  # セッションに保存
            return redirect("home")  # ログイン後に /home/ へ
        else:
            message = "ユーザー名またはパスワードが違います"

    return render(request, "registration/login.html", {"message": message})

def Chousasho_insert_into_table(cursor, Chousasho_table_name, columns, values):
    """
    汎用INSERT関数
    """
    columns_str = ", ".join(columns)
    placeholders = ", ".join(["%s"] * len(columns))
    sql = f"INSERT INTO {Chousasho_table_name} ({columns_str}) VALUES ({placeholders})"
    cursor.execute(sql, values)



# -----------------------sendmail.pyを実行----------------------------------------------------
def run_sendmail(csv_filename, row_json, csv_file_path, csv_row_json):
    # sendmail.py のパス
    SendMail_path = os.path.join(settings.BASE_DIR, "app", "sendmail.py")
    print(f"sendmail.py のパス: {SendMail_path}")  # 確認用

    # メール件名・本文に CSVファイル名を追加
    csv_file_name= os.path.basename(csv_file_path).replace(".csv", "")


    try:
        # subprocess で sendmail.py を実行する
        sendmail_result = subprocess.run(
                [sys.executable, SendMail_path, "--csv_name", csv_file_name,
                "--excel_data", csv_file_name + "更新結果", csv_row_json],      # コンテナの Python を使う( csvファイル名, excelファイル名, csv_json(DateNo等）を引数で渡す)
                check=True,
                cwd=os.path.dirname(SendMail_path),    # /app/app をカレントディレクトリに
                capture_output=True,                    # stdout をキャプチャ
                text=True,
                encoding='utf-8'  # エンコーディングを指定
            )

        print("sendmail.py が正常に実行されました")
        
    except subprocess.CalledProcessError as e:  
        print(f"sendmail.py の実行中にエラーが発生しました: {e}")   
# -----------------------sendmail.pyを実行----------------------------------------------------
# -----------------------fileupload.pyを実行----------------------------------------------------
def run_fileupload(csv_row_json, csv_file_path, TempFile_results):
    # fileupload.py のパス
    fileupload_path = os.path.join(settings.BASE_DIR, "app", "fileupload.py")
    print(f"fileupload.py のパス: {fileupload_path}")  # 確認用

    csv_file_name = os.path.basename(csv_file_path).replace(".csv", "")

    try:
        fileupload_result = subprocess.run(
            [sys.executable, fileupload_path,
            "--csv_name", csv_file_name,
            "--excel_data", csv_file_name + "更新結果",
            json.dumps(csv_row_json, ensure_ascii=False),
            json.dumps(TempFile_results, ensure_ascii=False)],
            check=True,
            cwd=os.path.dirname(fileupload_path),
            capture_output=True,
            text=True,
            encoding='utf-8'
        )

        print("fileupload.py が正常に実行されました")
        
    except subprocess.CalledProcessError as e:  
        print(f"fileupload.py の実行中にエラーが発生しました: {e}")

# -----------------------fileupload.pyを実行----------------------------------------------------









@login_required
def home_view(request):
    # 監視状態を取得（なければ作成）
    watch_status, created = WatchStatus.objects.get_or_create(
        defaults={'is_watching': False}
    )
    
    context = {
        'watch_status': watch_status,
        'is_watching': watch_status.is_watching,
    }
    return render(request, "registration/home.html", context)

@login_required
def logout_view(request):
    logout(request)
    return redirect("login")



@login_required
@require_POST
@csrf_exempt


def toggle_watch(request):
    """CSV監視の開始・停止を切り替え"""
    try:
        data = json.loads(request.body)
        action = data.get('action')
        
        watch_status, created = WatchStatus.objects.get_or_create(
            defaults={'is_watching': False}
        )
        if action == 'start':
            watch_status.is_watching = True
            watch_status.save()

            # CSVファイルのパス（例としてプロジェクトの雨量_注意_新潟デモ.csvを使用）
            csv_file_path = os.path.join(settings.BASE_DIR, "csv", "雨量_注意_新潟デモ.csv")

            # ファイル名から種別、警戒レベル、期間を取得
            file_name = os.path.basename(csv_file_path).replace(".csv", "")  # '雨量_注意_新潟デモ'
            file_parts = file_name.split("_")
            global csv_filename
            csv_filename = file_name

            Shubetsu_level = file_parts[0] if len(file_parts) > 0 else None  # 種別
            Keikai_level = file_parts[1] if len(file_parts) > 1 else None    # 警戒レベル
            j = 0
            # CSV読み込み処理
            try:
                csv_rows = []
                with open(csv_file_path, encoding="cp932") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        j = j + 1    
                        Dt_str = row.get("観測日時")
                        Cd2_str = row.get("統一ID")
                        Kessoku_str = row.get("欠測・未受信")
                        if not Dt_str or not Cd2_str:
                            continue
                        
                        csv_dt = datetime.strptime(Dt_str.strip(), "%Y/%m/%d %H:%M")
                        year_ago = csv_dt - timedelta(days=365)
                        date_str = csv_dt.strftime("%Y/%m/%d")  # DateNo用の文字列 "2025/06/29"
                        print(date_str)
                        
                        # 欠測・基準値超過フラグ
                        is_missing = False
                        is_exceed = False
                        if Kessoku_str is not None:
                            Kessoku_val = Kessoku_str.strip()
                            if Kessoku_val in ["欠測", "未受信", "-"]:
                                is_missing = True
                            elif Kessoku_val == "":  # 空白セル → 基準値超過
                                is_exceed = True

                        # 近隣観測所フラグ
                        is_kinbou = False

                        csv_rows.append({
                            "統一ID": Cd2_str.strip(),
                            "観測日時": csv_dt,
                            "1年前日時": year_ago,
                            # "開始日時": start_dt,
                            "項目種別": row.get("項目種別"),
                            "水水ID": row.get("水水ID"),
                            "観測所名": row.get("観測所名"),
                            "地方名": row.get("地方名"),
                            "水系名": row.get("水系名"),
                            "河川名": row.get("河川名"),
                            "管理者": row.get("管理者"),
                            "管理区分": row.get("管理区分"),
                            "観測値": row.get("観測値"),
                            "近傍観測所1のID": row.get("近傍観測所1のID"),
                            "近傍観測所1の名称": row.get("近傍観測所1の名称"),
                            "近傍観測所1の観測値": row.get("近傍観測所1の観測値"),
                            "近傍観測所2のID": row.get("近傍観測所2のID"),
                            "近傍観測所2の名称": row.get("近傍観測所2の名称"),
                            "近傍観測所2の観測値": row.get("近傍観測所2の観測値"),
                            "近傍観測所3のID": row.get("近傍観測所3のID"),
                            "近傍観測所3の名称": row.get("近傍観測所3の名称"),
                            "近傍観測所3の観測値": row.get("近傍観測所3の観測値"),
                            "IDW推定値": row.get("IDW推定値"),
                            "メッシュコード": row.get("メッシュコード"),
                            "レーダ雨量": row.get("レーダ雨量"),
                            "IDW異常": row.get("IDW異常"),
                            "上限値": row.get("上限値"),
                            "欠測・未受信": is_missing,
                            "基準値超過": is_exceed,
                            "連続する異常値": row.get("連続する異常値"),
                            "近傍観測所フラグ": is_kinbou # 近傍観測所フラグを追加(初期値False)
                        })


                if not csv_rows:
                    print("CSVに有効な行がありません")
                    return JsonResponse({"status": "no_data"})



                # MariaDB接続（今回は193サーバーのIjouchiDBV6を使用）
                conn = pymysql.connect(
                    host='192.168.99.193',
                    user='frics',
                    password='fricsV6',
                    database='IjouchiDBV6',
                    charset='utf8mb4'
                )

                cursor = conn.cursor(pymysql.cursors.DictCursor)

                # 統一IDから MS_KansokujoからKansokujoCD を取得(緯度経度も取得20250922)(近傍観測所のID情報も取得20250926)(JimushoCDがJimushoCD2ではなくIDなのでMS_JimushoからJimushoCDを取得するように変更20250929)
                KansokujoCD2_list = list({r["統一ID"] for r in csv_rows})  # 重複排除
                placeholders = ','.join(['%s'] * len(KansokujoCD2_list))
                sql = f"SELECT KansokujoCD, ShubetsuCD, JimushoCD, KasenCD, KenCD, SuikeiCD, KansokujoCD2, Ido, Keido, CenterCD FROM MS_Kansokujo WHERE KansokujoCD2 IN ({placeholders})"
                cursor.execute(sql, KansokujoCD2_list)
                MS_Kansokujo_results = cursor.fetchall()
                if not MS_Kansokujo_results:
                    print("MS_Kansokujo に一致するレコードがありません")
                    conn.close()
                    return JsonResponse({"status": "no_ms_record"})

                # 事務所CDがJimushoCD2ではなくIDなのでMS_JimushoからJimushoCDを取得するように変更20250929
                JimushoID_list = [r["JimushoCD"] for r in MS_Kansokujo_results]
                Jimusho_placeholders = ','.join(['%s'] * len(JimushoID_list))
                sql_jimusho = f"""
                    SELECT id, JimushoCD2
                    FROM MS_Jimusho
                    WHERE id IN ({Jimusho_placeholders})
                    """
                cursor.execute(sql_jimusho, JimushoID_list)
                MS_Jimusho_results = cursor.fetchall()

                # 事務所CDを辞書化: id → JimushoCD2
                MS_Jimusho_dict = {r["id"]: r["JimushoCD2"] for r in MS_Jimusho_results}


                # MS_Kansokujo を辞書化: KansokujoCD2 → (KansokujoCD, ShubetsuCD)
                MS_Kansokujo_dict = {r["KansokujoCD2"]: (r["KansokujoCD"], r["ShubetsuCD"], r["KasenCD"], r["KenCD"], MS_Jimusho_dict.get(r["JimushoCD"]), r["SuikeiCD"], r["Ido"], r["Keido"], r["CenterCD"] ) for r in MS_Kansokujo_results}

                # 各CSV行ごとに DS_ChousaMeisai 件数取得(1年前～観測日時) 
                DS_ChousaKihon_counts = []
                seq_dict = {}  # 観測所ごとの連番保持用辞書
                h = 0
                for r in csv_rows:
                    cd2 = r["統一ID"]
                    if cd2 not in MS_Kansokujo_dict:
                        continue
                    KansokujoCD, ShubetsuCD, KasenCD, KenCD, JimushoCD, SuikeiCD, Ido, Keido, CenterCD = MS_Kansokujo_dict[cd2]
                    
                    sql2 = """
                        SELECT DateNo
                        FROM DS_ChousaMeisai
                        WHERE KansokujoCD = %s
                        AND ShubetsuCD = %s
                        AND STR_TO_DATE(LEFT(DateNo,10),'%%Y/%%m/%%d') BETWEEN %s AND %s
                    """
                    params = [KansokujoCD, ShubetsuCD, r["1年前日時"].strftime("%Y/%m/%d"), r["観測日時"].strftime("%Y/%m/%d")]
                    cursor.execute(sql2, params)
                    DateNo_results = cursor.fetchall()
                    DateNo_list = [DateNo_row["DateNo"] for DateNo_row in DateNo_results]


                    # "雨量"かつ"注意"かつ基準値超過の場合のみ処理
                    if Shubetsu_level == '雨量' and Keikai_level == '注意' and r.get('基準値超過', False):
                        Latest_row = None
                        # 取得した DateNo で DS_ChousaKihonレコードを取得(HasseiJoukyouCD='845108' の最新レコード1件だけ取得)
                        DS_ChousaKihon_results = []

                        # TempFile_results = []
                        rows, cols = j, 11  
                        TempFile_results = [["0" for _ in range(cols)] for _ in range(rows)]

                        # TempFile_results = [[0]*11]*K  --- TempFile_results[0][K]=DateNo  TempFile_results[1-10][K]=添付ファイル---
                        # TempFile_results = [****-001, 0,0,0,0,0,0,0,0,0,0
                        #                     ****-002, 0,0,0,0,0,0,0,0,0,0]
                        
                        
                        for DateNo in DateNo_list:
                            sql3 = """
                                SELECT *
                                FROM DS_ChousaKihon
                                WHERE DateNo = %s
                                AND HasseiJoukyouCD = '845108'
                                ORDER BY DateNo DESC
                                LIMIT 1
                            """
                            cursor.execute(sql3, [DateNo])
                            DS_ChousaKihon_row = cursor.fetchone()
                            if DS_ChousaKihon_row:
                                DS_ChousaKihon_results.append(DS_ChousaKihon_row)

                                if (Latest_row is None) or (DS_ChousaKihon_row["DateNo"] > Latest_row["DateNo"]):
                                    Latest_row = DS_ChousaKihon_row

                        print(f"統一ID {cd2} の最新 DS_ChousaKihon.DateNo (HasseiJoukyouCD=845108): {Latest_row['DateNo'] if Latest_row else None}")
                        # for col, val in Latest_row.items():  # カラム名と値を一覧で表示
                        #     print(f"  {col}: {val}")

                        # DS_ChousaIjouchiSuiteiGenin を DateNoとCenterCD で推定原因、原因発生個所、繰り返し発生の有無取得
                        if Latest_row:
                            sql4 = """
                                SELECT CISG_GeninKashoKbn, CISG_HasseiUM, CISG_SuiteiGeninKbn
                                FROM DS_ChousaIjouchiSuiteiGenin
                                WHERE DateNo = %s
                                AND CenterCD = %s
                                """
                            cursor.execute(sql4, [Latest_row["DateNo"], Latest_row["CenterCD"]])
                            DS_ChousaIjouchiSuiteiGenin_row = cursor.fetchone()

                            print(f"DS_ChousaIjouchiSuiteiGenin (DateNo={Latest_row['DateNo']}, CenterCD={Latest_row['CenterCD']}) 件数: {len(DS_ChousaIjouchiSuiteiGenin_row)}")

                            
                        # -----------------------データベース登録-----------------------------------------------
                            # DS_ChousaKihon の新規登録

                            # DB用に分割
                            KakuninDate = csv_dt.strftime("%Y-%m-%d")   # "2025-06-29"
                            KakuninTime = csv_dt.strftime("%H:%M")      # "16:50"

                            # その日付の既存DateNoを取得
                            DateNo_check_sql = """
                                SELECT DateNo FROM DS_ChousaKihon
                                WHERE DateNo LIKE %s AND CenterCD=%s
                                ORDER BY DateNo DESC
                            """
                            cursor.execute(DateNo_check_sql, [f"{date_str}-%", Latest_row["CenterCD"]])
                            DateNo_existing = cursor.fetchall()

                            if DateNo_existing:
                                # 既存DateNoの最大連番を取得
                                DateNo_last_no = max(int(row['DateNo'].split("-")[1]) for row in DateNo_existing)
                                DateNo_New_no = f"{DateNo_last_no + 1:03d}"
                            else:
                                DateNo_New_no = "001"

                            TempFile_results[0][h] = f"{date_str}-{DateNo_New_no}"  # 1列目に DateNo をセット
                            h = h + 1

                            DateNo_New = f"{date_str}-{DateNo_New_no}"
                            print("新規DateNo:", DateNo_New)

                            # DateNoをリストに追加
                            DateNo_list.append(DateNo_New)

                            # -----------------------attached_file.pyを実行-----------------------------------------------
                            for test_csv_row in csv_rows:

                                test_csv_row = test_csv_row.copy()

                                # datetime を文字列に変換
                                if isinstance(test_csv_row["観測日時"], datetime):
                                    test_csv_row["観測日時"] = test_csv_row["観測日時"].strftime("%Y/%m/%d %H:%M")
                                if isinstance(test_csv_row["1年前日時"], datetime):
                                    test_csv_row["1年前日時"] = test_csv_row["1年前日時"].strftime("%Y/%m/%d %H:%M")

                                # ディレクトリ判定になるため　/ を - に置換
                                # 1.DateNo を追加※日付部分を置換（YYYY/MM/DD → YYYYMMDD）
                                date_part = DateNo_New.split("-")[0].replace("/", "")   # "20250629"

                                # 2. 連番部分をゼロパディング
                                serial_part = DateNo_New.split("-")[1].zfill(3)         # "003"

                                # 3. 結合
                                DateNo_CSV = f"{date_part}-{serial_part}"         # "20250629-003"  
                                test_csv_row["DateNo"] = DateNo_CSV

                                # 緯度経度を追加
                                test_csv_row["緯度"] = Ido
                                test_csv_row["経度"] = Keido
                                
                                # CenterCDを追加
                                test_csv_row["地方CD"] = CenterCD

                                if is_kinbou:
                                    # 近傍観測所1～3を順に追加
                                    kinbou_flags = {}  # 近傍観測所フラグ初期化
                                    for i in range(1, 4):
                                        kinbou_key = f"近傍観測所{i}のID"
                                        kinbou_cd2 = test_csv_row.get(kinbou_key)
                                        # 近傍観測所フラグをDBに統一ID(KansokujoCD2登録があるものを判別するため)
                                        kinbou_flags[i] = False  # 初期値False

                                        # IDが空白の場合はスキップ
                                        if not kinbou_cd2:
                                            continue

                                        # DBから近傍観測所の情報を取得
                                        sql = """
                                            SELECT KansokujoCD, ShubetsuCD, JimushoCD, KasenCD, KenCD, SuikeiCD,
                                                KansokujoCD2, Ido, Keido, CenterCD
                                            FROM MS_Kansokujo
                                            WHERE KansokujoCD2 = %s
                                        """
                                        cursor.execute(sql, [kinbou_cd2])
                                        kinbou_row = cursor.fetchone()
                                        if not kinbou_row:
                                            print(f"近傍観測所{i}:{kinbou_cd2} は MS_Kansokujo に存在しません")
                                            continue

                                        # # 近傍観測所情報を追加
                                        # test_csv_row[f"近傍観測所{i}_KansokujoCD"] = kinbou_row["KansokujoCD"]
                                        # test_csv_row[f"近傍観測所{i}_ShubetsuCD"] = kinbou_row["ShubetsuCD"]
                                        # test_csv_row[f"近傍観測所{i}_KasenCD"] = kinbou_row["KasenCD"]
                                        # test_csv_row[f"近傍観測所{i}_KenCD"] = kinbou_row["KenCD"]
                                        # test_csv_row[f"近傍観測所{i}_JimushoCD"] = kinbou_row["JimushoCD"]
                                        # test_csv_row[f"近傍観測所{i}_SuikeiCD"] = kinbou_row["SuikeiCD"]
                                        # test_csv_row[f"近傍観測所{i}_統一ID"] = kinbou_row["KansokujoCD2"]
                                        # test_csv_row[f"近傍観測所{i}_緯度"] = kinbou_row["Ido"]
                                        # test_csv_row[f"近傍観測所{i}_経度"] = kinbou_row["Keido"]
                                        # test_csv_row[f"近傍観測所{i}_地方CD"] = kinbou_row["CenterCD"]
                                        
                                        # 近傍観測所フラグをTrueに設定
                                        kinbou_flags[i] = True
                                        test_csv_row[f"近傍観測所{i}フラグ"] = True
                                        # 既存の test_csv_row の後ろに追加
                                        print(test_csv_row)
                                        print(f"近傍観測所 {kinbou_cd2} の情報を追加しました")

                                # CSV行をJSON文字列に変換
                                csv_row_json = json.dumps(test_csv_row, ensure_ascii=False)
                                data = {"TempFile_results": TempFile_results}
                                TempFile_results = json.dumps(data, ensure_ascii=False)

                                # attached_file.py のパス
                                attached_file_path = os.path.join(settings.BASE_DIR, "app", "attached_file.py")
                            
                                try:
                                    # subprocess で attached_file.py を実行し、標準出力を取得
                                    temp_result = subprocess.run(
                                            [sys.executable, attached_file_path, csv_row_json, TempFile_results, csv_filename],      # コンテナの Python を使う(csvを引数で渡す(json文字列))
                                            check=True,
                                            cwd=os.path.dirname(attached_file_path),    # /app/app をカレントディレクトリに
                                            capture_output=True,                    # stdout をキャプチャ
                                            text=True,
                                            encoding='utf-8'  # エンコーディングを指定
                                        )

                                    print("attached_file.py が正常に実行されました")
                                    
                                    # あとで直す(print活用しない)
                                    # 標準出力を確認
                                    stdout_lines = temp_result.stdout.strip().splitlines()
                                    json_temp_str = stdout_lines[-2]  # 最後の2行目(添付ファイルのリスト)
                                    json_str = stdout_lines[-1]  # 最後の行(添付ファイルアップロードパス)
                                    output_json = json.loads(json_str)

                                    # 添付ファイルのリストを取得
                                    TempFile_results = json.loads(json_temp_str)

                                    # 標準出力からパスを取り出す
                                    TempFilePath1 = output_json["TempFilePath1"] or ''
                                    TempFilePath2 = output_json["TempFilePath2"] or ''
                                    TempFilePath3 = output_json["TempFilePath3"] or ''
                                    TempFilePath4 = ''
                                    TempFilePath5 = ''
                                    # TempFilePath4 = output_json["TempFilePath4"] or ''
                                    # TempFilePath5 = output_json["TempFilePath5"] or ''


                                    print("取得したファイルパス:", TempFilePath1, TempFilePath2, TempFilePath3)
                                
                                except subprocess.CalledProcessError as e:  
                                    print(f"attached_file.py の実行中にエラーが発生しました: {e}")
                                    return JsonResponse({"status": "attached_file_error", "message": str(e)})
                                
                            
                            # -----------------------attached_file.pyを実行-----------------------------------------------

                            # -----------------------sendmail.pyを実行----------------------------------------------------
                            # 関数化後
                            run_sendmail(csv_filename, row, csv_file_path, csv_row_json)
                           
                            # -----------------------fileupload.pyを実行----------------------------------------------------

                            # 関数化後
                            run_fileupload(csv_row_json, csv_file_path, TempFile_results)

                            # -----------------------fileupload.pyを実行----------------------------------------------------

                            # 次の MeisaiNo
                            next_seq = seq_dict.get(KansokujoCD, 1)
                            seq_dict[KansokujoCD] = next_seq + 1

                            # CreateTime, UpdateTime は現在日時で作成
                            create_now = datetime.now()
                            create_time = create_now.strftime("%Y-%m-%d %H:%M:%S.") + f"{int(create_now.microsecond/1000):03d}"
                            update_now = datetime.now()
                            update_time = update_now.strftime("%Y-%m-%d %H:%M:%S.") + f"{int(update_now.microsecond/1000):03d}"


                            # 挿入データまとめ
                            Chousasho_insert_data = {
                                "DS_ChousaKihon": {
                                    "columns": ["DateNo", "CenterCD", "HasseiJoukyouCD",
                                                "KakuninDate", "KakuninTime",
                                                "IjouKessokuKbnCD", "JK_Kbn", "KanriCD", "ShozokuCD", "DenwaKaitou", "Shubetsu01",
                                                "Shubetsu02","Shubetsu03","Shubetsu04","Shubetsu05","Shubetsu06","Shubetsu07","Shubetsu08",
                                                "Shubetsu09", "HasseiKeii" ,"HakkenHouhouCD", "KKShubetsuCD",
                                                "KanshiTempFile01", "KanshiTempFile02", "KanshiTempFile03", "KanshiTempFile04", "KanshiTempFile05", #添付ファイル(上側)のカラム追加
                                                "SeqNo", "StartDate", "StartTime", "CreateTime", "UpdateTime", "FormatType", "KenCD"], #足りないカラムを追加
                                    "values": [DateNo_New, Latest_row["CenterCD"], Latest_row.get("HasseiJoukyouCD"),
                                            r["観測日時"].strftime("%Y-%m-%d"), r["観測日時"].strftime("%H:%M"),
                                            Latest_row.get("IjouKessokuKbnCD"), Latest_row.get("JK_Kbn"),
                                            Latest_row.get("KanriCD"), Latest_row.get("ShozokuCD"),
                                            Latest_row.get("DenwaKaitou", 0),
                                            1,  # ← 雨量確定で Shubetsu01は1固定
                                            0,  # ← 雨量確定で Shubetsu02は0固定
                                            0,  # ← 雨量確定で Shubetsu03は0固定
                                            0,  # ← 雨量確定で Shubetsu04は0固定
                                            0,  # ← 雨量確定で Shubetsu05は0固定
                                            0,  # ← 雨量確定で Shubetsu06は0固定
                                            0,  # ← 雨量確定で Shubetsu07は0固定
                                            0,  # ← 雨量確定で Shubetsu08は0固定
                                            0,  # ← 雨量確定で Shubetsu09は0固定
                                            '', #  発生経緯は空白固定
                                            4, # ← 新異常値検知検出システムで HakkenHouhouCDは4固定
                                            Latest_row.get("KKShubetsuCD"),
                                            '', #ない場合は''挿入1
                                            '', #ない場合は''挿入2
                                            '', #ない場合は''挿入3
                                            '', #ない場合は''挿入4
                                            '', #ない場合は''挿入5
                                            next_seq, # SeqNo
                                            r["観測日時"].strftime("%Y-%m-%d"), #StartDate
                                            r["観測日時"].strftime("%H:%M"), #StartTime
                                            create_time,#CreateTime
                                            update_time,#UpdateTime
                                            1, #FormatType(0:旧フォーマット、1:新フォーマット)
                                            Latest_row.get("KenCD"), #KenCD
                                            ],
                                },
                                "DS_ChousaMeisai": {
                                    "columns": ["DateNo", "CenterCD", "MeisaiNo", "SeqNo", "ShubetsuCD", "KansokujoCD", "JimushoCD", "KasenCD", "KenCD", "SuikeiCD",
                                                "CreateTime", "UpdateTime", "DelFlg"], #足りないカラムを追加
                                    "values": [DateNo_New, Latest_row.get("CenterCD"), str(next_seq), next_seq, ShubetsuCD, KansokujoCD, 
                                            JimushoCD, KasenCD, KenCD, SuikeiCD,
                                            create_time,#CreateTime
                                            update_time,#UpdateTime
                                            0],  
                                },
                                "DS_ChousaIjouchiSuiteiGenin": {
                                    "columns": ["DateNo", "CenterCD", "CISG_GeninKashoKbn", "CISG_HasseiUM", "CISG_SuiteiGeninKbn", "CISG_SuiteiNaiyou", "CISG_SankouInfo"],
                                    "values": [DateNo_New, Latest_row.get("CenterCD"),
                                            DS_ChousaIjouchiSuiteiGenin_row.get("CISG_GeninKashoKbn"),
                                            DS_ChousaIjouchiSuiteiGenin_row.get("CISG_HasseiUM"),
                                            DS_ChousaIjouchiSuiteiGenin_row.get("CISG_SuiteiGeninKbn"),
                                            '', ''], #足りないカラムを追加20250929(''で入力)
                                },
                                "DS_ChousaIjouchiHandan": {
                                    "columns": ["DateNo", "CenterCD", "CIH_KansokuData", "CIH_Tool", "CIH_Database", "CIH_CCTV", "CIH_HP", "CIH_River", "CIH_Kansoku", "CIH_HandanInfo", "CreateDateTime", "UpdateDateTime", 
                                                "CIH_TempFile_Kansoku", "CIH_TempFile_DataKanshi", "CIH_TempFile_CCTV", "CIH_TempFile_HP", "CIH_TempFile_Etc1", "CIH_TempFile_Etc2", "CIH_TempFile_Etc3", "CIH_TempFile_Etc4", 
                                                "CIH_TempFile_Etc5", "CIH_TempFile_Etc6",], #添付ファイルのカラム追加(CIH_TempFile_KansokuからCIH_TempFile_Etc6まで)
                                    "values": [DateNo_New, Latest_row.get("CenterCD"), '', '', '', '', '', '', '', '', create_time, update_time,
                                                TempFilePath1 if TempFilePath1 else '', #ない場合は''挿入1(10.png)
                                                '', #ない場合は''挿入2
                                                '', #ない場合は''挿入3
                                                '', #ない場合は''挿入4
                                                TempFilePath2 if TempFilePath2 else '', #ない場合は''挿入5(20.png)
                                                TempFilePath3 if TempFilePath3 else '', #ない場合は''挿入6(30.png)
                                                TempFilePath4 if TempFilePath4 else '', #ない場合は''挿入7
                                                TempFilePath5 if TempFilePath5 else '', #ない場合は''挿入8
                                                '', #ない場合は''挿入9
                                                '', #ない場合は''挿入10
                                                ]}, #足りないカラムを追加20250929(''で入力)
                                "DS_ChousaKaizenTaiou": {"columns": ["DateNo", "CenterCD", "CKT_Kinkyu", "CKT_Toumen", "CKT_Bappon", "CGF_Info", "CKTJ_KoukaInfo", "CKTJ_etc"], "values": [DateNo_New, Latest_row.get("CenterCD"), '', '', '', '', '', '']}, #足りないカラムを追加20250929(''で入力)
                                "DS_ChousashoShokanKikanKinyuuran": {"columns": ["DateNo", "CenterCD", "SI_Naiyou", "SI_Taiou"], "values": [DateNo_New, Latest_row.get("CenterCD"), '', '']} #足りないカラムを追加20250929(''で入力)
                            }

                            # 一括挿入
                            for Chousasho_table_name, Chousasho_data in Chousasho_insert_data.items():
                                Chousasho_insert_into_table(cursor, Chousasho_table_name, Chousasho_data["columns"], Chousasho_data["values"])
                            conn.commit()

                            DS_ChousaKihon_counts.append({"統一ID": cd2, "DateNo": DateNo_New})

                            print(f"統一ID {cd2} のデータベース登録が完了しました。新規DateNo: {DateNo_New}")

                        # ---------------------------データベース登録-----------------------------------------------

                conn.close()
                
                # デバッグ出力
                for rec in DS_ChousaKihon_counts:
                    print(rec)

                return JsonResponse({"status": "started", "counts": DS_ChousaKihon_counts})

                            
            except FileNotFoundError:
                return JsonResponse({
                    'success': False,
                    'message': f'CSVファイルが見つかりません: {csv_file_path}'
                })

            return JsonResponse({
                'success': True,
                'message': 'CSV監視を開始しました',
                'is_watching': True,
                'csv_preview': csv_data[:5],  # 最初の5行だけ返す
            })
        

        elif action == 'stop':
            watch_status.is_watching = False
            watch_status.save()
            return JsonResponse({
                'success': True,
                'message': 'CSV監視を停止しました',
                'is_watching': False
            })
        else:
            return JsonResponse({
                'success': False,
                'message': '無効なアクションです'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'エラーが発生しました: {str(e)}'
        })



@login_required
def get_watch_status(request):
    """現在の監視状態を取得"""
    try:
        watch_status, created = WatchStatus.objects.get_or_create(
            defaults={'is_watching': False}
        )
        
        return JsonResponse({
            'success': True,
            'is_watching': watch_status.is_watching,
            'last_checked': watch_status.last_checked.isoformat() if watch_status.last_checked else None,
            'processed_files_count': watch_status.processed_files_count,
            'error_count': watch_status.error_count
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'エラーが発生しました: {str(e)}'
        })
