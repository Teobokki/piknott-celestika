#define MyVer "1.0.0"
[Setup]
AppId={{B4C2E7A1-5D3F-4A9B-9E61-7C0D2F8A3B54}
AppName=PIKNOTT CELESTIKA
AppVersion={#MyVer}
AppVerName=PIKNOTT CELESTIKA {#MyVer}
AppPublisher=EX Inc./HYPERION DIGITAL
AppPublisherURL=https://github.com/Teobokki/piknott-celestika
AppCopyright=©2026 EX Inc./HYPERION DIGITAL ©2026
VersionInfoVersion={#MyVer}.0
VersionInfoCompany=EX Inc./HYPERION DIGITAL
VersionInfoCopyright=©2026 EX Inc./HYPERION DIGITAL ©2026
VersionInfoProductName=PIKNOTT CELESTIKA
VersionInfoDescription=PIKNOTT CELESTIKA Setup
DefaultDirName={localappdata}\Programs\PIKNOTT CELESTIKA
DefaultGroupName=PIKNOTT CELESTIKA
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=PIKNOTT.CELESTIKA.Setup.{#MyVer}
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\PIKNOTT CELESTIKA.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[InstallDelete]
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "dist\PIKNOTT CELESTIKA\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\PIKNOTT CELESTIKA"; Filename: "{app}\PIKNOTT CELESTIKA.exe"
Name: "{group}\Uninstall PIKNOTT CELESTIKA"; Filename: "{uninstallexe}"
Name: "{userdesktop}\PIKNOTT CELESTIKA"; Filename: "{app}\PIKNOTT CELESTIKA.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\PIKNOTT CELESTIKA.exe"; Description: "Launch PIKNOTT CELESTIKA now"; Flags: nowait postinstall skipifsilent
