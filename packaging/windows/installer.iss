; Inno Setup 6 스크립트. build_win.ps1 이 호출.
#define AppName "MouseBridge"
#define AppVersion "0.4.0"

[Setup]
AppId={{B7A1E3C2-5D4F-4C8E-9A61-2F0D7E6C1B90}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
OutputDir=..\..\dist
OutputBaseFilename={#AppName}-Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
UninstallDisplayName={#AppName}

[Tasks]
Name: "autostart"; Description: "로그인 시 자동 실행"; GroupDescription: "추가 작업:"
Name: "firewall";  Description: "Windows 방화벽 예외 추가 (TCP 24800)"; GroupDescription: "추가 작업:"

[Files]
; onedir 빌드 결과 폴더 전체
Source: "..\..\dist\MouseBridge\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\MouseBridge.exe"
Name: "{group}\{#AppName} 제거"; Filename: "{uninstallexe}"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; \
  ValueName: "{#AppName}"; ValueData: """{app}\MouseBridge.exe"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "netsh"; Parameters: "advfirewall firewall add rule name=""{#AppName}"" dir=in action=allow protocol=TCP localport=24800"; \
  Flags: runhidden; Tasks: firewall
Filename: "{app}\MouseBridge.exe"; Description: "{#AppName} 실행"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""{#AppName}"""; Flags: runhidden; RunOnceId: "fw"
