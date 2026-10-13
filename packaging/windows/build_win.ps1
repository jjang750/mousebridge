# Windows 빌드: PowerShell 에서 프로젝트 루트 기준으로 실행
#   powershell -ExecutionPolicy Bypass -File packaging\windows\build_win.ps1
# 결과: dist\MouseBridge\ (onedir)  (+ Inno Setup 설치 시 dist\MouseBridge-Setup.exe)
# 디버그(콘솔 표시):  $env:MB_CONSOLE="1"; powershell -ExecutionPolicy Bypass -File packaging\windows\build_win.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..\..")
python -m pip install -r requirements.txt pyinstaller --quiet
python -m PyInstaller --noconfirm --distpath dist --workpath build packaging\mousebridge.spec

# 자체 서명 인증서가 있으면 서명 (sign_selfsigned.ps1 로 1회 생성)
$cert = Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.Subject -eq "CN=MouseBridge Dev" } | Select-Object -First 1
if ($cert) {
    Set-AuthenticodeSignature -FilePath dist\MouseBridge\MouseBridge.exe -Certificate $cert -TimestampServer http://timestamp.digicert.com | Out-Null
    Write-Host "자체 서명 완료"
}

$iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (Test-Path $iscc) {
    & $iscc packaging\windows\installer.iss
    Write-Host "설치파일: dist\MouseBridge-Setup.exe"
} else {
    Write-Host "Inno Setup 미설치: dist\MouseBridge\MouseBridge.exe 만 생성됨 (https://jrsoftware.org/isdl.php)"
}
