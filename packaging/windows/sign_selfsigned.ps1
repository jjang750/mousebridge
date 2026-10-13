# 자체 서명 인증서 생성 + 신뢰 루트 등록 (본인 PC 전용, 1회). 관리자 PowerShell 에서 실행.
#   powershell -ExecutionPolicy Bypass -File packaging\windows\sign_selfsigned.ps1
# 이후 build_win.ps1 이 자동으로 exe 에 서명. 다른 PC 에 설치하려면 그 PC 에도 인증서(.cer) 를 신뢰 루트에 등록해야 함.
$ErrorActionPreference = "Stop"
$cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject "CN=MouseBridge Dev" `
    -CertStoreLocation Cert:\CurrentUser\My -NotAfter (Get-Date).AddYears(5)
$cer = "$PSScriptRoot\MouseBridgeDev.cer"
Export-Certificate -Cert $cert -FilePath $cer | Out-Null
Import-Certificate -FilePath $cer -CertStoreLocation Cert:\LocalMachine\Root | Out-Null
Import-Certificate -FilePath $cer -CertStoreLocation Cert:\LocalMachine\TrustedPublisher | Out-Null
Write-Host "완료: $cer (다른 PC 에 설치 시 이 파일을 신뢰 루트에 등록)"
