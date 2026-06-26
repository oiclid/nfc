[Setup]
AppName=NFC Cooperative Management System
AppVersion=2.0.0
AppPublisher=Nigerian Film Corporation
AppPublisherURL=https://codeberg.org/oiclid/nfc
DefaultDirName={autopf}\NFC-Cooperative
DefaultGroupName=NFC Cooperative
OutputDir=dist\installer
OutputBaseFilename=NFC-Cooperative-Setup-v2.0.0
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
; lowest = no admin required, installs per-user
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
; Show a friendly icon in Add/Remove Programs
UninstallDisplayIcon={app}\NFC-Cooperative.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: checkedonce

[Files]
; PyInstaller 6+ puts everything under _internal\; older versions put it at root.
; Recurse the whole dist folder so both layouts are covered.
Source: "dist\NFC-Cooperative\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\NFC Cooperative";           Filename: "{app}\NFC-Cooperative.exe"
Name: "{group}\Uninstall NFC Cooperative"; Filename: "{uninstallexe}"
Name: "{commondesktop}\NFC Cooperative";   Filename: "{app}\NFC-Cooperative.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\NFC-Cooperative.exe"; Description: "Launch NFC Cooperative"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; User data in %APPDATA%\NFC-Cooperative is intentionally preserved on uninstall.
; Only remove the install folder if it's empty after uninstall.
Type: dirifempty; Name: "{app}"
