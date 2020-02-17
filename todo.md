* README
* Figure out what to keep and how to control it: game directory, squash-fs AppDir, archive_temp (vs. archive) - "artifacts" config var? (list of directory, archive) - rename "archive?"
    - have new set of targets: appdir, appimage, game_directory, love, win32_directory, win32, win64_directory, win64 - which have a fixed dependency graph and will be built, if necessary, but deleted if not explicitely built
    - introduce appimage.keep_appdir, appimage.build_appimage, keep_gamedirectory, win32.keep_directory, build_archive
    - introduce a new parameter for all targets: artifacts, which is a list of things to build. for appimage: [appimage, appdir], for windows [directory, zip], for mac [app, zip] + keep_game_directory
    - introduce "archive_files" for each target and if you specify it a zip will be built with those extra files. this does not solve appimage/appdir
* test prebuild that builds asset list
* I don't like windows vs. win32/win64 and linux vs. appimage
* Reorder values in full config! (order by usefullness/likelihood of being set - actually introduce some sections)
* makelove --init. Asks for:
    - name
    - (default_targets = all on linux, win on win)
    - build_directory (default will be shown)
    - (love_files will be mentioned at the end and default values will be genrated)
* builtin hooks
* Take core functionality out into a library and wrap them in small cli tools, that come with makelove