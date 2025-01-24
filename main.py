def main():
    """
    アプリケーションのエントリーポイント。
    GUIの初期化を行い、メインループを開始する。
    """
    from directory_yml.gui import DirectoryYmlGUI
    app = DirectoryYmlGUI()
    app.run()

if __name__ == "__main__":
    main()
