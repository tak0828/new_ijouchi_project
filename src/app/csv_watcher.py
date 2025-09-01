import os
import time
import pandas as pd
from datetime import datetime
from django.core.management.base import BaseCommand
from app.models import csv_uryo  # 自分のアプリ名に置き換え

# Docker 内の監視フォルダ
WATCH_FOLDER = "/app/csv_input"  

class Command(BaseCommand):
    help = "CSVフォルダを監視してDBに取り込む"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("CSVウォッチャーを起動しました"))
        processed_files = set()

        while True:
            files = [f for f in os.listdir(WATCH_FOLDER) if f.endswith(".csv")]
            for file in files:
                if file not in processed_files:
                    self.process_csv(os.path.join(WATCH_FOLDER, file))
                    processed_files.add(file)
            time.sleep(10)  # 10秒ごとに監視

    def process_csv(self, file_path):
        df = pd.read_csv(file_path)
        for _, row in df.iterrows():
            csv_uryo.objects.create(
                observation_datetime = datetime.strptime(row['観測日時'], "%Y-%m-%d %H:%M:%S"),
                item_type = row['項目種別'],
                unified_id = row['統一ID'],
                water_id = row['水水ID'],
                station_name = row['観測所名'],
                region_name = row['地方名'],
                water_system_name = row['水系名'],
                river_name = row['河川名'],
                manager = row['管理者'],
                management_type = row['管理区分'],
                observation_value = float(row['観測値']) if row['観測値'] else None,
                neighbor1_id = row.get('近傍観測所1のID'),
                neighbor1_name = row.get('近傍観測所1の名称'),
                neighbor1_value = float(row['近傍観測所1の観測値']) if row.get('近傍観測所1の観測値') else None,
                # 近傍観測所2～10も同様に追加可能
                idw_estimated_value = float(row['IDW推定値']) if row.get('IDW推定値') else None,
                mesh_code = row.get('メッシュコード'),
                radar_rainfall = float(row['レーダ雨量']) if row.get('レーダ雨量') else None,
                idw_anomaly = float(row['IDW異常']) if row.get('IDW異常') else None,
                upper_limit = float(row['上限値']) if row.get('上限値') else None,
                missing_or_unreceived = row['欠測・未受信'] == 1,
                consecutive_abnormal_values = int(row['連続する異常値']) if row.get('連続する異常値') else None,
            )
        self.stdout.write(self.style.SUCCESS(f"{file_path} を DB に取り込みました"))
