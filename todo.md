* Add -y option that just answers "yes" whenever a prompt asks a question, so makelove can be used for automation more easily.
* Option to specify source directory
  It should not behave any different than cd-ing into the source directory and passing the makelove config explicitly via --config.
* Warn louder if patterns don't match anything? With some hints on how to fix? (i.e. "main.lua" instead of "./main.lua")
* git tag versions (could be postbuild) -> re builtin hooks?
* Cache löve appimages
* print "included by" and "excluded by" in file list?
* dont walk the whole tree in FileList, but use the patterns while walking to filter
* builtin hooks?
* I don't like windows vs. win32/win64 and linux vs. appimage
* Take core functionality out into a library and wrap them in small cli tools, that come with makelove
