#!/usr/bin/env bash
set -euo pipefail

echo "=== GhostMic Installer (Linux Mint) ==="

# System deps
echo "[1/4] Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
    python3-venv python3-dev \
    libgirepository1.0-dev gir1.2-gtk-3.0 gir1.2-gdk-3.0 \
    libcairo2-dev pkg-config \
    portaudio19-dev \
    xdotool

# Python venv
echo "[2/4] Creating virtual environment..."
VENV_DIR="$HOME/.local/share/ghostmic/venv"
mkdir -p "$(dirname "$VENV_DIR")"
python3 -m venv "$VENV_DIR" --system-site-packages

echo "[3/4] Installing Python packages..."
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install -q \
    faster-whisper \
    anthropic \
    sounddevice \
    numpy \
    pynput

# Download whisper model
echo "[4/4] Pre-downloading Whisper medium model (CUDA)..."
"$VENV_DIR/bin/python" -c "
from faster_whisper import WhisperModel
print('Downloading whisper medium model...')
model = WhisperModel('medium', device='cuda', compute_type='float16')
print('Model ready.')
" 2>&1 || {
    echo "CUDA model failed, falling back to CPU..."
    "$VENV_DIR/bin/python" -c "
from faster_whisper import WhisperModel
print('Downloading whisper medium model (CPU)...')
model = WhisperModel('medium', device='cpu', compute_type='int8')
print('Model ready (CPU mode).')
"
}

# Create launcher
echo "Creating launcher..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cat > "$HOME/.local/bin/ghostmic" << LAUNCHER
#!/usr/bin/env bash
exec "$VENV_DIR/bin/python" "$SCRIPT_DIR/app.py" "\$@"
LAUNCHER
chmod +x "$HOME/.local/bin/ghostmic"

echo ""
echo "=== Done ==="
echo "Run with: ghostmic"
echo "Or: $VENV_DIR/bin/python $SCRIPT_DIR/app.py"
