[app]
title = QsTool
package.name = qstool
package.domain = org.qstool

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,csv,txt
source.include_patterns = assets/*,qstool/*
source.exclude_dirs = .git,.buildozer,bin,build,dist,__pycache__

version = 1.0.0
requirements = python3,kivy

orientation = portrait
fullscreen = 0

android.api = 34
android.minapi = 26
android.ndk = 26b
android.archs = arm64-v8a

android.accept_sdk_license = True
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE

p4a.bootstrap = sdl2
p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 1
