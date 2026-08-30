; Macacolandia · instalador NSIS opcional
!include "MUI2.nsh"
Name "Macacolandia"
OutFile "dist\Macacolandia-Setup.exe"
InstallDir "$PROGRAMFILES\Macacolandia"
RequestExecutionLevel user

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_LANGUAGE "PortugueseBR"

Section "Macacolandia" SEC_MAIN
  SetOutPath "$INSTDIR"
  File "dist\Macacolandia.exe"
  CreateShortcut "$DESKTOP\Macacolandia.lnk" "$INSTDIR\Macacolandia.exe"
SectionEnd
