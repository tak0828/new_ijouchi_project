from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from app.models import  WatchStatus, MS_Kansokujo_Update
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
            csv_data = []
            try:
                with open(csv_file_path, encoding="cp932") as f:  # Windows製CSVはShift_JIS(cp932)
                    reader = csv.DictReader(f)  # 1行目をヘッダとして扱う(例：統一CD等)
                    KansokujoCD2_list = []  # 統一IDを格納するリスト
                    for row in reader:
                        # 統一IDがある行だけ抽出
                        KansokujoCD2_id = row.get('統一ID')
                        if KansokujoCD2_id:  # 空でなければ追加
                            KansokujoCD2_list.append(KansokujoCD2_id)


                print(KansokujoCD2_list)  # デバッグ用にコンソール出力

                # mariadb接続(今回は仮想環境192.168.99.193を使用)
                conn = pymysql.connect(
                    host='192.168.99.193',
                    user='frics',
                    password='fricsV6',
                    database='IjouchiDBV6',
                    charset='utf8mb4'
                )
                cursor = conn.cursor(pymysql.cursors.DictCursor)  # 辞書形式で取得


                # SQLで一致するレコードを取得
                # IN句を使う場合、プレースホルダに注意
                if KansokujoCD2_list:
                    # CSVの値を前後空白除去
                    KansokujoCD2_list = [id_.strip() for id_ in KansokujoCD2_list if id_]

                    # プレースホルダを自動生成
                    placeholders = ','.join(['%s'] * len(KansokujoCD2_list))
                    sql = f"SELECT * FROM MS_Kansokujo WHERE KansokujoCD2 IN ({placeholders})"

                    # デバッグ用にSQLとパラメータを出力
                    # print("DEBUG SQL:", sql)
                    # print("DEBUG PARAMS:", KansokujoCD2_list)

                    # SQL実行
                    cursor.execute(sql, KansokujoCD2_list)
                    KansokujoCD2_results = cursor.fetchall()  # すべて取得
                    print("取得結果:", KansokujoCD2_results)  # デバッグ
                
                conn.close()

                # Docker内DB(MS_Kanoskujo_Updateに保存)
                with transaction.atomic():
                    for row in KansokujoCD2_results:
                        try:
                            MS_Kansokujo_Update.objects.update_or_create(
                                KansokujoCD=row['KansokujoCD'],
                                defaults={
                                    # foreign_keyを使わずに直接保存
                                    'ShubetsuCD': row.get('ShubetsuCD'),
                                    'KansokujoCD2': row.get('KansokujoCD2'),
                                    'KansokujoName': row.get('KansokujoName'),
                                    'KansokujoYomi': row.get('KansokujoYomi'),
                                    'Shozaichi': row.get('Shozaichi'),
                                    'CenterCD': row.get('CenterCD'),
                                    'ShozokuCD': row.get('ShozokuCD'),
                                    'KanriCD': row.get('KanriCD'),
                                    'KenCD': row.get('KenCD'),
                                    'JimushoCD': row.get('JimushoCD'),
                                    'JimushoCD2': row.get('JimushoCD2'),
                                    'SuikeiCD': row.get('SuikeiCD'),
                                    'SuikeiCD2': row.get('SuikeiCD2'),
                                    'KasenCD': row.get('KasenCD'),
                                    'KasenCD2': row.get('KasenCD2'),
                                    'Hyokou': row.get('Hyokou'),
                                    'Ido': row.get('Ido'),
                                    'Keido': row.get('Keido'),
                                    'KijunFLG': row.get('KijunFLG', False),
                                    'TenyuryokuFLG': row.get('TenyuryokuFLG', False),
                                    'StartYMD': row.get('StartYMD'),
                                    'EndYMD': row.get('EndYMD'),
                                    'HyoujiNo': row.get('HyoujiNo'),
                                    'ShutsuryokuNo': row.get('ShutsuryokuNo'),
                                    'K_GroupCD': row.get('K_GroupCD'),
                                    'S_GroupCD': row.get('S_GroupCD'),
                                    'SuiiShuuchiFLG': row.get('SuiiShuuchiFLG', False),
                                    'KansokuKikiCD': row.get('KansokuKikiCD'),
                                    'KansokuKikiYMD': row.get('KansokuKikiYMD'),
                                    'DelFlg': row.get('DelFlg', False),
                                    'DblFlg': row.get('DblFlg', False),
                                    'K_Time': row.get('K_Time'),
                                    'Kijunchi': row.get('Kijunchi'),
                                    'Jougenchi': row.get('Jougenchi'),
                                    'Kagenchi': row.get('Kagenchi'),
                                    'Hendouryou': row.get('Hendouryou'),
                                    'TempFile01': None,
                                    'TempFile02': None,
                                    'TempFile03': None,
                                    'TempFile04': None,
                                    'TempFile05': None,
                                    'TempFile06': None,
                                    'TempFile07': None,
                                    'TempFile08': None,
                                    'TempFile09': None,
                                    'TempFile10': None,
                                }
                            )

                            print(f"レコード {row['KansokujoCD']} を保存または更新しました")
                        except Exception as e:
                            print(f"レコード {row['KansokujoCD']} の保存でエラー:", e)
                            
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
