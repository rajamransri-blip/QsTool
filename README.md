# QsTool Pro — Unreal Engine PAK Archive Manager

A fast, lightweight, and modern dark-themed Android utility application built using **Python**, **Kivy**, and **python-for-android**. It enables reading, inspecting, and extracting Unreal Engine `.pak` archive files directly on Android devices without requiring a PC.

---

## Key Features

* **Full PAK Extraction & Single Asset Unpack:** Extract the full contents of an archive or target a specific file name inside the package.
* **Native Compression Support:** Built-in decoding for **Zlib** and **Gzip** compressed data blocks.
* **Modern OLED / Dark UI:** Responsive layout with high-contrast elements, real-time terminal output, and clear status banners.
* **Android 11–14+ Ready:** Built-in `MANAGE_ALL_FILES_ACCESS_PERMISSION` request flow to bypass modern Scoped Storage restrictions.
* **Structure Manifest Output:** Automatically outputs an inventory log (`[archive]_structure.txt`) detailing internal paths, sizes, and compression types.
* **Automated CI/CD Builds:** Pre-configured GitHub Actions workflow compiling 64-bit (`arm64-v8a`) debug APKs via Buildozer.

---

## Directory Structure on Device

When launched, the app automatically creates its working workspace inside your device's internal storage:

```text
/storage/emulated/0/QsTool/
├── Original/       <-- Place your input .pak archives here
├── Unpack/         <-- Extracted files are saved here
├── Structure/      <-- Archive manifest reports (.txt) are saved here
└── Editor/         <-- Staging folder for modded files
