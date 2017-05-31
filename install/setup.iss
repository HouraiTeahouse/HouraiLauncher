; Setup Config file for Windows Installer
; Note this is only for 64-bit installations
; Uses the Inno Setup program to compile a *.exe file to install the program
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

#define ARCH            'x64'
#define BITS            '64'
#define ARCH_ALLOWED    'x64'

#define APP_NAME      'Fantasy Crescendo'
#define APP_VERSION   '0.3.0-alpha'
#define BUILD_NAME    'launcher'

#define README        '..\README.md'
#define LICENSE       '..\LICENSE'

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
AppId=7247CA18-94BF-4A24-8CB8-086FC8C8614D
AppName={#APP_NAME}
AppVersion={%APPVEYOR_BUILD_VERSION|#APP_VERSION}
AppVerName={#APP_NAME}
AppPublisher=Hourai Teahouse
AppPublisherURL=http://houraiteahouse.net
AppSupportURL=http://houraiteahouse.net
AppUpdatesURL=http://houraiteahouse.net
DefaultDirName=C:\Games\{#APP_NAME}
DefaultGroupName={#APP_NAME}
SetupIconFile=..\img\app.ico
AllowNoIcons=yes
;AppReadmeFile={#README}
LicenseFile={#LICENSE}
OutputBaseFilename=FC_Setup
;_v{%APPVEYOR_BUILD_VERSION|APP_VERSION}
WizardImageFile=installer_image.bmp
WizardSmallImageFile=small_installer_image.bmp
WizardImageStretch=no
Compression=lzma/ultra64
SolidCompression=yes
OutputDir=..\dist
UsePreviousAppDir=yes
ArchitecturesAllowed={#ARCH_ALLOWED}
#if BITS == '64'
ArchitecturesInstallIn64BitMode={#ARCH}
#endif

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "dutch"; MessagesFile: "compiler:Languages\Dutch.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"
Name: "portuguese"; MessagesFile: "compiler:Languages\Portuguese.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 0,6.1

[Dirs]
Name: "{app}"; Flags: uninsalwaysuninstall; Permissions: users-full;

[Files]
Source: "{#LICENSE}"; DestDir: "{app}"; Flags: ignoreversion;
Source: "..\dist\*.*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion;

[Icons]
Name: "{group}\{#APP_NAME}"; Filename: "{app}\{#BUILD_NAME}.exe"
Name: "{commondesktop}\{#APP_NAME}"; Filename: "{app}\{#BUILD_NAME}.exe"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#APP_NAME}"; Filename: "{app}\{#BUILD_NAME}.exe"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#BUILD_NAME}.exe"; Description: "{cm:LaunchProgram,Fantasy Crescendo}"; Flags: nowait postinstall skipifsilent

