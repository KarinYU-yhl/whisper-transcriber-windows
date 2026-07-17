# Low-Level Design (LLD)

## 1. はじめに (Introduction)
本ドキュメントは、HLDに基づき、各モジュールの詳細設計、クラス設計、および処理フローを定義します。実装者がコードを記述するために十分な詳細レベルを提供することを目的とします。

## 2. モジュール構成 (Module Structure)

プロジェクトは単一のスクリプトファイル (`gui.py`) を中心に構成されますが、将来的な拡張性を考慮し、論理的には以下の構造を持ちます。

```
mlx-whisper-mac/
├── gui.py              # メインエントリポイント、GUI、ロジック
├── requirements.txt    # 依存パッケージリスト
├── README.md           # ドキュメント
└── CRD.md / HLD.md / LLD.md
```

## 3. クラス詳細設計 (Class Design)

### 3.1 `class App(ctk.CTk)`
アプリケーションのメインウィンドウを表すクラス。`customtkinter.CTk` を継承します。

#### プロパティ (Properties)
| 名前 | 型 | 説明 |
| :--- | :--- | :--- |
| `title_label` | `CTkLabel` | アプリタイトル表示用ラベル |
| `file_frame` | `CTkFrame` | ファイル選択エリアのコンテナ |
| `file_path_entry` | `CTkEntry` | 選択されたファイルパスを表示する入力欄 |
| `browse_button` | `CTkButton` | ファイル選択ダイアログを開くボタン |
| `model_select_menu` | `CTkOptionMenu` | 使用するWhisperモデルを選択するドロップダウン |
| `log_textbox` | `CTkTextbox` | ログやステータスを表示するテキストエリア |
| `transcribe_button` | `CTkButton` | 文字起こし処理を開始するボタン |
| `selected_file` | `str` | 現在選択されている音声ファイルの絶対パス |
| `is_transcribing` | `bool` | 現在文字起こし処理中かどうかのフラグ |

#### メソッド (Methods)

##### `__init__(self)`
*   **説明**: ウィンドウの初期化、レイアウトの構築、イベントハンドラのバインドを行う。
*   **処理**:
    1.  `super().__init__()` コール。
    2.  ウィンドウサイズ (600x400)、タイトル設定。
    3.  グリッドレイアウトの設定。
    4.  各UIウィジェットの生成と配置。

##### `browse_file(self)`
*   **説明**: ファイル選択ダイアログを開く。
*   **トリガー**: `browse_button` クリック。
*   **処理**:
    1.  `filedialog.askopenfilename` を呼び出す。
    2.  フィルタ: `*.mp3`, `*.wav`, `*.m4a`, `*.mp4`, `*.flac`。
    3.  ファイルが選択された場合:
        *   `self.selected_file` を更新。
        *   `self.file_path_entry` にパスを表示。
        *   ログエリアに選択ファイルを記録。

##### `log_message(self, message: str)`
*   **説明**: GUIのログエリアにメッセージを追記する。
*   **引数**: `message` (表示する文字列)
*   **処理**:
    1.  `log_textbox` を `normal` 状態に変更。
    2.  末尾にメッセージと改行を挿入。
    3.  自動スクロール (`see("end")`)。
    4.  `log_textbox` を `disabled` 状態に戻す (読み取り専用化)。

##### `start_transcription_thread(self)`
*   **説明**: 文字起こし処理を別スレッドで開始する。
*   **トリガー**: `transcribe_button` クリック。
*   **処理**:
    1.  `self.selected_file` が空なら警告ダイアログを表示して終了。
    2.  `self.is_transcribing` が `True` なら無視。
    3.  `self.is_transcribing` を `True` に設定。
    4.  UIボタンを無効化 (`disabled`)。
    5.  `threading.Thread` を作成し、`target=self.run_transcription` で開始。

##### `run_transcription(self)`
*   **説明**: 実際の文字起こし処理を行う（ワーカースレッド内で実行）。
*   **処理**:
    1.  `try` ブロック開始。
    2.  GUIで選択されたモデル名を取得 (`self.model_select_menu.get()`)。
    3.  ログに開始メッセージと使用モデルを表示。
    4.  `mlx_whisper.transcribe` を呼び出し。
        *   `path_or_hf_repo` に選択されたモデルID (例: `mlx-community/whisper-large-v3`) を渡す。
    5.  結果辞書から `text` を取得。
    5.  出力ファイルパスを生成 (`os.path.splitext` を使用)。
    6.  ファイルを書き込みモード (`utf-8`) で開き、テキストを保存。
    7.  ログに成功メッセージと保存先パスを表示。
    8.  `messagebox.showinfo` で完了通知。
    9.  `except` ブロック:
        *   エラー内容をログに表示。
        *   `messagebox.showerror` でエラー通知。
    10. `finally` ブロック:
        *   `self.is_transcribing` を `False` に戻す。
        *   `self.after(0, self.reset_ui)` を呼び出し、メインスレッドでUIを復帰させる。

##### `reset_ui(self)`
*   **説明**: UI要素を初期状態（操作可能）に戻す。
*   **処理**:
    1.  `transcribe_button` を有効化し、テキストを "Start Transcription" に戻す。
    2.  `browse_button` を有効化。

## 4. データ構造とアルゴリズム (Data Structures & Algorithms)

### 4.1 文字起こしフロー
特に複雑なアルゴリズムは持たないが、`mlx-whisper` ライブラリの仕様に従う。

1.  **モデルロード**: 初回実行時にHugging Face Hubからモデルキャッシュへダウンロードされる。
2.  **推論**: `mlx_whisper.transcribe(audio_path)` は内部的に以下の処理を行うと想定される。
    *   音声のロードとリサンプリング (16kHz)。
    *   Log-Mel Spectrogram の計算。
    *   Encoder-Decoder モデルによる推論。
    *   トークンのデコードとテキスト生成。

## 5. エラーハンドリング (Error Handling)

| エラー種別 | 原因例 | 処理方針 |
| :--- | :--- | :--- |
| **ファイル未選択** | ユーザーがファイルを選ばずに開始ボタンを押下 | 警告ダイアログを表示し、処理を開始しない。 |
| **ファイル読み込みエラー** | ファイルが破損している、権限がない | 例外をキャッチし、エラーダイアログとログで通知する。 |
| **モデルダウンロード失敗** | ネットワーク未接続 | 例外をキャッチし、ネットワーク確認を促すメッセージを表示する。 |
| **FFmpeg未インストール** | システムにFFmpegがない | `mlx-whisper` 内部でエラーが発生するため、それをキャッチして「FFmpegが必要です」とログに出す（可能であれば）。 |

## 6. セキュリティ考慮事項 (Security Considerations)
*   **ファイルアクセス**: ユーザーが選択したファイルと、そのディレクトリへの書き込み権限が必要。意図しないシステムファイルの上書きを防ぐため、出力ファイル名は自動生成とし、既存ファイルがある場合は上書きする（仕様として明記）。
*   **外部通信**: モデルダウンロードのためにHugging FaceへのHTTPS通信が発生する。
