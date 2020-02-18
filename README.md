# makelove

A packaging tool for [löve](https://love2d.org) games

## Features
* Build fused win32 and win64 löve binaries (including handling of .exe metadata and icon, but only on Windows or with Wine!)
* Build [AppImages](https://appimage.org/) using the AppImages from [love-appimages](pfirsich/love-appimages) (This is feature is only supported on Linux and WSL2. WSL does not support AppImages for a lack of FUSE support)
* Proper handling of shared libraries (both Lua modules and FFI)!
* Packaging of those binaries in archives, including extra files
* Versioned builds
* Control and customization along the way:
    - Configure which targets to build
    - Which files to include in the .love or the archive with a list of include/exclude patterns
    - Which löve binaries or AppImage to use as the base
    - Which artifacts to generate or keep
    - pre- and postbuild hooks that are able to change the configuration on the fly. For example you can decide dynamically which files to include in the .love (e.g. through parsing asset lists), inject build metadata or just to upload your build automatically afterwards (e.g. via butler to [itch.io](https://itch.io)))

### Planned

- Mac build support (**help needed**, since I do not have a Mac to test on)

## Quickstart

To use makelove you need to install Python 3.7 or later and then execute (probably just `pip` on Windows):

```
pip3 install makelove
```

Then navigate to the directory containing the `main.lua` of your game (your game directory) and execute:

```
makelove --init
```

and enter the values you are prompted for. This will create a makelove.toml in your working directory.

It is also possible to execute makelove without any configuration file (makelove will try to guess every configuration parameter), but `makelove --init` does not take long to execute and will probably give you way better results.

If you want to do unversioned builds, it's simply enough to invoke makelove:

```
makelove
```

If you wish to version your builds, you should pass a version the first time you build:

```
makelove --version 0.1
```

For all subsequent builds the version number will simply be bumped unless you specify a version explicitely and an invocation of makelove without arguments is enough.

There are a number of arguments you can specify to customize the build (e.g. to specify a configuration file explicitely, disable hooks, produce more verbose output or check the config file), so make sure to have a look at the help text of makelove:

```
makelove --help
```

## Configuration

All possible configuration values are shown and explained in [makelove_full.toml](makelove_full.toml) (not a valid makelove configuration).

Hooks are capable of rewriting the config for a build. For more information on configuring hooks, see [hooks.md](hooks.md) (coming soon!)
