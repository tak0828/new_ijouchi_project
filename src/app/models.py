from django.db import models
from decimal import Decimal
from django.db.backends.base.base import BaseDatabaseWrapper





class CustomTextField(models.TextField):
    """ "デフォルトは longtext になるため、text に変更するためのTextField"""

    def db_type(self, connection: BaseDatabaseWrapper):
        if connection.settings_dict["ENGINE"] == "django.db.backends.mysql":
            return "text"
        else:
            return super(CustomTextField, self).db_type(connection=connection)


# 193サーバーから取得した調査書更新用のテーブル
class MS_Kansokujo_Update(models.Model):


    KansokujoCD = models.CharField('観測所コード', max_length=20, primary_key=True)
    ShubetsuCD = models.CharField('観測所種別コード', max_length=20, null=True, blank=True)
    KansokujoCD2 = models.CharField('観測所コード(川防用)', max_length=20)
    KansokujoName = CustomTextField('観測所名')
    KansokujoYomi = CustomTextField('観測所読み', null=True, blank=True)
    Shozaichi = CustomTextField('所在地', null=True, blank=True)
    CenterCD = models.CharField('センター(運用課)コード', max_length=20, null=True, blank=True)
    ShozokuCD = models.CharField('所属区分コード', max_length=20, null=True, blank=True)
    KanriCD = models.CharField('管理区分コード', max_length=20, null=True, blank=True)
    KenCD = models.CharField('都道府県コード', max_length=10, null=True, blank=True)
    JimushoCD = models.CharField('事務所コード', max_length=20, null=True, blank=True)
    JimushoCD2 = models.CharField('事務所コード2', max_length=20, null=True, blank=True)
    SuikeiCD = models.CharField('水系コード(入力用)', max_length=20, null=True, blank=True)
    SuikeiCD2 = models.CharField('水系コード(出力用)', max_length=20, null=True, blank=True)
    KasenCD = models.CharField('河川コード(入力用)', max_length=20, null=True, blank=True)
    KasenCD2 = models.CharField('河川コード(出力用)', max_length=20, null=True, blank=True)
    Hyokou = CustomTextField('標高', null=True, blank=True)
    Ido = CustomTextField('緯度', null=True, blank=True)
    Keido = CustomTextField('経度', null=True, blank=True)
    KijunFLG = models.BooleanField('基準観測所フラグ', default=False)
    TenyuryokuFLG = models.BooleanField('手入力フラグ', default=False)
    StartYMD = models.DateField('観測開始日', null=True, blank=True)
    EndYMD = models.DateField('観測終了日', null=True, blank=True)
    HyoujiNo = models.IntegerField('画面表示順', null=True, blank=True)
    ShutsuryokuNo = models.IntegerField('帳票出力順', null=True, blank=True)
    K_GroupCD = models.CharField('一斉欠測グループコード', max_length=20, null=True, blank=True)
    S_GroupCD = models.CharField('出力観測所グループコード', max_length=20, null=True, blank=True)
    SuiiShuuchiFLG = models.BooleanField('水位周知フラグ', default=False)
    KansokuKikiCD = models.CharField('観測機器コード', max_length=20, null=True, blank=True)
    KansokuKikiYMD = models.CharField('観測機器更新日', max_length=20, null=True, blank=True)
    CreateTime = models.DateTimeField('レコード作成日時', auto_now_add=True)
    UpdateTime = models.DateTimeField('レコード更新日時', auto_now=True)
    DelFlg = models.BooleanField('削除フラグ', default=False)
    DblFlg = models.BooleanField('重複フラグ', default=False)
    K_Time = models.CharField('欠測継続時間', max_length=20, null=True, blank=True)
    Kijunchi = models.CharField('基準値', max_length=20, null=True, blank=True)
    Jougenchi = models.CharField('上限値', max_length=20, null=True, blank=True)
    Kagenchi = models.CharField('下限値', max_length=20, null=True, blank=True)
    Hendouryou = models.DecimalField('変動量', max_digits=6, decimal_places=2, null=True, blank=True)
    TempFile01 = models.ImageField('添付ファイル1', upload_to='kansokujo_photos/', null=True, blank=True)
    TempFile02 = models.ImageField('添付ファイル2', upload_to='kansokujo_photos/', null=True, blank=True)
    TempFile03 = models.ImageField('添付ファイル3', upload_to='kansokujo_photos/', null=True, blank=True)
    TempFile04 = models.ImageField('添付ファイル4', upload_to='kansokujo_photos/', null=True, blank=True)
    TempFile05 = models.ImageField('添付ファイル5', upload_to='kansokujo_photos/', null=True, blank=True)
    TempFile06 = models.ImageField('添付ファイル6', upload_to='kansokujo_photos/', null=True, blank=True)
    TempFile07 = models.ImageField('添付ファイル7', upload_to='kansokujo_photos/', null=True, blank=True)
    TempFile08 = models.ImageField('添付ファイル8', upload_to='kansokujo_photos/', null=True, blank=True)
    TempFile09 = models.ImageField('添付ファイル9', upload_to='kansokujo_photos/', null=True, blank=True)
    TempFile10 = models.ImageField('添付ファイル10', upload_to='kansokujo_photos/', null=True, blank=True)

    class Meta:
        verbose_name = verbose_name_plural = "観測所更新マスタ(MS_Kansokujo_Update)"
        db_table = "MS_Kansokujo_Update"
        ordering = ["KansokujoCD"]



    def __str__(self):
        return f"{self.KansokujoCD}: {self.KansokujoName}"



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

