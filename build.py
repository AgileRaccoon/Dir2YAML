import os
import sys
import shutil
import subprocess
import zipfile
from directory_yml import __version__

def create_package_readme():
    """パッケージ用のREADMEを作成"""
    readme_content = f'''# Dir2YAML

ディレクトリ構造をYAML形式で出力するGUIアプリケーションです。

## 使い方

1. `Dir2YAML.exe` を実行します。

2. GUI画面が開いたら、以下の手順で操作してください：

   a. 「ディレクトリ追加」ボタンをクリックし、解析したいフォルダを選択  
   b. 必要に応じて「プロジェクト名」を入力（任意）  
   c. 「YAML生成」ボタンをクリック  
   d. 生成されたYAMLを「コピー」または「保存」

3. 除外設定：
   - デフォルトで `.env`, `.htpasswd`, `*.log` は除外されます
   - 追加の除外パターンを登録する場合は「ユーザパターン」に入力し、「登録」をクリック
   - 例: `*.tmp, *.bak`

4. 設定の保存：
   - 指定したディレクトリや除外パターンは `config.json` に自動保存されます
   - 次回起動時に自動的に読み込まれます

## 詳細情報

- 複数のディレクトリを同時に解析できます
- 大きなファイルやバイナリファイルの内容は自動的にスキップされます
- 進捗状況は画面下部のログで確認できます

## お問い合わせ

バグ報告や機能要望は以下のGitHubリポジトリでお受けしています：  
https://github.com/AgileRaccoon/Dir2YAML/issues

---
Dir2YAML version {__version__}
MIT License - Copyright (c) 2025 AgileRaccoon'''
    
    return readme_content

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
    name='Dir2YAML',  # バージョン無しの名前に変更
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
    name='Dir2YAML',  # バージョン無しの名前に変更
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

def create_distribution_files():
    """配布用ファイルの作成とコピー"""
    # 元のビルドディレクトリ
    original_dist_dir = os.path.join('dist', 'Dir2YAML')
    
    # バージョン付きの新しいディレクトリ名
    versioned_dir_name = f'Dir2YAML-{__version__}'
    versioned_dist_dir = os.path.join('dist', versioned_dir_name)
    
    # 既存のバージョン付きディレクトリがあれば削除
    if os.path.exists(versioned_dist_dir):
        shutil.rmtree(versioned_dist_dir)
    
    # ディレクトリをバージョン付きの名前にリネーム
    os.rename(original_dist_dir, versioned_dist_dir)
    
    # READMEの作成
    readme_content = create_package_readme()
    readme_path = os.path.join(versioned_dist_dir, 'README.txt')
    try:
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        print(f"Created README at: {readme_path}")
    except Exception as e:
        print(f"Warning: Failed to create README: {e}")
    
    # ZIPファイルの作成
    zip_filename = os.path.join('dist', f'{versioned_dir_name}.zip')
    try:
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(versioned_dist_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.join(versioned_dir_name, 
                                         os.path.relpath(file_path, versioned_dist_dir))
                    zipf.write(file_path, arcname)
        print(f"\nCreated ZIP file: {zip_filename}")
    except Exception as e:
        print(f"Warning: Failed to create ZIP file: {e}")

def build():
    """ビルドプロセスを実行"""
    print(f"Building Dir2YAML version {__version__}...")
    
    # 一時specファイルを作成
    spec_file = create_spec_file()
    
    try:
        # PyInstallerでビルド
        subprocess.run(['pyinstaller', spec_file], check=True)
        print("\nBuild completed successfully!")
        
        # 配布用ファイルの作成
        print("\nCreating distribution files...")
        create_distribution_files()
        
        # ビルド後のクリーンアップ
        print("\nCleaning up build files...")
        cleanup_build_files()
        
        print("\nBuild process completed!")
        print(f"You can find the package in: dist/Dir2YAML-{__version__}.zip")
        print(f"Unzipped files are in: dist/Dir2YAML-{__version__}/")
        
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