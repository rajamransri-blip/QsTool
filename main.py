import os
import threading
import time
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import StringProperty, ListProperty
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.utils import platform

from qstool.pak import PakReader, PakError


KV = r"""
<HomeScreen>:
    name: "home"
    BoxLayout:
        orientation: "vertical"
        padding: dp(20)
        spacing: dp(14)

        Label:
            text: "QsTool"
            font_size: "32sp"
            bold: True
            size_hint_y: None
            height: dp(60)

        Label:
            text: "Unreal PAK Tool (BGMI/PUBG)"
            color: 0.7, 0.7, 0.7, 1
            size_hint_y: None
            height: dp(35)

        Button:
            text: "Open PAK Unpacker"
            size_hint_y: None
            height: dp(55)
            on_release:
                root.manager.current = "unpack"

        Label:
            text: "Path: /storage/emulated/0/QsTool/"
            font_size: "13sp"
            color: 0.5, 0.8, 0.5, 1
            size_hint_y: None
            height: dp(40)


<UnpackScreen>:
    name: "unpack"
    BoxLayout:
        orientation: "vertical"
        padding: dp(14)
        spacing: dp(10)

        Label:
            text: "PAK Unpack Console"
            font_size: "22sp"
            bold: True
            size_hint_y: None
            height: dp(40)

        Spinner:
            id: pak_spinner
            text: "Choose PAK"
            values: root.pak_values
            size_hint_y: None
            height: dp(48)

        Button:
            text: "🔄 Scan / Refresh PAKs"
            size_hint_y: None
            height: dp(44)
            on_release:
                root.refresh()

        TextInput:
            id: target
            text: "ALL"
            hint_text: "Target filename or ALL"
            multiline: False
            size_hint_y: None
            height: dp(48)

        Button:
            text: "⚡ Start Unpacking"
            bold: True
            size_hint_y: None
            height: dp(50)
            on_release:
                root.start_unpack()

        Label:
            text: root.status
            size_hint_y: None
            height: dp(35)
            color: 1, 0.8, 0.2, 1

        TextInput:
            text: root.terminal
            readonly: True
            font_size: "12sp"

        Button:
            text: "Back to Home"
            size_hint_y: None
            height: dp(44)
            on_release:
                root.manager.current = "home"
"""


def storage_root():
    if platform == "android":
        return Path("/storage/emulated/0/QsTool")
    return Path.home() / "QsTool"


def make_dirs():
    root = storage_root()
    for folder in ("Original", "Editor", "Unpack", "Structure"):
        (root / folder).mkdir(parents=True, exist_ok=True)
    return root


class HomeScreen(Screen):
    pass


class UnpackScreen(Screen):
    pak_values = ListProperty([])
    status = StringProperty("Ready")
    terminal = StringProperty("")

    def on_pre_enter(self):
        make_dirs()
        self.refresh()

    def log(self, message):
        def update(_dt):
            self.terminal += message + "\n"
        Clock.schedule_once(update)

    def refresh(self):
        root = make_dirs()
        original = root / "Original"
        files = sorted(
            p.name
            for p in original.iterdir()
            if p.is_file() and p.suffix.lower() == ".pak"
        )
        self.pak_values = files
        self.ids.pak_spinner.values = files

        if files:
            self.ids.pak_spinner.text = files[0]
            self.status = f"{len(files)} PAK(s) found in Original/"
        else:
            self.ids.pak_spinner.text = "Choose PAK"
            self.status = "Copy .pak to /sdcard/QsTool/Original/"

    def start_unpack(self):
        pak_name = self.ids.pak_spinner.text.strip()
        target = self.ids.target.text.strip()

        if not pak_name or pak_name == "Choose PAK":
            self.status = "Error: Please select a PAK file"
            return

        if not target:
            self.status = "Error: Specify file or ALL"
            return

        root = make_dirs()
        pak_path = root / "Original" / pak_name
        self.terminal = ""
        self.status = "Unpacking started..."

        thread = threading.Thread(
            target=self.worker,
            args=(pak_path, root / "Unpack", root / "Structure", target),
            daemon=True,
        )
        thread.start()

    def worker(self, pak_path, unpack_dir, structure_dir, target):
        started = time.perf_counter()
        try:
            self.log(f"Loading: {pak_path.name}")
            reader = PakReader(pak_path)
            reader.open()

            self.log(f"PAK Version: {reader.version}")
            self.log(f"Total Entries: {len(reader.entries):,}")

            if reader.encrypted_index:
                raise PakError("Encrypted PAK index. Authorized AES key needed.")

            wanted = []
            target_norm = target.replace("\\", "/").strip("/").lower()

            if target.upper() == "ALL":
                wanted = list(reader.entries.values())
            else:
                for entry in reader.entries.values():
                    if Path(entry.path).name.lower() == target_norm:
                        wanted.append(entry)

            if not wanted:
                raise PakError("Target file not found in archive.")

            self.log(f"Extracting: {len(wanted)} files...")
            total_bytes = 0

            for idx, entry in enumerate(wanted, 1):
                clean_subpath = entry.path.lstrip("/\\")
                output = unpack_dir / clean_subpath
                output.parent.mkdir(parents=True, exist_ok=True)

                data = reader.read_entry(entry)
                output.write_bytes(data)

                total_bytes += len(data)
                if idx % 50 == 0 or idx == len(wanted):
                    self.log(f"[{idx}/{len(wanted)}] {clean_subpath} ({len(data):,} B)")

            # Write Structure manifest
            report = structure_dir / f"{pak_path.stem}_structure.txt"
            with report.open("w", encoding="utf-8") as fp:
                for entry in reader.entries.values():
                    fp.write(f"{entry.path}\t{entry.uncompressed_size}\t{entry.compression}\n")

            elapsed = time.perf_counter() - started
            self.log(f"Done! Extracted {total_bytes:,} bytes in {elapsed:.2f}s")
            Clock.schedule_once(lambda dt: setattr(self, "status", "Extraction Completed!"))

        except Exception as exc:
            self.log(f"ERROR: {str(exc)}")
            Clock.schedule_once(lambda dt: setattr(self, "status", "Failed - Check Logs"))


class QsToolApp(App):
    def build(self):
        self.request_android_permissions()
        make_dirs()
        Builder.load_string(KV)
        sm = ScreenManager()
        sm.add_widget(HomeScreen(name="home"))
        sm.add_widget(UnpackScreen(name="unpack"))
        return sm

    def request_android_permissions(self):
        if platform == "android":
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
            ])


if __name__ == "__main__":
    QsToolApp().run()
