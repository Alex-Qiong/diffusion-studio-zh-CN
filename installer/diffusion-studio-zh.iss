; Diffusion Studio v0.207.0 简体中文版 - Inno Setup 脚本
#define MyAppName "Diffusion Studio"
#define MyAppVersion "0.207.0"
#define MyAppPublisher "Diffusion Studio"
#define MyAppURL "https://github.com/diffusionstudio/editor"
#define MyAppExeName "Diffusion Studio.exe"

[Setup]
AppId={{7202f1e9-71a2-4fcf-8f6b-b3982da28705}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion} 简体中文版
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\final_app\LICENSE
InfoBeforeFile=简体中文版说明.txt
OutputDir=output
OutputBaseFilename=Diffusion-Studio-v0.207.0-zh-CN-x64-Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName={#MyAppName} v{#MyAppVersion} 简体中文版
VersionInfoVersion={#MyAppVersion}
VersionInfoDescription={#MyAppName} 简体中文版安装程序

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\final_app\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "squirrel.exe,Diffusion Studio_ExecutionStub.exe"
Source: "简体中文版说明.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
