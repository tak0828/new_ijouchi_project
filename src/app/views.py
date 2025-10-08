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
from app.attached_file import execute_attached_file_processing
from app.sendmail import execute_sendmail_processing
from app.fileupload import execute_fileupload_processing



import json
import sys
import os
import subprocess
import csv
import pymysql
import traceback


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


def process_csv_row(csv_rows, MS_Kansokujo_dict, cursor, csv_filename):
    """
    CSV行複数行の処理を行う関数
    DS_ChousaMeisaiの履歴検索
    """

    DS_ChousaMeisai_results = []

    for csv_row in csv_rows:
        cd2 = csv_row["統一ID"]
        if cd2 not in MS_Kansokujo_dict:
            continue
        
        KansokujoCD, ShubetsuCD, KasenCD, KenCD, JimushoCD, SuikeiCD, Ido, Keido, CenterCD = MS_Kansokujo_dict[cd2]
        
        # 1年前～観測日時のDS_ChousaMeisaiの最新の1件だけ取得
        sql2 = """
            SELECT DateNo
            FROM DS_ChousaMeisai
            WHERE KansokujoCD = %s
            AND ShubetsuCD = %s
            AND STR_TO_DATE(LEFT(DateNo,10),'%%Y/%%m/%%d') BETWEEN %s AND %s
            ORDER BY DateNo DESC
            LIMIT 1
        """
        params = [KansokujoCD, ShubetsuCD, csv_row["1年前日時"].strftime("%Y/%m/%d"), csv_row["観測日時"].strftime("%Y/%m/%d")]
        cursor.execute(sql2, params)
        DateNo_List = cursor.fetchone() #1件だけ取得(辞書型)
        DateNo = DateNo_List["DateNo"] if DateNo_List else None  # 文字列だけ取り出す  # 文字列だけ取り出す

        
        DS_ChousaMeisai_results.append({
            "csv_row": csv_row,
            "KansokujoCD": KansokujoCD,
            "ShubetsuCD": ShubetsuCD,
            "KasenCD": KasenCD,
            "KenCD": KenCD,
            "JimushoCD": JimushoCD,
            "SuikeiCD": SuikeiCD,
            "Ido": Ido,
            "Keido": Keido,
            "CenterCD": CenterCD,
            "DateNo": DateNo
        })
    return DS_ChousaMeisai_results


def get_latest_chousa_kihon(cursor, DateNo):
    
    """
    最新のDS_ChousaKihonレコードを取得
    """
    Latest_row = None
    DS_ChousaKihon_results = []
    
    for SQL_DateNo in DateNo:
        sql3 = """
            SELECT *
            FROM DS_ChousaKihon
            WHERE DateNo = %s
            AND HasseiJoukyouCD = '845108'
            ORDER BY DateNo DESC
            LIMIT 1
        """
        cursor.execute(sql3, [SQL_DateNo])
        DS_ChousaKihon_row = cursor.fetchone()
        if DS_ChousaKihon_row:
            DS_ChousaKihon_results.append(DS_ChousaKihon_row)
            if (Latest_row is None) or (DS_ChousaKihon_row["DateNo"] > Latest_row["DateNo"]):
                Latest_row = DS_ChousaKihon_row
    
    return DS_ChousaKihon_results


def get_latest_chousa_suitei(cursor, DateNo, CenterCD):

    """
    最新のDS_ChousaSuiteiレコードを取得
    """

    DS_ChousaIjouchiSuiteiGenin_results = []

    # DateNo と CenterCD をペアでループ
    for SQL_DateNo, SQL_CenterCD  in zip(DateNo, CenterCD):
        sql4 = """
            SELECT CISG_GeninKashoKbn, CISG_HasseiUM, CISG_SuiteiGeninKbn
            FROM DS_ChousaIjouchiSuiteiGenin
            WHERE DateNo = %s
            AND CenterCD = %s
        """
        cursor.execute(sql4, [SQL_DateNo, SQL_CenterCD])
        DS_ChousaIjouchiSuiteiGenin_row = cursor.fetchone()

        # DS_ChousaMeisaiから取得したCenterCDとDateNoをもとに最新のDS_ChousaSuiteiレコード(CISG_GeninKashoKbn, CISG_HasseiUM, CISG_SuiteiGeninKbn)を取得
        
        DS_ChousaIjouchiSuiteiGenin_results.append({
            "DateNo": SQL_DateNo,
            "CenterCD": SQL_CenterCD,
            "CISG_GeninKashoKbn": DS_ChousaIjouchiSuiteiGenin_row.get("CISG_GeninKashoKbn"),
            "CISG_HasseiUM": DS_ChousaIjouchiSuiteiGenin_row.get("CISG_HasseiUM"),
            "CISG_SuiteiGeninKbn": DS_ChousaIjouchiSuiteiGenin_row.get("CISG_SuiteiGeninKbn"),
        })

    return DS_ChousaIjouchiSuiteiGenin_results


def generate_new_dateno(cursor, csv_rows, csv_dt, CenterCD):
    """
    CSV行ごとに新しいDateNoを生成して csv_rows の各辞書に追加
    csv_rows: list[dict]
    csv_dt: list[datetime]（観測日時）
    CenterCD: list[str]（センターコード）
    """
    # 同じ日付・センターコードの最大番号をキャッシュ
    max_no_cache = {}

    # csv_rows(idx行)にそれぞれDateNoを追加
    for idx, (SQL_csv_dt, SQL_CenterCD) in enumerate(zip(csv_dt, CenterCD)):
        date_str = SQL_csv_dt.strftime("%Y/%m/%d")  # "YYYY/MM/DD"
        dateno_key = (date_str, SQL_CenterCD)

        # キャッシュがなければDBから取得
        if dateno_key not in max_no_cache:
            sql5 = """
                SELECT DateNo FROM DS_ChousaKihon
                WHERE DateNo LIKE %s AND CenterCD=%s
                ORDER BY DateNo DESC
            """
            like_DateNo = f"{date_str}-%"   # このままだと最新レコード入手できないから
            cursor.execute(sql5, (like_DateNo, SQL_CenterCD))

            DateNo_existing = cursor.fetchall()

            if DateNo_existing:
                max_no_cache[dateno_key] = max(
                    int(DateNo_List['DateNo'].split("-")[1]) for DateNo_List in DateNo_existing
                )
            else:
                max_no_cache[dateno_key] = 0

        # 新しい連番を作成
        max_no_cache[dateno_key] += 1
        DateNo_New_no = f"{max_no_cache[dateno_key]:03d}"

        # DateNo を作成（スラッシュを除去してハイフン形式）
        date_part = date_str.replace("/", "")
        DateNo_CSV = f"{date_part}-{DateNo_New_no}"

        # csv_rows の各行に 'DateNo' を追加
        csv_rows[idx]['DateNo'] = DateNo_CSV

    return csv_rows
    


def insert_database_records(cursor, csv_rows, DS_ChousaKihon_results, DS_ChousaMeisai_results, DS_ChousaIjouchiSuiteiGenin_results, temp_result_paths, seq_dict):
    """
    データベースへのレコード挿入処理
    """

    for i, rows in enumerate(csv_rows):
        # 次の MeisaiNo
        KansokujoCD = rows["観測所CD"]
        next_seq = seq_dict.get(KansokujoCD, 1)
        seq_dict[KansokujoCD] = next_seq + 1

        # CreateTime, UpdateTime は現在日時で作成
        create_now = datetime.now()
        create_time = create_now.strftime("%Y-%m-%d %H:%M:%S.") + f"{int(create_now.microsecond/1000):03d}"
        update_now = datetime.now()
        update_time = update_now.strftime("%Y-%m-%d %H:%M:%S.") + f"{int(update_now.microsecond/1000):03d}"

        # 各i行目の対応データを取得(マスタからの履歴データ,添付ファイル情報の取得)（上書きしないように別変数にする）
        DS_ChousaKihon_result = DS_ChousaKihon_results[i]
        DS_ChousaMeisai_result = DS_ChousaMeisai_results[i]
        DS_ChousaIjouchiSuiteiGenin_result = DS_ChousaIjouchiSuiteiGenin_results[i]
        temp_result_path = temp_result_paths[i]  # 例: [DateNo, path1, path2, path3, path4, path5]
        temp_result_path = list(temp_result_path) + [""] * (6 - len(temp_result_path))  # 空文字で補完
        TempFilePath1, TempFilePath2, TempFilePath3, TempFilePath4, TempFilePath5 = temp_result_path[1:6] #1個目から6個目までを割り当てる

        # 挿入データまとめ
        Chousasho_insert_data = {
            "DS_ChousaKihon": {
                "columns": ["DateNo", "CenterCD", "HasseiJoukyouCD",
                            "KakuninDate", "KakuninTime",
                            "IjouKessokuKbnCD", "JK_Kbn", "KanriCD", "ShozokuCD", "DenwaKaitou", "Shubetsu01",
                            "Shubetsu02","Shubetsu03","Shubetsu04","Shubetsu05","Shubetsu06","Shubetsu07","Shubetsu08",
                            "Shubetsu09", "HasseiKeii" ,"HakkenHouhouCD", "KKShubetsuCD",
                            "KanshiTempFile01", "KanshiTempFile02", "KanshiTempFile03", "KanshiTempFile04", "KanshiTempFile05",
                            "SeqNo", "StartDate", "StartTime", "CreateTime", "UpdateTime", "FormatType", "KenCD"],
                "values": [rows["DateNo"], rows["地方CD"], DS_ChousaKihon_result.get("HasseiJoukyouCD"),
                        rows["観測日時"].strftime("%Y-%m-%d"), rows["観測日時"].strftime("%H:%M"),
                        DS_ChousaKihon_result.get("IjouKessokuKbnCD"), DS_ChousaKihon_result.get("JK_Kbn"),
                        DS_ChousaKihon_result.get("KanriCD"), DS_ChousaKihon_result.get("ShozokuCD"),
                        DS_ChousaKihon_result.get("DenwaKaitou", 0),
                        1, 0, 0, 0, 0, 0, 0, 0, 0, '', 4, DS_ChousaKihon_result.get("KKShubetsuCD"),
                        '', '', '', '', '', next_seq,
                        rows["観測日時"].strftime("%Y-%m-%d"), rows["観測日時"].strftime("%H:%M"),
                        create_time, update_time, 1, rows["都道府県CD"]
                        ],
            },
            "DS_ChousaMeisai": {
                "columns": ["DateNo", "CenterCD", "MeisaiNo", "SeqNo", "ShubetsuCD", "KansokujoCD", "JimushoCD", "KasenCD", "KenCD", "SuikeiCD",
                            "CreateTime", "UpdateTime", "DelFlg"],
                "values": [rows["DateNo"], rows["地方CD"], str(next_seq), next_seq, rows["種別CD"], rows["観測所CD"], 
                        rows["事務所CD"], rows["河川CD"], rows["都道府県CD"], rows["水系CD"], create_time, update_time, 0],  
            },
            "DS_ChousaIjouchiSuiteiGenin": {
                "columns": ["DateNo", "CenterCD", "CISG_GeninKashoKbn", "CISG_HasseiUM", "CISG_SuiteiGeninKbn", "CISG_SuiteiNaiyou", "CISG_SankouInfo"],
                "values": [rows["DateNo"], rows["地方CD"],
                        DS_ChousaIjouchiSuiteiGenin_result["CISG_GeninKashoKbn"],
                        DS_ChousaIjouchiSuiteiGenin_result["CISG_HasseiUM"],
                        DS_ChousaIjouchiSuiteiGenin_result["CISG_SuiteiGeninKbn"],
                        '', ''],
            },
            "DS_ChousaIjouchiHandan": {
                "columns": ["DateNo", "CenterCD", "CIH_KansokuData", "CIH_Tool", "CIH_Database", "CIH_CCTV", "CIH_HP", "CIH_River", "CIH_Kansoku", "CIH_HandanInfo", "CreateDateTime", "UpdateDateTime", 
                            "CIH_TempFile_Kansoku", "CIH_TempFile_DataKanshi", "CIH_TempFile_CCTV", "CIH_TempFile_HP", "CIH_TempFile_Etc1", "CIH_TempFile_Etc2", "CIH_TempFile_Etc3", "CIH_TempFile_Etc4", 
                            "CIH_TempFile_Etc5", "CIH_TempFile_Etc6"],
                "values": [rows["DateNo"], rows["地方CD"], '', '', '', '', '', '', '', '', create_time, update_time,
                            TempFilePath1 if TempFilePath1 else '', '', '', '', 
                            TempFilePath2 if TempFilePath2 else '', TempFilePath3 if TempFilePath3 else '', 
                            TempFilePath4 if TempFilePath4 else '', TempFilePath5 if TempFilePath5 else '', 
                            '', ''],
            },
            "DS_ChousaKaizenTaiou": {
                "columns": ["DateNo", "CenterCD", "CKT_Kinkyu", "CKT_Toumen", "CKT_Bappon", "CGF_Info", "CKTJ_KoukaInfo", "CKTJ_etc"], 
                "values": [rows["DateNo"], rows["地方CD"], '', '', '', '', '', '']
            },
            "DS_ChousashoShokanKikanKinyuuran": {
                "columns": ["DateNo", "CenterCD", "SI_Naiyou", "SI_Taiou"], 
                "values": [rows["DateNo"], rows["地方CD"], '', '']
            }
        }

        # ===== 挿入実行 =====

        # 一括挿入
        for Chousasho_table_name, Chousasho_data in Chousasho_insert_data.items():
            Chousasho_insert_into_table(cursor, Chousasho_table_name, Chousasho_data["columns"], Chousasho_data["values"])
    
    return next_seq



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

            # CSVファイルのパス（複数行テスト用）
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
                # csv_rows→r
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

                # 各CSV行ごとに処理
                seq_dict = {}  # 観測所ごとの連番保持用辞書

                # CSV複数行に緯度、経度、地方コードを入れる
                for r in csv_rows:
                    # CSV行データを準備
                    row_data =MS_Kansokujo_dict.get(r["統一ID"])
                    
                    # # 緯度経度を追加
                    if row_data:
                        kansokujo_cd, shubetsu_cd, kasen_cd, ken_cd, jimusho_cd, suikei_cd, ido, keido, center_cd = row_data
                        r["観測所CD"] = kansokujo_cd 
                        r["種別CD"] = shubetsu_cd
                        r["河川CD"] = kasen_cd
                        r["都道府県CD"] = ken_cd
                        r["事務所CD"] = jimusho_cd
                        r["水系CD"] = suikei_cd
                        r["緯度"] = ido
                        r["経度"] = keido
                        r["地方CD"] = center_cd
                    else:
                        r["緯度"] = r["経度"] = r["地方CD"] = r["観測所CD"] = r["種別CD"] = r["河川CD"] = r["都道府県CD"] = r["事務所CD"] = r["水系CD"] = None

                    
                    # 近傍観測所フラグの処理
                    is_kinbou = r.get("近傍観測所フラグ", False)
                    if is_kinbou:
                        for i in range(1, 4):
                            kinbou_key = f"近傍観測所{i}のID"
                            kinbou_cd2 = r.get(kinbou_key)
                            
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
                            if kinbou_row:
                                r[f"近傍観測所{i}フラグ"] = True
                                print(f"近傍観測所 {kinbou_cd2} の情報を追加しました")


                # ----------------------ここから改修-------------------------
                
                # CSV行の処理
                DS_ChousaMeisai_results = process_csv_row(csv_rows, MS_Kansokujo_dict, cursor, csv_filename)

                # 複数行まとめてDateNOを抽出(辞書型なので変換)
                DateNo_List = [DateNo_List["DateNo"] for DateNo_List in DS_ChousaMeisai_results]
                
                # 複数行まとめてCenterCDを抽出(辞書型なので変換)
                CenterCD_List = [CenterCD_List["CenterCD"] for CenterCD_List in DS_ChousaMeisai_results]
                
                # 最新のDS_ChousaKihonレコードを取得
                DS_ChousaKihon_results = get_latest_chousa_kihon(cursor, DateNo_List)
        
                # 最新のDS_ChousaIjouchiSuiteiレコードを取得
                DS_ChousaIjouchiSuiteiGenin_results = get_latest_chousa_suitei(cursor, DateNo_List, CenterCD_List)

                # CSV複数行まとめてを観測日時を抽出(辞書型なので変換)
                KansokuDate_List = [KansokuDate_List["観測日時"] for KansokuDate_List in csv_rows]
                
                # 新しいDateNoを生成してcsv_rowsに上書き(調査書登録番号)
                csv_rows = generate_new_dateno(cursor, csv_rows, KansokuDate_List, CenterCD_List)
                
                                
                # スクリーンショット生成: 関数版に切替
                # attached_capture.pyを実行
                try:
                    rows, cols = j, 11  
                    TempFile_results = [["0" for _ in range(cols)] for _ in range(rows)]
                    TempFile_results, temp_result_paths = execute_attached_file_processing(csv_rows, csv_filename, TempFile_results)
                except Exception as e:
                    print(f"attached_capture の実行中にエラーが発生しました: {e}")
                
                # sendmail.pyを実行
                # -----------------------------------------------------------------------------------
                csv_file_name = os.path.basename(csv_file_path).replace(".csv", "")
    
                try:
                    sendmail_result = execute_sendmail_processing(csv_rows, csv_file_name)
                    print("sendmail.py が正常に実行されました")
                    
                except subprocess.CalledProcessError as e:
                    print(f"sendmail.py の実行中にエラーが発生しました: {e}")

                # ---------------------------------------------------------------------------------------------
                # fileupload.pyを実行                
                try:
                    fileupload_result = execute_fileupload_processing(csv_rows, csv_file_name, TempFile_results)
                    print("fileupload.py が正常に実行されました")
                    
                except subprocess.CalledProcessError as e:
                    print(f"fileupload.py の実行中にエラーが発生しました: {e}")

                # ---------------------------------------------------------------------------------------------
                # データベースにレコード挿入
                next_seq = insert_database_records(
                    cursor, csv_rows,DS_ChousaKihon_results, DS_ChousaMeisai_results, DS_ChousaIjouchiSuiteiGenin_results,
                    temp_result_paths, seq_dict
                )
                
                conn.commit()
                conn.close()
                

                return JsonResponse({
                    "status": "completed",
                    "message": "データベースの登録が完了しました。"
                })

                            
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
            'message': f'エラーが発生しました: {str(e)}',
            'exception_type': str(exc_type.__name__),
            'line_no': lineno,
            'trace': traceback.format_exc()
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
