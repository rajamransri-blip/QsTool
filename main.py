__version__ = "1.0.0"

import csv
import threading
import time
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.screenmanager import ScreenManager, Screen

from qstool.pak import PakReader, PakError


KV = r'''
ScreenManager:
    HomeScreen:
    UnpackScreen:

<HomeScreen>:
    name: "home"

    BoxLayout:
        orientation: "vertical"
        padding: dp(18)
        spacing: dp(12)

        Label:
            text: "QsTool"
            font_size: "30sp"
            bold: True
            size_hint_y: None
            height: dp(55)

        Label:
            text: "PAK Unpack / Structure Tool"
            size_hint_y: None
            height: dp(35)

        Button:
            text: "Unpack"
            size_hint_y: None
            height: dp(55)
            on_release:
                root.manager.current = "unpack"

        Label:
            text: "Storage: /storage/emulated/0/QsTool/"
            size_hint_y: None
            height: dp(40)

<UnpackScreen>:
    name: "unpack"

    BoxLayout:
        orientation: "vertical"
        padding: dp(12)
        spacing: dp(8)

        Label:
            text: "PAK Unpack"
            font_size: "24sp"
            bold: True
            size_hint_y: None
            height: dp(42)

        Spinner:
            id: pak_spinner
            text: "Choose PAK"
            values: root.pak_values
            size_hint_y: None
            height: dp(48)

        Button:
            text: "Detect / Refresh PAK"
            size_hint_y: None
            height: dp(44)
            on_release:
                root.refresh()

        TextInput:
            id: target
            hint_text: "Target file name or ALL"
            multiline: False
            size_hint_y: None
            height: dp(48)

        Button:
            text: "Unpacking Options"
            size_hint_y: None
            height: dp(52)
            on_release:
                root.start_unpack()

        Label:
            text: root.status
            text_size: self.width, None
            halign: "left"
            valign: "top"

        TextInput:
            text: root.terminal
            readonly: True
            size_hint_y: 1

        Button:
            text: "Back"
            size_hint_y: None
            height: dp(44)
            on_release:
                root.manager.current = "home"
'''


def storage_root():
    android_storage = Path("/storage/emulated/0")

    if android_storage.exists():
        return android_storage / "QsTool"

    return Path.home() / "QsTool"


def ensure_dirs():
    root = storage_root()

    for name in (
        "Original",
        "Editor",
        "Unpack",
        "Structure",
    ):
        (root / name).mkdir(
            parents=True,
            exist_ok=True
        )

    return root


class HomeScreen(Screen):
    pass


class UnpackScreen(Screen):

    pak_values = []
    status = StringProperty("")
    terminal = StringProperty("")

    def on_pre_enter(self):
        ensure_dirs()
        self.refresh()

    def log(self, text):
        def update(_dt):
            self.terminal += text + "\n"

        Clock.schedule_once(update)

    def refresh(self):
        root = ensure_dirs()

        original = root / "Original"

        files = sorted(
            [
                p.name
                for p in original.iterdir()
                if p.is_file()
                and p.suffix.lower() == ".pak"
            ]
        )

        self.pak_values = files
        self.ids.pak_spinner.values = files

        if files:
            self.ids.pak_spinner.text = files[0]
            self.status = (
                f"Detected {len(files)} PAK file(s)"
            )
        else:
            self.ids.pak_spinner.text = "Choose PAK"
            self.status = (
                "Put .pak files into:\n"
                f"{original}"
            )

    def start_unpack(self):
        pak_name = self.ids.pak_spinner.text.strip()
        target = self.ids.target.text.strip()

        if (
            not pak_name
            or pak_name == "Choose PAK"
        ):
            self.status = "Choose a PAK first."
            return

        if not target:
            self.status = (
                "Enter target filename or ALL."
            )
            return

        root = ensure_dirs()

        pak_path = (
            root
            / "Original"
            / pak_name
        )

        unpack_dir = root / "Unpack"
        structure_dir = root / "Structure"

        self.terminal = ""
        self.status = "Starting..."

        threading.Thread(
            target=self.worker,
            args=(
                pak_path,
                unpack_dir,
                structure_dir,
                target,
            ),
            daemon=True,
        ).start()

    def worker(
        self,
        pak_path,
        unpack_dir,
        structure_dir,
        target,
    ):
        started = time.perf_counter()

        try:
            self.log(
                f"PAK: {pak_path.name}"
            )

            self.log(
                f"Target: {target}"
            )

            self.log(
                "Reading PAK index..."
            )

            reader = PakReader(
                pak_path
            )

            reader.open()

            self.log(
                f"Version: {reader.version}"
            )

            self.log(
                f"Entries: {len(reader.entries):,}"
            )

            self.log(
                f"Encrypted index: "
                f"{reader.encrypted_index}"
            )

            if reader.encrypted_index:
                raise PakError(
                    "Encrypted PAK index. "
                    "An authorized key is required."
                )

            wanted = []

            target_norm = (
                target
                .replace("\\", "/")
                .strip("/")
                .lower()
            )

            if target.upper() == "ALL":
                wanted = list(
                    reader.entries.values()
                )

            else:
                for entry in (
                    reader.entries.values()
                ):
                    filename = (
                        Path(entry.path)
                        .name
                        .lower()
                    )

                    if filename == target_norm:
                        wanted.append(entry)

                if not wanted:
                    for entry in (
                        reader.entries.values()
                    ):
                        if (
                            entry.path.lower()
                            == target_norm
                        ):
                            wanted.append(entry)

            if not wanted:
                raise PakError(
                    "Target file not found "
                    "in PAK index."
                )

            self.log(
                f"Matched: {len(wanted):,}"
            )

            total_bytes = 0

            for index, entry in enumerate(
                wanted,
                start=1,
            ):
                output = (
                    unpack_dir
                    / Path(entry.path)
                )

                output.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                one_started = (
                    time.perf_counter()
                )

                data = (
                    reader.read_entry(entry)
                )

                output.write_bytes(data)

                size = len(data)

                total_bytes += size

                elapsed = (
                    time.perf_counter()
                    - one_started
                )

                self.log(
                    f"[{index}/"
                    f"{len(wanted)}] "
                    f"{entry.path} | "
                    f"{size:,} bytes | "
                    f"{elapsed:.2f}s"
                )

            report = (
                structure_dir
                / f"{pak_path.stem}"
                "_structure.txt"
            )

            with report.open(
                "w",
                encoding="utf-8",
            ) as fp:

                for entry in (
                    reader.entries.values()
                ):
                    fp.write(
                        f"{entry.path}\t"
                        f"{entry.uncompressed_size}\t"
                        f"{entry.compression}\n"
                    )

            total_time = (
                time.perf_counter()
                - started
            )

            self.log(
                f"Total: "
                f"{total_bytes:,} bytes"
            )

            self.log(
                f"Time: "
                f"{total_time:.2f}s"
            )

            Clock.schedule_once(
                lambda dt: setattr(
                    self,
                    "status",
                    "Unpacking completed.",
                )
            )

        except Exception as exc:
            self.log(
                "ERROR: "
                + str(exc)
            )

            Clock.schedule_once(
                lambda dt: setattr(
                    self,
                    "status",
                    "Unpacking failed. "
                    "See terminal.",
                )
            )


class QsToolApp(App):

    def build(self):
        ensure_dirs()

        Builder.load_string(KV)

        return ScreenManager()


if __name__ == "__main__":
    QsToolApp().run()
