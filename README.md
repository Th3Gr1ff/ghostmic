# GhostMic

**Invisible AI meeting assistant for Linux.** Captures system audio, transcribes in real-time with local Whisper (GPU-accelerated), and answers questions mid-meeting via Claude. No bots join your call. No cloud transcription. Your audio never leaves your machine.

Built as an open-source alternative to [Cluely](https://cluely.com/).

## What It Does

- **Live transcription** via [faster-whisper](https://github.com/SYSTRAN/faster-whisper) running locally on your GPU (CUDA) or CPU
- **AI Q&A** powered by Claude - ask questions about the conversation in real-time
- **Meeting notes** generated on-demand from the transcript
- **Dark transparent overlay** that stays on top of your windows, draggable, hideable
- **Auto-saves** full transcript to `~/Documents/` on quit
- **Zero cloud audio processing** - Whisper runs entirely on your hardware

## Requirements

- Linux with PulseAudio or PipeWire (tested on Linux Mint 22, Ubuntu 24.04)
- Python 3.10+
- NVIDIA GPU recommended (CUDA) - CPU fallback available
- Anthropic API key (for AI features - transcription works without it)

## Install

```bash
git clone https://github.com/Th3Gr1ff/ghostmic.git
cd ghostmic
chmod +x install.sh
./install.sh
```

The installer:
1. Installs system dependencies (GTK3, PortAudio, etc.)
2. Creates a Python virtual environment at `~/.local/share/ghostmic/venv/`
3. Downloads the Whisper medium model (CUDA if available, CPU fallback)
4. Creates a `ghostmic` launcher at `~/.local/bin/`

## Usage

```bash
# Set your Anthropic API key (optional - transcription works without it)
export ANTHROPIC_API_KEY="sk-ant-..."

# Launch
ghostmic
```

### Hotkeys

| Shortcut | Action |
|---|---|
| `Ctrl+Shift+H` | Toggle overlay visibility (hide before screen sharing) |
| `Ctrl+Shift+N` | Generate meeting notes from transcript |
| `Ctrl+Shift+Space` | Focus the input field |
| `Enter` | Send question to Claude (when input is focused) |
| `Ctrl+Q` | Quit (auto-saves transcript) |

### Options

```bash
ghostmic --model small        # Use smaller/faster Whisper model
ghostmic --model large-v3     # Use largest/most accurate model
ghostmic --device cpu          # Force CPU mode (no GPU)
ghostmic --llm claude-sonnet-4-20250514  # Change Claude model
```

### Whisper Model Sizes

| Model | VRAM | Speed | Accuracy |
|---|---|---|---|
| `tiny` | ~1 GB | Fastest | Basic |
| `base` | ~1 GB | Fast | OK |
| `small` | ~2 GB | Good | Good |
| `medium` | ~5 GB | Real-time on RTX 3060+ | Great |
| `large-v3` | ~10 GB | Needs RTX 3090+ | Best |

## How It Works

1. **Audio capture**: Reads from PulseAudio's monitor source (captures whatever your speakers/headphones play)
2. **Transcription**: Feeds 3-second audio chunks to faster-whisper running on your local GPU
3. **AI layer**: When you ask a question, sends the rolling transcript to Claude's API for context-aware answers
4. **Overlay**: GTK3 window with notification type hint - stays on top, skips taskbar, draggable by title bar

## Cost

- **Transcription**: Free. Runs locally on your hardware.
- **AI Q&A**: ~$0.01-0.03 per question (Claude API). Only fires when you explicitly ask. A typical 1-hour meeting with 10 questions costs ~$0.20.

## Privacy

- Audio is processed locally by Whisper. It never hits any cloud API.
- Only the text transcript is sent to Claude's API when you ask a question.
- Transcripts are saved locally to `~/Documents/`.
- No telemetry, no analytics, no tracking.

## Screen Share Visibility

The overlay uses GTK's notification window type hint, which hides it from the taskbar and pager. On X11 (most Linux desktops), this may or may not hide it from screen sharing depending on how the screen-share app captures.

**Safe approach**: Use `Ctrl+Shift+H` to hide the overlay before sharing your screen.

## License

MIT - see [LICENSE](LICENSE).

## Credits

Built by [Griffin Cyber Solutions](https://griffincybersolutions.com).
