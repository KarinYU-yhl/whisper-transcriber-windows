# High-Level Design (HLD)

## 1. はじめに (Introduction)
本ドキュメントは、Apple Silicon Mac向け音声文字起こしアプリケーションのアーキテクチャ概要を記述します。CRDに基づき、システムの全体像、主要コンポーネント、およびデータフローを定義します。

## 2. システムアーキテクチャ (System Architecture)

本システムは、ユーザーインターフェース層、アプリケーションロジック層、および推論エンジン層の3層構造を採用します。

```mermaid
graph TD
    User[ユーザー] -->|操作| GUI[GUI Layer (CustomTkinter)]
    GUI -->|イベント| Logic[Application Logic / Controller]
    Logic -->|非同期実行| Thread[Worker Thread]
    Thread -->|APIコール| Engine[Inference Engine (mlx-whisper)]
    Engine -->|GPU計算| Hardware[Apple Silicon GPU/NPU]
    Engine -->|結果返却| Thread
    Thread -->|ファイル書き込み| FileSystem[File System]
    Thread -->|状態更新| GUI
```

## 3. 主要コンポーネント (Key Components)

### 3.1 GUI Layer (Presentation)
*   **役割**: ユーザーからの入力を受け付け、処理状況と結果を表示する。
*   **技術**: `customtkinter`
*   **機能**:
    *   ファイル選択ダイアログの表示
    *   処理開始トリガー
    *   ログ・ステータス表示 (テキストボックス)
    *   エラーメッセージのポップアップ表示

### 3.2 Application Logic (Controller)
*   **役割**: GUIとバックエンド処理の橋渡しを行う。
*   **機能**:
    *   入力値の検証 (ファイルパスの存在確認など)
    *   スレッド管理 (UIフリーズ防止のための非同期実行)
    *   例外処理とユーザーへのフィードバック

### 3.3 Inference Engine (Backend)
*   **役割**: 音声データをテキストに変換する。
*   **技術**: `mlx-whisper` (OpenAI Whisper V3 model)
*   **機能**:
    *   モデルのロード (初回は自動ダウンロード)
    *   音声の前処理 (FFmpeg利用)
    *   推論実行 (Apple Silicon最適化)

### 3.4 File System (Storage)
*   **役割**: 入力音声の読み込みと、結果テキストの保存。
*   **機能**:
    *   音声ファイルの読み込み
    *   `.txt` ファイルの書き出し (UTF-8エンコーディング)

## 4. データフロー (Data Flow)

1.  **入力**: ユーザーがGUIで音声ファイル (`.mp3` 等) を選択。
2.  **トリガー**: 「Start Transcription」ボタン押下。
3.  **処理**:
    *   メインスレッドからワーカースレッドを起動。
    *   `mlx-whisper` が音声ファイルを読み込み、GPUを使用して推論を実行。
4.  **出力**:
    *   推論結果のテキストデータを取得。
    *   入力ファイルと同じディレクトリに同名の `.txt` ファイルを作成し、テキストを書き込む。
5.  **フィードバック**: 完了メッセージまたはエラー詳細をGUIに表示。

## 5. 技術スタック (Technology Stack)

| カテゴリ | 技術 | 備考 |
| :--- | :--- | :--- |
| **言語** | Python 3.8+ | |
| **GUIフレームワーク** | CustomTkinter | モダンなUIコンポーネント |
| **MLライブラリ** | mlx-whisper | Apple MLXフレームワークベース |
| **モデル** | whisper-large-v3 | mlx-community版 |
| **音声処理** | FFmpeg | システムにインストール済みであること |
| **パッケージ管理** | uv | 高速な依存関係解決 |

## 6. 制約事項 (Constraints)
*   Apple Silicon (Mシリーズチップ) 搭載のMacでのみ動作保証。
*   初回実行時に数GB単位のモデルダウンロードが発生するため、インターネット接続が必要。
