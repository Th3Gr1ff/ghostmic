#!/usr/bin/env python3
"""
GhostMic - invisible meeting assistant for Linux.
Captures system audio, transcribes live, answers questions via Claude.

Hotkeys:
  Ctrl+Shift+H     Toggle overlay visibility
  Ctrl+Shift+N     Generate meeting notes
  Ctrl+Shift+Space  Focus input field
  Ctrl+Q           Quit
"""

import sys
import os
import threading
import signal
import argparse
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from audio import AudioCapture
from transcribe import Transcriber
from brain import Brain
from overlay import GhostOverlay


class GhostMic:
    def __init__(self, args):
        self.args = args
        self.audio = AudioCapture(sample_rate=16000, chunk_seconds=3)
        self.transcriber = Transcriber(
            model_size=args.model,
            device=args.device,
            compute_type=args.compute,
        )
        self.brain = Brain(api_key=args.api_key, model=args.llm)
        self.overlay = GhostOverlay(
            on_question=self._on_question,
            on_quit=self._quit,
        )
        self._running = False
        self._hotkey_listener = None

    def start(self):
        self._running = True

        # Load whisper model in background
        threading.Thread(target=self._load_model, daemon=True).start()

        # Start global hotkeys
        threading.Thread(target=self._start_hotkeys, daemon=True).start()

        # Show overlay
        self.overlay.show()

        # Run GTK main loop
        Gtk.main()

    def _load_model(self):
        self.overlay.set_status("loading whisper...")
        self.transcriber.load_model()
        device_label = self.transcriber.device.upper()
        self.overlay.set_status(f"starting audio ({device_label})...")

        self.audio.start()
        self.overlay.set_status(f"listening ({device_label})")

        threading.Thread(target=self._transcribe_loop, daemon=True).start()

    def _transcribe_loop(self):
        while self._running:
            chunk = self.audio.get_chunk(timeout=5.0)
            if chunk is None:
                continue

            text = self.transcriber.transcribe_chunk(chunk)
            if text:
                self.overlay.append_transcript(text)

    def _on_question(self, question):
        def _ask():
            transcript = self.transcriber.get_transcript()
            if not transcript.strip():
                self.overlay.set_ai_response("No transcript yet - waiting for audio.")
                return

            if question.lower() in ("recap", "summary", "notes"):
                self.overlay.set_ai_response("Generating notes...")
                notes = self.brain.auto_notes(transcript)
                self.overlay.set_ai_response(notes)
            else:
                self.brain.ask(
                    transcript, question,
                    callback=lambda text: self.overlay.set_ai_response(text),
                )

        threading.Thread(target=_ask, daemon=True).start()

    def _start_hotkeys(self):
        try:
            from pynput import keyboard

            def on_activate_toggle():
                GLib.idle_add(self.overlay.toggle_visible)

            def on_activate_notes():
                self._on_question("notes")

            def on_activate_focus():
                GLib.idle_add(self.overlay.focus_input)
                if not self.overlay.visible:
                    GLib.idle_add(self.overlay.toggle_visible)

            def on_activate_quit():
                GLib.idle_add(self._quit)

            hotkeys = keyboard.GlobalHotKeys({
                "<ctrl>+<shift>+h": on_activate_toggle,
                "<ctrl>+<shift>+n": on_activate_notes,
                "<ctrl>+<shift>+<space>": on_activate_focus,
                "<ctrl>+q": on_activate_quit,
            })
            self._hotkey_listener = hotkeys
            hotkeys.run()
        except Exception as e:
            print(f"Hotkey registration failed: {e}", file=sys.stderr)

    def _quit(self):
        self._running = False
        self.audio.stop()
        if self._hotkey_listener:
            self._hotkey_listener.stop()

        transcript = self.transcriber.get_transcript()
        if transcript.strip():
            save_path = os.path.expanduser(
                f"~/Documents/ghostmic_transcript_{_timestamp()}.txt"
            )
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, "w") as f:
                f.write(transcript)
            print(f"Transcript saved: {save_path}")

        Gtk.main_quit()


def _timestamp():
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def main():
    parser = argparse.ArgumentParser(description="GhostMic - invisible meeting assistant")
    parser.add_argument("--model", default="medium", help="Whisper model size (tiny/base/small/medium/large-v3)")
    parser.add_argument("--device", default="cuda", help="Whisper device (cuda/cpu)")
    parser.add_argument("--compute", default=None, help="Compute type (float16/int8/int8_float16)")
    parser.add_argument("--llm", default="claude-sonnet-4-20250514", help="Claude model for Q&A")
    parser.add_argument("--api-key", default=None, help="Anthropic API key (or set ANTHROPIC_API_KEY)")
    args = parser.parse_args()

    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))

    app = GhostMic(args)
    app.start()


if __name__ == "__main__":
    main()
