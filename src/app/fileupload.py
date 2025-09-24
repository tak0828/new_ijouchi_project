import paramiko

ServPath_Kanshisya = "Temp/****/****"
ServPath_Handansya = "Temp/****/****"

UpFileName = "*****"
HostName = "*******"
UserName = "*******"
PassWD = "*******"

# 監視者のPath
ServPath = ServPath_Kanshisya
# 判断者のPath
ServPath = ServPath_Handansya
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HostName, username=UserName, password=PassWD)

sftp = ssh.open_sftp()
sftp.put(UpFileName, ServPath+UpFileName)
sftp.close()
ssh.close()