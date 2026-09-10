[app]

title = QsTool
package.name = qstool
package.domain = org.qstool

source.dir = .

source.include_exts = py,csv,kv,txt,md

source.include_patterns = assets/*,qstool/*

source.exclude_dirs = bin,.buildozer,__pycache__,.git

version = 1.0.0

requirements = python3,kivy

orientation = portrait

fullscreen = 0

android.api = 35
android.minapi = 24
android.ndk = 28c

android.archs = arm64-v8a

android.accept_sdk_license = True

android.permissions = READ_MEDIA_IMAGES,READ_MEDIA_VIDEO,READ_MEDIA_AUDIO

android.allow_backup = False

android.release_artifact = apk

p4a.bootstrap = sdl2

[buildozer]

log_level = 2
warn_on_root = 0
