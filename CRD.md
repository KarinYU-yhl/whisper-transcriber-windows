# Customer Requirement Document (CRD)

## 1. 概要 (Overview)
本ドキュメントは、Apple Silicon搭載のMac上で動作する、高精度な音声文字起こしアプリケーションの要件を定義するものです。OpenAIのWhisper V3モデルを使用し、Apple SiliconのGPU性能を活かした高速な処理を実現します。

## 2. ターゲット環境 (Target Environment)
*   **OS**: macOS (Apple Silicon搭載機: M1, M2, M3, M4など)
*   **ハードウェア**: Apple Silicon GPU/NPUを利用
*   **言語**: Python 3.8以上
*   **パッケージ管理**: `uv` (Astral) を必須とする。

## 3. 機能要件 (Functional Requirements)

### 3.1 入力 (Input)
*   **GUI**: ユーザーはGUI上の「Browse」ボタンから音声ファイルを選択できること。
*   サポートする音声フォーマット: FFmpegがサポートする一般的な形式 (mp3, wav, m4a, mp4など)。

### 3.2 処理 (Processing)
*   **エンジン**: `mlx-whisper` ライブラリを使用すること。
*   **モデル**: `whisper-large-v3` (mlx-community版) を使用し、高い認識精度を提供すること。
*   **ハードウェアアクセラレーション**: AppleのMLXフレームワークを通じて、Apple SiliconのGPUを自動的に利用して推論を行うこと。
*   **非同期処理**: GUIがフリーズしないよう、文字起こし処理は別スレッドで実行すること。

### 3.3 出力 (Output)
*   文字起こし結果を**テキストファイル (.txt)** として保存すること。
*   **ファイル名規則**: 出力ファイル名は、入力音声ファイルの拡張子を `.txt` に変更したものとすること (例: `audio.mp3` -> `audio.txt`)。
*   **保存場所**: 入力ファイルと同じディレクトリに出力すること。
*   **GUI表示**: 処理状況（開始、完了、エラー）と保存先パスをGUI上のログエリアに表示すること。

## 4. 非機能要件 (Non-Functional Requirements)
*   **パフォーマンス**: CPUのみの処理と比較して、GPUを利用することで高速に文字起こしが完了すること。
*   **依存関係**:
    *   `ffmpeg`: 音声処理用
    *   `mlx-whisper`: 推論エンジン
    *   `customtkinter`: モダンなGUIフレームワーク
*   **ユーザビリティ**: シンプルで直感的なGUIを提供すること。ダークモードに対応すること。

## 6. 配布・ライセンス (Distribution & Licensing)
*   **配布形態**: ソースコード配布、またはMac App Store**以外**でのバイナリ配布（DMG等）。
*   **App Store制限**: FFmpegへの依存（外部コマンド呼び出し）があるため、Mac App Storeでの配布は行わない（App Storeのサンドボックス規定およびライセンス規定により困難なため）。
*   **ユーザー責任**: FFmpegのインストールはユーザー自身の責任で行うものとする。

## 7. 将来の拡張性 (Future Scope) - オプション
*   モデルサイズの選択 (tiny, small, mediumなど)
*   出力フォーマットの選択 (srt, vttなど)
*   ドラッグ＆ドロップへの対応
