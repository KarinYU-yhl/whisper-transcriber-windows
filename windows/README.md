# Whisper Transcriber（Windows 版）

macOS 版 `mlx-whisper` 语音转文字工具的 **Windows 移植版**。

macOS 版使用 Apple 专有的 MLX 框架（仅支持 Apple Silicon 的 Metal GPU），
本版本把推理引擎替换为 **[faster-whisper](https://github.com/SYSTRAN/faster-whisper)（CTranslate2）**，
可在 Windows 上使用 **CPU** 或 **NVIDIA CUDA GPU** 运行，并自动选择设备。

界面、拖拽、批量处理、模型选择、语言选择、Hugging Face 缓存管理、离线本地模型加载等功能与原版保持一致。

---

## 与 macOS 版的对应关系

| 能力 | macOS 版 | Windows 版 |
|---|---|---|
| GUI | customtkinter + tkinterdnd2 | 相同（跨平台） |
| 推理引擎 | `mlx-whisper`（Apple Silicon） | `faster-whisper`（CPU / CUDA） |
| 音频解码 | 系统 FFmpeg（`brew install ffmpeg`） | PyAV 内置 FFmpeg，**无需单独安装** |
| 模型仓库 | `mlx-community/whisper-*` | `Systran/faster-whisper-*` |
| 硬件加速 | Metal GPU | CUDA GPU（有则自动用），否则 CPU int8 |
| 打包 | PyInstaller → `.app` + DMG + 签名 | PyInstaller → `.exe`（免签名） |

> 注意：两个版本的模型格式不同，Windows 版不能直接加载 MLX 模型，请使用 `Systran/faster-whisper-*` 系列模型。

---

## 快速开始（从源码运行）

> 支持 Python 3.9 - 3.14。已验证 `ctranslate2` / `faster-whisper` 提供了
> Python 3.14 的预编译 wheel（`cp314`），可直接使用当前环境的 Python。

```powershell
# 1. 进入 windows 目录
cd windows

# 2. 创建并激活虚拟环境
py -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. 安装依赖
pip install -r requirements.txt

# 4. 运行 GUI
python gui.py
```

首次转写时会自动从 Hugging Face 下载所选模型（几百 MB 到 ~3GB 不等），下载后缓存供后续使用。

### 命令行用法

```powershell
python transcribe.py "C:\path\to\audio.mp3" --model large-v3 --language ja
```

- `--model`：`tiny` / `base` / `small` / `medium` / `large-v3` / `large-v3-turbo`，或 HF 仓库 id，或本地模型文件夹路径
- `--language`：语言代码（如 `en`、`ja`、`zh`），省略则自动检测

输出为与输入同名的 `.txt` 文件，保存在输入文件所在目录。

---

## 录制 Teams（或任意应用）会议并转写

界面里有一个 **● Record Meeting** 按钮，用于把正在开的会议直接转成文字：

1. 打开并加入你的 Teams 会议。
2. 在本工具里选好 **模型** 和 **语言**（中文选 `Chinese`，或 `Auto`）。
3. 点 **● Record Meeting** 开始录制，按钮变红显示计时和音量条。
4. 会议结束后点 **■ Stop & Transcribe**，工具会自动保存录音并转写。

录制内容包含两路并自动混音：

- **系统声音（WASAPI 环回）**：Teams 从扬声器播放的声音，即**其他参会者**。
- **你的麦克风**：你**自己发言**的声音。

> 录音文件保存在 `C:\Users\你\WhisperMeetings\meeting_YYYYMMDD_HHMMSS.wav`，
> 转写文本 `.txt` 与之同名同目录。

小贴士：

- 会议全程保持本工具运行；**用扬声器外放**效果最好。若戴**耳机**，系统环回同样能录到对方声音（因为音频仍经过系统混音输出）。
- 只想录对方、不录自己：目前默认同时录制，如需只录系统声音可告知我改成可选开关。
- 长会议会占用一定内存（16kHz 单声道，约每小时 ~230MB×2 路），一般 1-2 小时会议没问题。

## GPU 加速（可选）

- 若安装了 **NVIDIA GPU + CUDA 运行库**，程序会自动使用 GPU（`float16`），速度大幅提升。
- faster-whisper 需要 cuBLAS 与 cuDNN。GPU 环境准备可参考
  [faster-whisper 的 GPU 说明](https://github.com/SYSTRAN/faster-whisper#gpu)。
- 无 GPU 时自动回退到 CPU（`int8` 量化），也能正常工作，只是较慢。

界面右侧「Compute:」会显示当前实际使用的设备。

---

## 打包成可分享的安装包

```powershell
cd windows
.\.venv\Scripts\Activate.ps1
python build.py
```

生成物位于 `dist\WhisperTranscriber\WhisperTranscriber.exe`（onedir 形式，**不依赖 Python 环境**）。

### 制作分享给同事的 zip 安装包

```powershell
# 把使用手册放进程序文件夹
Copy-Item .\使用手册.md .\dist\WhisperTranscriber\使用手册.txt
# 压缩成一个 zip
Compress-Archive -Path .\dist\WhisperTranscriber -DestinationPath .\dist\WhisperTranscriber_v1.0.27.zip -Force
```

得到的 `WhisperTranscriber_v1.0.27.zip`（约 90MB）即可直接发给同事：
**解压 → 双击 `WhisperTranscriber.exe` 即可使用，无需安装任何东西**（首次转写会联网下载模型）。

面向同事的完整图文说明见 [`使用手册.md`](使用手册.md)。

---

## 离线 / 内网使用

1. 访问对应模型页面，例如 <https://huggingface.co/Systran/faster-whisper-large-v3/tree/main>
2. 下载全部文件（`config.json`、`model.bin`、`tokenizer.json`、`vocabulary.txt`）到一个文件夹
3. 在界面点击绿色的 **Load Local...**，选择该文件夹

程序内置 `truststore`，会使用系统证书库，兼容企业代理 / SSL 检查环境。

---

## 常见问题

- **安装 `ctranslate2` 失败**：确认使用 64 位 Python；若 Python 版本极新暂无 wheel，可改用 3.11/3.12。
- **首次运行下载很慢 / 失败**：可能是网络或防火墙拦截 Hugging Face，可先在浏览器打开模型页面，或使用离线模式。
- **中文识别**：语言选 `Chinese` 或命令行 `--language zh`；也可用 `Auto` 自动检测。

## 许可证

MIT（沿用原项目）
