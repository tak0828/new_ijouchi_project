from django.db import models

class csv_uryo(models.Model):
    
    observation_datetime = models.DateTimeField(verbose_name="観測日時")
    item_type = models.CharField(max_length=50, verbose_name="項目種別")
    unified_id = models.CharField(max_length=50, verbose_name="統一ID")
    water_id = models.CharField(max_length=50, verbose_name="水水ID")
    station_name = models.CharField(max_length=100, verbose_name="観測所名")
    region_name = models.CharField(max_length=50, verbose_name="地方名")
    water_system_name = models.CharField(max_length=50, verbose_name="水系名")
    river_name = models.CharField(max_length=50, verbose_name="河川名")
    manager = models.CharField(max_length=50, verbose_name="管理者")
    management_type = models.CharField(max_length=50, verbose_name="管理区分")
    observation_value = models.FloatField(verbose_name="観測値", null=True, blank=True)

    # 近傍観測所1
    neighbor1_id = models.CharField(max_length=50, verbose_name="近傍観測所1のID", null=True, blank=True)
    neighbor1_name = models.CharField(max_length=100, verbose_name="近傍観測所1の名称", null=True, blank=True)
    neighbor1_value = models.FloatField(verbose_name="近傍観測所1の観測値", null=True, blank=True)

    # 近傍観測所2
    neighbor2_id = models.CharField(max_length=50, verbose_name="近傍観測所2のID", null=True, blank=True)
    neighbor2_name = models.CharField(max_length=100, verbose_name="近傍観測所2の名称", null=True, blank=True)
    neighbor2_value = models.FloatField(verbose_name="近傍観測所2の観測値", null=True, blank=True)

    # 近傍観測所3
    neighbor3_id = models.CharField(max_length=50, verbose_name="近傍観測所3のID", null=True, blank=True)
    neighbor3_name = models.CharField(max_length=100, verbose_name="近傍観測所3の名称", null=True, blank=True)
    neighbor3_value = models.FloatField(verbose_name="近傍観測所3の観測値", null=True, blank=True)

    # 近傍観測所4
    neighbor4_id = models.CharField(max_length=50, verbose_name="近傍観測所4のID", null=True, blank=True)
    neighbor4_name = models.CharField(max_length=100, verbose_name="近傍観測所4の名称", null=True, blank=True)
    neighbor4_value = models.FloatField(verbose_name="近傍観測所4の観測値", null=True, blank=True)

    # 近傍観測所5
    neighbor5_id = models.CharField(max_length=50, verbose_name="近傍観測所5のID", null=True, blank=True)
    neighbor5_name = models.CharField(max_length=100, verbose_name="近傍観測所5の名称", null=True, blank=True)
    neighbor5_value = models.FloatField(verbose_name="近傍観測所5の観測値", null=True, blank=True)

    # 近傍観測所6
    neighbor6_id = models.CharField(max_length=50, verbose_name="近傍観測所6のID", null=True, blank=True)
    neighbor6_name = models.CharField(max_length=100, verbose_name="近傍観測所6の名称", null=True, blank=True)
    neighbor6_value = models.FloatField(verbose_name="近傍観測所6の観測値", null=True, blank=True)

    # 近傍観測所7
    neighbor7_id = models.CharField(max_length=50, verbose_name="近傍観測所7のID", null=True, blank=True)
    neighbor7_name = models.CharField(max_length=100, verbose_name="近傍観測所7の名称", null=True, blank=True)
    neighbor7_value = models.FloatField(verbose_name="近傍観測所7の観測値", null=True, blank=True)

    # 近傍観測所8
    neighbor8_id = models.CharField(max_length=50, verbose_name="近傍観測所8のID", null=True, blank=True)
    neighbor8_name = models.CharField(max_length=100, verbose_name="近傍観測所8の名称", null=True, blank=True)
    neighbor8_value = models.FloatField(verbose_name="近傍観測所8の観測値", null=True, blank=True)

    # 近傍観測所9
    neighbor9_id = models.CharField(max_length=50, verbose_name="近傍観測所9のID", null=True, blank=True)
    neighbor9_name = models.CharField(max_length=100, verbose_name="近傍観測所9の名称", null=True, blank=True)
    neighbor9_value = models.FloatField(verbose_name="近傍観測所9の観測値", null=True, blank=True)

    # 近傍観測所10
    neighbor10_id = models.CharField(max_length=50, verbose_name="近傍観測所10のID", null=True, blank=True)
    neighbor10_name = models.CharField(max_length=100, verbose_name="近傍観測所10の名称", null=True, blank=True)
    neighbor10_value = models.FloatField(verbose_name="近傍観測所10の観測値", null=True, blank=True)

    # その他の情報
    idw_estimated_value = models.FloatField(verbose_name="IDW推定値", null=True, blank=True)
    mesh_code = models.CharField(max_length=20, verbose_name="メッシュコード", null=True, blank=True)
    radar_rainfall = models.FloatField(verbose_name="レーダ雨量", null=True, blank=True)
    idw_anomaly = models.FloatField(verbose_name="IDW異常", null=True, blank=True)
    upper_limit = models.FloatField(verbose_name="上限値", null=True, blank=True)
    missing_or_unreceived = models.BooleanField(verbose_name="欠測・未受信", default=False)
    consecutive_abnormal_values = models.IntegerField(verbose_name="連続する異常値", null=True, blank=True)

    def __str__(self):
        return f"{self.station_name} - {self.observation_datetime}"

class WatchStatus(models.Model):
    """CSV監視の状態を管理するモデル"""
    is_watching = models.BooleanField(default=False, verbose_name="監視中")
    last_checked = models.DateTimeField(auto_now=True, verbose_name="最終チェック時刻")
    processed_files_count = models.IntegerField(default=0, verbose_name="処理済みファイル数")
    error_count = models.IntegerField(default=0, verbose_name="エラー数")
    
    class Meta:
        verbose_name = "監視状態"
        verbose_name_plural = "監視状態"
    
    def __str__(self):
        status = "監視中" if self.is_watching else "停止中"
        return f"CSV監視 - {status}"

class ProcessedFile(models.Model):
    """処理済みCSVファイルの情報を管理するモデル"""
    file_name = models.CharField(max_length=255, verbose_name="ファイル名", unique=True)
    file_path = models.CharField(max_length=500, verbose_name="ファイルパス")
    file_size = models.BigIntegerField(verbose_name="ファイルサイズ")
    file_hash = models.CharField(max_length=64, verbose_name="ファイルハッシュ")
    processed_at = models.DateTimeField(auto_now_add=True, verbose_name="処理日時")
    records_count = models.IntegerField(default=0, verbose_name="レコード数")
    status = models.CharField(max_length=20, choices=[
        ('success', '成功'),
        ('error', 'エラー'),
        ('partial', '部分成功'),
    ], default='success', verbose_name="処理状態")
    error_message = models.TextField(blank=True, null=True, verbose_name="エラーメッセージ")
    
    class Meta:
        verbose_name = "処理済みファイル"
        verbose_name_plural = "処理済みファイル"
        ordering = ['-processed_at']
    
    def __str__(self):
        return f"{self.file_name} - {self.processed_at.strftime('%Y-%m-%d %H:%M')}"

