import os
import time
import pandas as pd
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from app.models import csv_uryo  
import logging

# ログ設定
logger = logging.getLogger(__name__)

# 監視フォルダ（開発環境とDocker環境の両方に対応）
WATCH_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "..", "csv_input")
WATCH_FOLDER = os.path.abspath(WATCH_FOLDER)

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
            if not os.path.exists(watch_folder):
                self.stdout.write(self.style.ERROR(f"監視フォルダが存在しません: {watch_folder}"))
                return
                
            files = [f for f in os.listdir(watch_folder) if f.endswith(".csv")]
            
            for file in files:
                if file not in processed_files:
                    file_path = os.path.join(watch_folder, file)
                    try:
                        self.process_csv(file_path)
                        processed_files.add(file)
                        self.stdout.write(self.style.SUCCESS(f"新しいCSVファイルを処理しました: {file}"))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"CSVファイルの処理に失敗しました {file}: {str(e)}"))
                        logger.error(f"CSV processing error for {file}: {str(e)}")
                        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"ファイル監視中にエラーが発生しました: {str(e)}"))
            logger.error(f"File watching error: {str(e)}")

    def process_csv(self, file_path):
        """CSVファイルを読み込んでデータベースに保存"""
        try:
            # CSVファイルを読み込み
            df = pd.read_csv(file_path, encoding='utf-8')
            
            if df.empty:
                self.stdout.write(self.style.WARNING(f"CSVファイルが空です: {file_path}"))
                return
            
            # トランザクション内で一括処理
            with transaction.atomic():
                records_created = 0
                for _, row in df.iterrows():
                    try:
                        # データの前処理とバリデーション
                        record_data = self.prepare_record_data(row)
                        
                        # データベースに保存
                        csv_uryo.objects.create(**record_data)
                        records_created += 1
                        
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"行の処理に失敗しました: {str(e)}"))
                        logger.error(f"Row processing error: {str(e)}")
                        continue
                
                self.stdout.write(self.style.SUCCESS(f"{file_path} から {records_created} 件のレコードをDBに保存しました"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"CSVファイルの読み込みに失敗しました {file_path}: {str(e)}"))
            logger.error(f"CSV reading error for {file_path}: {str(e)}")
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
