import os
import sys
import shutil
import subprocess
from directory_yml import __version__

def create_spec_file():
    """一時的なspecファイルを作成"""
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Dir2YAML-{__version__}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Dir2YAML-{__version__}',
)
'''
    with open('temp_build.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    return 'temp_build.spec'

def cleanup_build_files():
    """ビルド関連の一時ファイル・フォルダを削除"""
    paths_to_remove = ['build', '__pycache__', 'directory_yml/__pycache__']
    
    for path in paths_to_remove:
        if os.path.exists(path):
            try:
                if os.path.isfile(path):
                    os.remove(path)
                else:
                    shutil.rmtree(path)
                print(f"Cleaned up: {path}")
            except Exception as e:
                print(f"Warning: Failed to remove {path}: {e}")

def build():
    """ビルドプロセスを実行"""
    print(f"Building Dir2YAML version {__version__}...")
    
    # 一時specファイルを作成
    spec_file = create_spec_file()
    
    try:
        # PyInstallerでビルド
        subprocess.run(['pyinstaller', spec_file], check=True)
        print("\nBuild completed successfully!")
        
        # ビルド後のクリーンアップ
        print("\nCleaning up build files...")
        cleanup_build_files()
        print("\nBuild process completed!")
        print(f"You can find the executable in: dist/Dir2YAML-{__version__}/")
        
    except subprocess.CalledProcessError as e:
        print(f"Build failed with error: {e}")
        sys.exit(1)
        
    finally:
        # 一時specファイルを削除
        if os.path.exists(spec_file):
            os.remove(spec_file)
            print(f"Removed temporary spec file: {spec_file}")

if __name__ == '__main__':
    build()