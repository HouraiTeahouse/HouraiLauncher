# -*- mode: python -*-

block_cipher = None

a = Analysis(['../src/main.py'],
             pathex=[
              './src',
              'C:/Python35-x64/Lib/site-packages/PyQt5/Qt/bin'
             ],
             binaries=[],
             datas=[
              ('../config.json', '.'),
              ('../img/*', 'img'),
              ('../i18n/*', 'i18n')
             ],
             hiddenimports=[
              'config',
              'babel.dates',
              'babel.numbers'
            ],
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
          exclude_binaries=True,
          name='launcher',
          debug=False,
          strip=False,
          upx=True,
          console=False,
          icon="img/256x256.ico")
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='launcher')
