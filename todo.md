* For unversioned builds, if you make e.g. "appimage" and "win32" and then only "appimage", it will delete the old win32 build. That's weird because it's surprising, but good because you don't have mismatching builds floating around. How do I want to handle this?
* Reorder values in full config! (order by usefullness/likelihood of being set - actually introduce some sections)
* README
* test prebuild that builds asset list

* builtin hooks
* I don't like windows vs. win32/win64 and linux vs. appimage
* Take core functionality out into a library and wrap them in small cli tools, that come with makelove