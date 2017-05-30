# -*- mode: python -*-

block_cipher = None

added_files = [
]

a = Analysis(['src/main.py'],
             pathex=['./src'],
             binaries=[],
             datas=[
              ('config.json', '.'),
              ('img/*', 'img'),
              ('i18n/*', 'i18n'),
              # Need to manually add PyQt DLLs due to bug in PyInstaller
              ('C:\\Python35\\Lib\\site-packages\\PyQt5\\Qt\\bin\\Qt5Core.dll', '.'),
              ('C:\\Python35\\Lib\\site-packages\\PyQt5\\Qt\\bin\\Qt5Gui.dll', '.'),
              ('C:\\Python35\\Lib\\site-packages\\PyQt5\\Qt\\bin\\Qt5Widgets.dll', '.')
             ],
             hiddenimports=['config'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='launcher',
          debug=False,
          strip=False,
          upx=True,
          console=True )
