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

            Shubetsu_level = file_parts[0] if len(file_parts) > 0 else None  # 種別
            Keikai_level = file_parts[1] if len(file_parts) > 1 else None    # 警戒レベル

            # CSV読み込み処理
            try:
                csv_rows = []
                with open(csv_file_path, encoding="cp932") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
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

                        csv_rows.append({
                            "統一ID": Cd2_str.strip(),
                            "観測日時": csv_dt,
                            "1年前日時": year_ago,
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
                            "連続する異常値": row.get("連続する異常値")
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

                # 統一IDから MS_KansokujoからKansokujoCD を取得
                KansokujoCD2_list = list({r["統一ID"] for r in csv_rows})  # 重複排除
                placeholders = ','.join(['%s'] * len(KansokujoCD2_list))
                sql = f"SELECT KansokujoCD, ShubetsuCD, JimushoCD, KasenCD, KenCD, SuikeiCD, KansokujoCD2 FROM MS_Kansokujo WHERE KansokujoCD2 IN ({placeholders})"
                cursor.execute(sql, KansokujoCD2_list)
                MS_Kansokujo_results = cursor.fetchall()
                if not MS_Kansokujo_results:
                    print("MS_Kansokujo に一致するレコードがありません")
                    conn.close()
                    return JsonResponse({"status": "no_ms_record"})

                # MS_Kansokujo を辞書化: KansokujoCD2 → (KansokujoCD, ShubetsuCD)
                MS_Kansokujo_dict = {r["KansokujoCD2"]: (r["KansokujoCD"], r["ShubetsuCD"], r["KasenCD"], r["KenCD"], r["JimushoCD"], r["SuikeiCD"]) for r in MS_Kansokujo_results}

                # 各CSV行ごとに DS_ChousaMeisai 件数取得(1年前～観測日時) 
                DS_ChousaKihon_counts = []
                seq_dict = {}  # 観測所ごとの連番保持用辞書
                for r in csv_rows:
                    cd2 = r["統一ID"]
                    if cd2 not in MS_Kansokujo_dict:
                        continue
                    KansokujoCD, ShubetsuCD, JimushoCD, KasenCD, KenCD, SuikeiCD = MS_Kansokujo_dict[cd2]
                    
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

                            DateNo_New = f"{date_str}-{DateNo_New_no}"
                            print("新規DateNo:", DateNo_New)


                            # -----------------------attached_file.pyを実行-----------------------------------------------
                            for test_csv_row in csv_rows:

                                test_csv_row = test_csv_row.copy()

                                # datetime を文字列に変換
                                if isinstance(test_csv_row["観測日時"], datetime):
                                    test_csv_row["観測日時"] = test_csv_row["観測日時"].strftime("%Y/%m/%d %H:%M")
                                if isinstance(test_csv_row["1年前日時"], datetime):
                                    test_csv_row["1年前日時"] = test_csv_row["1年前日時"].strftime("%Y/%m/%d %H:%M")

                                # DateNo を追加
                                test_csv_row["DateNo"] = DateNo_New

                                # CSV行をJSON文字列に変換
                                csv_row_json = json.dumps(test_csv_row, ensure_ascii=False)

                                # attached_file.py のパス
                                attached_file_path = os.path.join(settings.BASE_DIR, "app", "attached_file.py")
                            
                                try:
                                    # subprocess.run(["python", attched_file_path], check=True, cwd=settings.BASE_DIR) # cwdで作業ディレクトリを指定(プロジェクト直下で実行)
                                    subprocess.run(
                                            [sys.executable, attached_file_path, csv_row_json],      # コンテナの Python を使う(csvを引数で渡す(json文字列))
                                            check=True,
                                            cwd=os.path.dirname(attached_file_path)    # /app/app をカレントディレクトリに
                                        )
                                    print("attached_file.py が正常に実行されました")
                                
                                except subprocess.CalledProcessError as e:  
                                    print(f"attached_file.py の実行中にエラーが発生しました: {e}")
                                    return JsonResponse({"status": "attached_file_error", "message": str(e)})
                                
                                return JsonResponse({"status": "started", "counts": len(csv_rows)})    
                            
                            # -----------------------attached_file.pyを実行-----------------------------------------------


                            # 次の MeisaiNo
                            next_seq = seq_dict.get(KansokujoCD, 1)
                            seq_dict[KansokujoCD] = next_seq + 1


                            # 挿入データまとめ
                            Chousasho_insert_data = {
                                "DS_ChousaKihon": {
                                    "columns": ["DateNo", "CenterCD", "HasseiJoukyouCD",
                                                "KakuninDate", "KakuninTime",
                                                "IjouKessokuKbnCD", "JK_Kbn", "KanriCD", "ShozokuCD", "DenwaKaitou", "Shubetsu01",
                                                "Shubetsu02","Shubetsu03","Shubetsu04","Shubetsu05","Shubetsu06","Shubetsu07","Shubetsu08",
                                                "Shubetsu09","HakkenHouhouCD", "KKShubetsuCD"],
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
                                            4, # ← 新異常値検知検出システムで HakkenHouhouCDは4固定
                                            Latest_row.get("KKShubetsuCD")
                                            ],
                                },
                                "DS_ChousaMeisai": {
                                    "columns": ["DateNo", "CenterCD", "MeisaiNo", "SeqNo", "ShubetsuCD", "KansokujoCD", "JimushoCD", "KasenCD", "KenCD", "SuikeiCD"],
                                    "values": [DateNo_New, Latest_row.get("CenterCD"), str(next_seq), next_seq, ShubetsuCD, KansokujoCD, 
                                              JimushoCD, KasenCD, KenCD, SuikeiCD],  
                                },
                                "DS_ChousaIjouchiSuiteiGenin": {
                                    "columns": ["DateNo", "CenterCD", "CISG_GeninKashoKbn", "CISG_HasseiUM", "CISG_SuiteiGeninKbn"],
                                    "values": [DateNo_New, Latest_row.get("CenterCD"),
                                            DS_ChousaIjouchiSuiteiGenin_row.get("CISG_GeninKashoKbn"),
                                            DS_ChousaIjouchiSuiteiGenin_row.get("CISG_HasseiUM"),
                                            DS_ChousaIjouchiSuiteiGenin_row.get("CISG_SuiteiGeninKbn")]
                                },
                                "DS_ChousaIjouchiHandan": {"columns": ["DateNo", "CenterCD"], "values": [DateNo_New, Latest_row.get("CenterCD")]},
                                "DS_ChousaKaizenTaiou": {"columns": ["DateNo", "CenterCD"], "values": [DateNo_New, Latest_row.get("CenterCD")]},
                                "DS_ChousashoShokanKikanKinyuuran": {"columns": ["DateNo", "CenterCD"], "values": [DateNo_New, Latest_row.get("CenterCD")]}
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
