* Resumable builds: allow building a different target for the same version and don't rebuild .love if already present
* makelove --init. Asks for:
    - name
    - (default_targets = all on linux, win on win)
    - build_directory (default will be shown)
    - (love_files will be mentioned at the end and default values will be genrated)
* Reorder values in full config! (order by usefullness/likelihood of being set - actually introduce some sections)
* README
* test prebuild that builds asset list

* builtin hooks
* I don't like windows vs. win32/win64 and linux vs. appimage
* Take core functionality out into a library and wrap them in small cli tools, that come with makelove