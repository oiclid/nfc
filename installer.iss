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

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
Source: "dist\NFC-Cooperative\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\NFC Cooperative";           Filename: "{app}\NFC-Cooperative.exe"
Name: "{group}\Uninstall NFC Cooperative"; Filename: "{uninstallexe}"
Name: "{commondesktop}\NFC Cooperative";   Filename: "{app}\NFC-Cooperative.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\NFC-Cooperative.exe"; Description: "Launch NFC Cooperative"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; user data in AppData is intentionally preserved on uninstall
Type: dirifempty; Name: "{app}"
