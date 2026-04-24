[app]
title = 盲水印工具
package.name = watermark
package.domain = org.sijin
source.dir = .
source.include_exts = py,png,jpg,jpeg
version = 1.0

# 必须加上opencv-python，否则打包失败
requirements = python3,kivy==2.2.1,numpy,opencv-python,pillow

android.api = 33
android.ndk = 25b
android.sdk = 24
android.archs = arm64-v8a, armeabi-v7a

android.permissions = READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE
android.enable_androidx = True
android.allow_backup = True

# Windows 必须加这两行
android.sdk_path =
android.ndk_path =

[buildozer]
log_level = 2
warn_on_root = 0