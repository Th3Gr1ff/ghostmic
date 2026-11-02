import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib, Pango
import subprocess


CSS = b"""
#ghostmic-window {
    background-color: rgba(18, 18, 24, 0.92);
    border-radius: 12px;
}
#title-bar {
    background-color: rgba(30, 30, 42, 0.95);
    border-radius: 12px 12px 0 0;
    padding: 6px 12px;
}
#title-label {
    color: #8888aa;
    font-size: 11px;
    font-weight: bold;
    font-family: monospace;
}
#status-label {
    color: #44dd66;
    font-size: 11px;
    font-family: monospace;
}
#transcript-view {
    background-color: transparent;
    color: #ccccdd;
    font-family: monospace;
    font-size: 12px;
    padding: 8px;
}
#transcript-view text {
    background-color: transparent;
    color: #ccccdd;
}
#ai-response {
    background-color: rgba(40, 40, 60, 0.9);
    color: #aaddff;
    font-family: monospace;
    font-size: 12px;
    padding: 8px;
    border-radius: 0 0 6px 6px;
}
#ai-response text {
    background-color: transparent;
    color: #aaddff;
}
#input-entry {
    background-color: rgba(50, 50, 70, 0.9);
    color: #ffffff;
    font-family: monospace;
    font-size: 12px;
    padding: 6px 8px;
    border: none;
    border-radius: 6px;
    caret-color: #aaddff;
}
#mode-label {
    color: #666688;
    font-size: 10px;
    font-family: monospace;
}
"""


class GhostOverlay:
    def __init__(self, on_question=None, on_quit=None):
        self.on_question = on_question
        self.on_quit = on_quit
        self.visible = True
        self._drag_start = None

        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        self.window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        self.window.set_name("ghostmic-window")
        self.window.set_title("GhostMic")
        self.window.set_default_size(420, 550)
        self.window.set_decorated(False)
        self.window.set_resizable(True)
        self.window.set_keep_above(True)
        self.window.set_skip_taskbar_hint(True)
        self.window.set_skip_pager_hint(True)
        self.window.set_app_paintable(True)
        self.window.set_type_hint(Gdk.WindowTypeHint.NOTIFICATION)

        screen = self.window.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.window.set_visual(visual)

        self.window.connect("delete-event", self._on_delete)
        self.window.connect("button-press-event", self._on_button_press)
        self.window.connect("motion-notify-event", self._on_motion)
        self.window.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.POINTER_MOTION_MASK
        )

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.window.add(vbox)

        # Title bar
        title_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title_bar.set_name("title-bar")

        title_label = Gtk.Label(label="GHOSTMIC")
        title_label.set_name("title-label")
        title_bar.pack_start(title_label, False, False, 0)

        self.status_label = Gtk.Label(label="loading model...")
        self.status_label.set_name("status-label")
        title_bar.pack_end(self.status_label, False, False, 0)

        vbox.pack_start(title_bar, False, False, 0)

        # Transcript area
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(200)
        scroll.set_vexpand(True)

        self.transcript_view = Gtk.TextView()
        self.transcript_view.set_name("transcript-view")
        self.transcript_view.set_editable(False)
        self.transcript_view.set_cursor_visible(False)
        self.transcript_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.transcript_buf = self.transcript_view.get_buffer()
        scroll.add(self.transcript_view)
        vbox.pack_start(scroll, True, True, 0)

        # AI response area
        ai_scroll = Gtk.ScrolledWindow()
        ai_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        ai_scroll.set_min_content_height(80)
        ai_scroll.set_max_content_height(180)

        self.ai_view = Gtk.TextView()
        self.ai_view.set_name("ai-response")
        self.ai_view.set_editable(False)
        self.ai_view.set_cursor_visible(False)
        self.ai_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.ai_buf = self.ai_view.get_buffer()
        self.ai_buf.set_text("Press Ctrl+Enter to ask a question")
        ai_scroll.add(self.ai_view)
        vbox.pack_start(ai_scroll, False, True, 0)

        # Input area
        input_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        input_box.set_margin_start(8)
        input_box.set_margin_end(8)
        input_box.set_margin_top(4)
        input_box.set_margin_bottom(8)

        self.input_entry = Gtk.Entry()
        self.input_entry.set_name("input-entry")
        self.input_entry.set_placeholder_text("Ask about the meeting... (Enter to send)")
        self.input_entry.connect("activate", self._on_input_activate)
        input_box.pack_start(self.input_entry, True, True, 0)
        vbox.pack_start(input_box, False, False, 0)

        # Status line
        mode_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        mode_box.set_margin_start(8)
        mode_box.set_margin_bottom(4)
        self.mode_label = Gtk.Label(
            label="Ctrl+Shift+H: hide  |  Ctrl+Shift+N: notes  |  Ctrl+Q: quit"
        )
        self.mode_label.set_name("mode-label")
        mode_box.pack_start(self.mode_label, False, False, 0)
        vbox.pack_start(mode_box, False, False, 0)

        # Position bottom-right
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        geom = monitor.get_geometry()
        self.window.move(geom.x + geom.width - 440, geom.y + 60)

    def show(self):
        self.window.show_all()

    def toggle_visible(self):
        if self.visible:
            self.window.hide()
            self.visible = False
        else:
            self.window.show_all()
            self.visible = True

    def set_status(self, text):
        GLib.idle_add(self.status_label.set_text, text)

    def append_transcript(self, text):
        def _do():
            end = self.transcript_buf.get_end_iter()
            if self.transcript_buf.get_char_count() > 0:
                self.transcript_buf.insert(end, "\n")
                end = self.transcript_buf.get_end_iter()
            self.transcript_buf.insert(end, text)
            # Auto-scroll
            mark = self.transcript_buf.get_insert()
            self.transcript_view.scroll_mark_onscreen(mark)
            adj = self.transcript_view.get_parent().get_vadjustment()
            adj.set_value(adj.get_upper() - adj.get_page_size())
        GLib.idle_add(_do)

    def set_ai_response(self, text):
        GLib.idle_add(self.ai_buf.set_text, text)

    def focus_input(self):
        GLib.idle_add(self.input_entry.grab_focus)

    def _on_input_activate(self, entry):
        question = entry.get_text().strip()
        if question and self.on_question:
            entry.set_text("")
            self.set_ai_response("Thinking...")
            self.on_question(question)

    def _on_delete(self, *args):
        if self.on_quit:
            self.on_quit()
        return True

    def _on_button_press(self, widget, event):
        if event.button == 1 and event.y < 35:
            self.window.begin_move_drag(
                event.button, int(event.x_root), int(event.y_root), event.time
            )

    def _on_motion(self, widget, event):
        pass
