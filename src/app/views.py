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
import os
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
            csv_file_path = os.path.join(settings.BASE_DIR, "csv", "雨量_注意_新潟デモ2.csv")

            # CSV読み込み処理
            try:
                csv_rows = []
                with open(csv_file_path, encoding="cp932") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        dt_str = row.get("観測日時")
                        cd2_str = row.get("統一ID")
                        if not dt_str or not cd2_str:
                            continue
                        
                        csv_dt = datetime.strptime(dt_str.strip(), "%Y/%m/%d %H:%M")
                        two_years_ago = csv_dt - timedelta(days=365*2)
                        
                        csv_rows.append({
                            "統一ID": cd2_str.strip(),
                            "観測日時": csv_dt,
                            "2年前日時": two_years_ago
                        })

                if not csv_rows:
                    print("CSVに有効な行がありません")
                    return JsonResponse({"status": "no_data"})

                # MariaDB接続
                conn = pymysql.connect(
                    host='192.168.99.193',
                    user='frics',
                    password='fricsV6',
                    database='IjouchiDBV6',
                    charset='utf8mb4'
                )

                cursor = conn.cursor(pymysql.cursors.DictCursor)

                # 統一IDから MS_Kansokujo を取得
                KansokujoCD2_list = list({r["統一ID"] for r in csv_rows})  # 重複排除
                placeholders = ','.join(['%s'] * len(KansokujoCD2_list))
                sql = f"SELECT KansokujoCD, ShubetsuCD, KansokujoCD2 FROM MS_Kansokujo WHERE KansokujoCD2 IN ({placeholders})"
                cursor.execute(sql, KansokujoCD2_list)
                MS_Kansokujo_results = cursor.fetchall()
                if not MS_Kansokujo_results:
                    print("MS_Kansokujo に一致するレコードがありません")
                    conn.close()
                    return JsonResponse({"status": "no_ms_record"})

                # MS_Kansokujo を辞書化: KansokujoCD2 → (KansokujoCD, ShubetsuCD)
                MS_Kansokujo_dict = {r["KansokujoCD2"]: (r["KansokujoCD"], r["ShubetsuCD"]) for r in MS_Kansokujo_results}

                # 各CSV行ごとに DS_ChousaMeisai 件数取得
                result_counts = []
                for r in csv_rows:
                    cd2 = r["統一ID"]
                    if cd2 not in MS_Kansokujo_dict:
                        continue
                    KansokujoCD, ShubetsuCD = MS_Kansokujo_dict[cd2]
                    
                    sql2 = """
                        SELECT COUNT(*) as cnt
                        FROM DS_ChousaMeisai
                        WHERE KansokujoCD = %s
                        AND ShubetsuCD = %s
                        AND STR_TO_DATE(LEFT(DateNo,10),'%%Y/%%m/%%d') BETWEEN %s AND %s
                    """
                    params = [KansokujoCD, ShubetsuCD, r["2年前日時"].strftime("%Y/%m/%d"), r["観測日時"].strftime("%Y/%m/%d")]
                    cursor.execute(sql2, params)
                    count = cursor.fetchone()["cnt"]
                    result_counts.append({
                        "統一ID": cd2,
                        "KansokujoCD": KansokujoCD,
                        "ShubetsuCD": ShubetsuCD,
                        "観測日時": r["観測日時"].strftime("%Y/%m/%d %H:%M"),
                        "2年前日時": r["2年前日時"].strftime("%Y/%m/%d"),
                        "件数": count
                    })

                conn.close()
                
                # デバッグ出力
                for rec in result_counts:
                    print(rec)

                return JsonResponse({"status": "started", "counts": result_counts})

                # # Docker内DB(MS_Kanoskujo_Updateに保存)
                # with transaction.atomic():
                #     for row in KansokujoCD2_results:
                #         try:
                #             MS_Kansokujo_Update.objects.update_or_create(
                #                 KansokujoCD=row['KansokujoCD'],
                #                 defaults={
                #                     # foreign_keyを使わずに直接保存
                #                     'ShubetsuCD': row.get('ShubetsuCD'),
                #                     'KansokujoCD2': row.get('KansokujoCD2'),
                #                     'KansokujoName': row.get('KansokujoName'),
                #                     'KansokujoYomi': row.get('KansokujoYomi'),
                #                     'Shozaichi': row.get('Shozaichi'),
                #                     'CenterCD': row.get('CenterCD'),
                #                     'ShozokuCD': row.get('ShozokuCD'),
                #                     'KanriCD': row.get('KanriCD'),
                #                     'KenCD': row.get('KenCD'),
                #                     'JimushoCD': row.get('JimushoCD'),
                #                     'JimushoCD2': row.get('JimushoCD2'),
                #                     'SuikeiCD': row.get('SuikeiCD'),
                #                     'SuikeiCD2': row.get('SuikeiCD2'),
                #                     'KasenCD': row.get('KasenCD'),
                #                     'KasenCD2': row.get('KasenCD2'),
                #                     'Hyokou': row.get('Hyokou'),
                #                     'Ido': row.get('Ido'),
                #                     'Keido': row.get('Keido'),
                #                     'KijunFLG': row.get('KijunFLG', False),
                #                     'TenyuryokuFLG': row.get('TenyuryokuFLG', False),
                #                     'StartYMD': row.get('StartYMD'),
                #                     'EndYMD': row.get('EndYMD'),
                #                     'HyoujiNo': row.get('HyoujiNo'),
                #                     'ShutsuryokuNo': row.get('ShutsuryokuNo'),
                #                     'K_GroupCD': row.get('K_GroupCD'),
                #                     'S_GroupCD': row.get('S_GroupCD'),
                #                     'SuiiShuuchiFLG': row.get('SuiiShuuchiFLG', False),
                #                     'KansokuKikiCD': row.get('KansokuKikiCD'),
                #                     'KansokuKikiYMD': row.get('KansokuKikiYMD'),
                #                     'DelFlg': row.get('DelFlg', False),
                #                     'DblFlg': row.get('DblFlg', False),
                #                     'K_Time': row.get('K_Time'),
                #                     'Kijunchi': row.get('Kijunchi'),
                #                     'Jougenchi': row.get('Jougenchi'),
                #                     'Kagenchi': row.get('Kagenchi'),
                #                     'Hendouryou': row.get('Hendouryou'),
                #                     'TempFile01': None,
                #                     'TempFile02': None,
                #                     'TempFile03': None,
                #                     'TempFile04': None,
                #                     'TempFile05': None,
                #                     'TempFile06': None,
                #                     'TempFile07': None,
                #                     'TempFile08': None,
                #                     'TempFile09': None,
                #                     'TempFile10': None,
                #                 }
                #             )

                #             print(f"レコード {row['KansokujoCD']} を保存または更新しました")
                #         except Exception as e:
                #             print(f"レコード {row['KansokujoCD']} の保存でエラー:", e)
                            
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
