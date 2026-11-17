# 解密渠道/游戏配置类 XML：输入文件是 base64 文本，AES + PKCS7（默认 ECB），key 为 ASCII
#
# 用法: powershell -NoProfile -File src/decrypt_aes_cfg.ps1 -Src x.xml -Dst plain.xml -Key 0123456789abcdef
#   -Mode CBC -InitVec 0000000000000000   可选（CBC 必须给 16 字节 IV）
# 说明: 找不到 key 时先用 src/apk_findstr.py 在 dex 里搜 16/24/32 字符常量，再逐个试。
# 注意: 参数名不能用 -In / -Iv（与 PowerShell 公共参数别名冲突），故用 -Src / -Dst / -InitVec。
param(
  [Parameter(Mandatory=$true)][string]$Src,
  [Parameter(Mandatory=$true)][string]$Dst,
  [Parameter(Mandatory=$true)][string]$Key,
  [ValidateSet("ECB","CBC")][string]$Mode = "ECB",
  [string]$InitVec = ""
)

$txt = [IO.File]::ReadAllText((Resolve-Path $Src)).Trim()
$ct = [Convert]::FromBase64String($txt)
$aes = [Security.Cryptography.Aes]::Create()
$aes.Mode = $Mode
$aes.Padding = [Security.Cryptography.PaddingMode]::PKCS7
$aes.Key = [Text.Encoding]::UTF8.GetBytes($Key)
if ($InitVec -ne "") { $aes.IV = [Text.Encoding]::UTF8.GetBytes($InitVec) }
$pt = $aes.CreateDecryptor().TransformFinalBlock($ct, 0, $ct.Length)
[IO.File]::WriteAllBytes((Join-Path (Get-Location) $Dst), $pt)
Write-Output ("ok bytes=" + $pt.Length)

