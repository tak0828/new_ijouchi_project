import os
import time
import pandas as pd
import hashlib
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from app.models import csv_uryo, ProcessedFile, WatchStatus
import logging

# ログ設定
logger = logging.getLogger(__name__)

# 監視フォルダ（Docker優先。環境変数→/app/csv_input→プロジェクト相対csv_input の順に解決）
def resolve_watch_folder() -> str:
    # 1) 環境変数指定があれば最優先
    env_folder = os.environ.get("CSV_WATCH_FOLDER")
    if env_folder and os.path.exists(env_folder):
        return os.path.abspath(env_folder)

    # 2) Docker のマウントデフォルト
    docker_default = "/app/csv_input"
    if os.path.exists(docker_default):
        return docker_default

    # 3) プロジェクト相対（src 配下からの相対）
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    local_relative = os.path.abspath(os.path.join(base_dir, "..", "..", "csv_input"))
    return local_relative

WATCH_FOLDER = resolve_watch_folder()

class Command(BaseCommand):
    help = "CSVフォルダを監視してDBに取り込む"

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=10,
            help='監視間隔（秒）デフォルト: 10秒'
        )
        parser.add_argument(
            '--folder',
            type=str,
            help='監視するCSVフォルダのパス'
        )

    def handle(self, *args, **options):
        # 監視フォルダの設定
        watch_folder = options.get('folder') or WATCH_FOLDER
        interval = options.get('interval', 10)
        
        self.stdout.write(self.style.SUCCESS(f"CSVウォッチャーを起動しました"))
        self.stdout.write(f"監視フォルダ: {watch_folder}")
        self.stdout.write(f"監視間隔: {interval}秒")
        
        # 監視フォルダが存在しない場合は作成
        if not os.path.exists(watch_folder):
            os.makedirs(watch_folder)
            self.stdout.write(f"監視フォルダを作成しました: {watch_folder}")
        
        processed_files = set()
        
        try:
            while True:
                self.check_for_new_files(watch_folder, processed_files)
                time.sleep(interval)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("CSVウォッチャーを停止しました"))

    def check_for_new_files(self, watch_folder, processed_files):
        """新しいCSVファイルをチェックして処理"""
        try:
            # 監視状態をチェック
            watch_status, created = WatchStatus.objects.get_or_create(
                defaults={'is_watching': False}
            )
            
            if not watch_status.is_watching:
                # 監視が停止されている場合は何もしない
                return
                
            if not os.path.exists(watch_folder):
                self.stdout.write(self.style.ERROR(f"監視フォルダが存在しません: {watch_folder}"))
                return
                
            files = [f for f in os.listdir(watch_folder) if f.endswith(".csv")]
            
            for file in files:
                file_path = os.path.join(watch_folder, file)
                
                # ファイルの新規判定
                if self.is_new_file(file_path):
                    try:
                        self.process_csv(file_path)
                        processed_files.add(file)
                        # 処理済みファイル数を更新
                        watch_status.processed_files_count += 1
                        watch_status.save()
                        self.stdout.write(self.style.SUCCESS(f"新しいCSVファイルを処理しました: {file}"))
                    except Exception as e:
                        # エラー数を更新
                        watch_status.error_count += 1
                        watch_status.save()
                        self.stdout.write(self.style.ERROR(f"CSVファイルの処理に失敗しました {file}: {str(e)}"))
                        logger.error(f"CSV processing error for {file}: {str(e)}")
                else:
                    self.stdout.write(self.style.WARNING(f"ファイルは既に処理済みです: {file}"))
                        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"ファイル監視中にエラーが発生しました: {str(e)}"))
            logger.error(f"File watching error: {str(e)}")

    def is_new_file(self, file_path):
        """ファイルが新規かどうかを判定"""
        try:
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            file_hash = self.calculate_file_hash(file_path)
            
            # データベースで同じファイル名、サイズ、ハッシュのファイルを検索
            existing_file = ProcessedFile.objects.filter(
                file_name=file_name,
                file_size=file_size,
                file_hash=file_hash
            ).first()
            
            if existing_file:
                self.stdout.write(f"ファイルは既に処理済みです: {file_name} (処理日時: {existing_file.processed_at})")
                return False
            
            return True
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"ファイル判定中にエラーが発生しました: {str(e)}"))
            logger.error(f"File check error: {str(e)}")
            return True  # エラーの場合は新規として処理

    def calculate_file_hash(self, file_path):
        """ファイルのハッシュ値を計算"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"Hash calculation error: {str(e)}")
            return ""

    def process_csv(self, file_path):
        """CSVファイルを読み込んでデータベースに保存"""
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        file_hash = self.calculate_file_hash(file_path)
        
        try:
            # 複数のエンコーディングを試す
            encodings = ['utf-8', 'shift_jis', 'cp932', 'euc-jp']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    self.stdout.write(f"ファイルを {encoding} エンコーディングで読み込みました: {file_name}")
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                raise ValueError("ファイルのエンコーディングが判別できませんでした")
            
            if df.empty:
                self.stdout.write(self.style.WARNING(f"CSVファイルが空です: {file_path}"))
                # 空ファイルも記録
                self.record_processed_file(file_name, file_path, file_size, file_hash, 0, 'success')
                return
            
            # トランザクション内で一括処理
            with transaction.atomic():
                records_created = 0
                errors = 0
                
                for _, row in df.iterrows():
                    try:
                        # データの前処理とバリデーション
                        record_data = self.prepare_record_data(row)
                        
                        # 重複チェック
                        if self.is_duplicate_record(record_data):
                            continue
                        
                        # データベースに保存
                        csv_uryo.objects.create(**record_data)
                        records_created += 1
                        
                    except Exception as e:
                        errors += 1
                        self.stdout.write(self.style.ERROR(f"行の処理に失敗しました: {str(e)}"))
                        logger.error(f"Row processing error: {str(e)}")
                        continue
                
                # 処理結果を記録
                status = 'success' if errors == 0 else 'partial' if records_created > 0 else 'error'
                self.record_processed_file(file_name, file_path, file_size, file_hash, records_created, status)
                
                self.stdout.write(self.style.SUCCESS(f"{file_path} から {records_created} 件のレコードをDBに保存しました"))
                if errors > 0:
                    self.stdout.write(self.style.WARNING(f"{errors} 件のレコードでエラーが発生しました"))
                
        except Exception as e:
            error_msg = str(e)
            self.stdout.write(self.style.ERROR(f"CSVファイルの読み込みに失敗しました {file_path}: {error_msg}"))
            logger.error(f"CSV reading error for {file_path}: {error_msg}")
            
            # エラーも記録
            self.record_processed_file(file_name, file_path, file_size, file_hash, 0, 'error', error_msg)
            raise

    def prepare_record_data(self, row):
        """行データをデータベース用に準備"""
        def safe_float(value):
            """安全にfloatに変換"""
            if pd.isna(value) or value == '' or value is None:
                return None
            try:
                return float(value)
            except (ValueError, TypeError):
                return None
        
        def safe_int(value):
            """安全にintに変換"""
            if pd.isna(value) or value == '' or value is None:
                return None
            try:
                return int(value)
            except (ValueError, TypeError):
                return None
        
        def safe_str(value):
            """安全に文字列に変換"""
            if pd.isna(value) or value is None:
                return None
            return str(value)
        
        # 観測日時の処理
        try:
            observation_datetime = datetime.strptime(str(row['観測日時']), "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            # 他の日時フォーマットも試す
            try:
                observation_datetime = pd.to_datetime(row['観測日時'])
            except:
                raise ValueError(f"観測日時の形式が正しくありません: {row['観測日時']}")
        
        # 近傍観測所のデータを動的に処理
        neighbor_data = {}
        for i in range(1, 11):  # 近傍観測所1～10
            neighbor_data[f'neighbor{i}_id'] = safe_str(row.get(f'近傍観測所{i}のID'))
            neighbor_data[f'neighbor{i}_name'] = safe_str(row.get(f'近傍観測所{i}の名称'))
            neighbor_data[f'neighbor{i}_value'] = safe_float(row.get(f'近傍観測所{i}の観測値'))
        
        return {
            'observation_datetime': observation_datetime,
            'item_type': safe_str(row.get('項目種別')),
            'unified_id': safe_str(row.get('統一ID')),
            'water_id': safe_str(row.get('水水ID')),
            'station_name': safe_str(row.get('観測所名')),
            'region_name': safe_str(row.get('地方名')),
            'water_system_name': safe_str(row.get('水系名')),
            'river_name': safe_str(row.get('河川名')),
            'manager': safe_str(row.get('管理者')),
            'management_type': safe_str(row.get('管理区分')),
            'observation_value': safe_float(row.get('観測値')),
            **neighbor_data,
            'idw_estimated_value': safe_float(row.get('IDW推定値')),
            'mesh_code': safe_str(row.get('メッシュコード')),
            'radar_rainfall': safe_float(row.get('レーダ雨量')),
            'idw_anomaly': safe_float(row.get('IDW異常')),
            'upper_limit': safe_float(row.get('上限値')),
            'missing_or_unreceived': bool(row.get('欠測・未受信', 0) == 1),
            'consecutive_abnormal_values': safe_int(row.get('連続する異常値')),
        }

    def is_duplicate_record(self, record_data):
        """レコードの重複をチェック"""
        try:
            # 観測日時、統一ID、観測所名で重複チェック
            existing = csv_uryo.objects.filter(
                observation_datetime=record_data['observation_datetime'],
                unified_id=record_data['unified_id'],
                station_name=record_data['station_name']
            ).exists()
            
            return existing
            
        except Exception as e:
            logger.error(f"Duplicate check error: {str(e)}")
            return False  # エラーの場合は重複なしとして処理

    def record_processed_file(self, file_name, file_path, file_size, file_hash, records_count, status, error_message=None):
        """処理済みファイルの情報を記録"""
        try:
            ProcessedFile.objects.create(
                file_name=file_name,
                file_path=file_path,
                file_size=file_size,
                file_hash=file_hash,
                records_count=records_count,
                status=status,
                error_message=error_message
            )
        except Exception as e:
            logger.error(f"File record error: {str(e)}")
