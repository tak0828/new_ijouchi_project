# app/utils/csv_watcher.py
import os
import threading
import time
import csv
import hashlib
from django.conf import settings
from django.utils import timezone
from app.models import WatchStatus, csv_uryo, ProcessedFile

def process_csv_file(filepath):
    """CSVを読み込んで DB に保存"""
    records_count = 0
    try:
        with open(filepath, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # csv_uryo のフィールドに合わせて保存
                csv_uryo.objects.create(
                    observation_datetime=row.get("observation_datetime"),
                    item_type=row.get("item_type"),
                    unified_id=row.get("unified_id"),
                    water_id=row.get("water_id"),
                    station_name=row.get("station_name"),
                    region_name=row.get("region_name"),
                    water_system_name=row.get("water_system_name"),
                    river_name=row.get("river_name"),
                    manager=row.get("manager"),
                    management_type=row.get("management_type"),
                    observation_value=row.get("observation_value") or None,
                    # 近傍観測所やその他の値も同様に
                    # neighbor1_id=row.get("neighbor1_id") ...
                )
                records_count += 1
        return records_count, None
    except Exception as e:
        return records_count, str(e)

def watch_csv_loop():
    print("watcher loop running")
    csv_dir = os.path.join(settings.BASE_DIR, "csv_input")
    while True:
        try:
            watch_status = WatchStatus.objects.first()
            if watch_status and watch_status.is_watching:
                for filename in os.listdir(csv_dir):
                    if not filename.endswith(".csv"):
                        continue
                    filepath = os.path.join(csv_dir, filename)
                    
                    # すでに処理済みならスキップ
                    if ProcessedFile.objects.filter(file_name=filename).exists():
                        continue

                    # CSV処理
                    records_count, error_message = process_csv_file(filepath)

                    # ファイル情報を保存
                    with open(filepath, "rb") as f:
                        file_hash = hashlib.sha256(f.read()).hexdigest()
                        file_size = os.path.getsize(filepath)

                    ProcessedFile.objects.create(
                        file_name=filename,
                        file_path=filepath,
                        file_size=file_size,
                        file_hash=file_hash,
                        records_count=records_count,
                        status="success" if error_message is None else "error",
                        error_message=error_message
                    )

                    watch_status.processed_files_count += records_count
                    if error_message:
                        watch_status.error_count += 1

                watch_status.last_checked = timezone.now()
                watch_status.save()
        except Exception as e:
            print("CSV監視エラー:", e)
        time.sleep(5)

def start_watcher_thread():
    thread = threading.Thread(target=watch_csv_loop, daemon=True)
    thread.start()
