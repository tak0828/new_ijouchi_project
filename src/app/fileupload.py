import paramiko
from pathlib import Path


DateNo = "202509****-***"
ServPathK = "Temp/*****/"
ServPathH = "Temp/*****/"


UpFileName = "*****"
HostName = "*******"
UserName = "*******"
PassWD = "*******"



# 監視者のPath
ServPath = ServPathK + DateNo
# 判断者のPath
ServPath = ServPathK + DateNo

# Fileアップロード
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HostName, username=UserName, password=PassWD)
sftp = ssh.open_sftp()
# Path の確認*******************************
dir_path = Path(ServPath)
# ディレクトリが存在しない場合は作成
dir_path.mkdir(parents=True, exist_ok=True)
# ここまで**********************************

sftp.put(UpFileName, ServPath+UpFileName)

sftp.close()
ssh.close()