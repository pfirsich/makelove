# makelove

A packaging tool for [löve](https://love2d.org) games

## Features
* Build fused win32 and win64 löve binaries with effortless setting of .exe metadata (including the icon)
* Build [AppImage](https://appimage.org/)s using the AppImages from [love-appimages](pfirsich/love-appimages) (this implies support for löve 0.10 and 0.9!)
* Proper handling of shared libraries (both Lua modules and FFI)!
* Packaging of those binaries in archives, including extra files
* Versioned builds
* Control and customization along the way:
    - Configure which targets to build
    - Which files to include in the .love or the archive with a list of include/exclude patterns
    - Which löve binaries or AppImage to use as the base
    - Which artifacts to generate/keep
    - pre- and postbuild hooks that are able to change the configuration on the fly. For example you can decide dynamically which files to include in the .love (e.g. through parsing asset lists), inject build metadata or just to upload your build automatically afterwards (e.g. via butler to [itch.io](https://itch.io)))

## Quickstart

To use makelove you need to install Python 3.7 or later and then execute:
```
pip3 install makelove
```

Then navigate to the directory containing the `main.lua` of your game (your game directory) and execute:
```
makelove --init
```
and enter the values you are prompted for. This will create a makelove.toml in your working directory.

It is also possible to execute makelove without any configuration file (makelove will try to guess every configuration parameter), but `makelove --init` does not take long to execute and will probably give you way better results.

Then just invoke makelove to do the build:
```
makelove
```
And other parameters are optional

// add auto-bump?

// link makelove_full.toml
// more examples
// paste helptext?