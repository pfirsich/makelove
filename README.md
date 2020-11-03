# makelove

A packaging tool for [löve](https://love2d.org) games

**This tool is pretty early in development and may be buggy. Please do not expect it to work super well and contact me if you notice anything going wrong!**

## Features
* Build fused win32 and win64 löve binaries (including handling of .exe metadata and icon, but only on Windows or with Wine!)
* Build [AppImages](https://appimage.org/) using the AppImages from [love-appimages](https://github.com/pfirsich/love-appimages) (This is feature is only supported on Linux and WSL2. WSL does not support AppImages for a lack of FUSE support)
* Mac Builds
* [love.js](https://github.com/Davidobot/love.js) builds (which does not support Lua modules from shared libraries or LuaJIT-specific features, like FFI)
* Proper handling of shared libraries (both Lua modules and FFI)!
* Packaging of those binaries in archives, including extra files
* Versioned builds
* Control and customization along the way:
    - Configure which targets to build
    - Which files to include in the .love with a list of include/exclude patterns
    - Which löve binaries or AppImage to use as the base
    - Which artifacts to generate or keep
    - pre- and postbuild hooks that are able to change the configuration on the fly. For example you can decide dynamically which files to include in the .love (e.g. through parsing asset lists), inject build metadata or just to upload your build automatically afterwards (e.g. via butler to [itch.io](https://itch.io)))

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

*NOTE: Please have a look at [makelove_full.toml](makelove_full.toml) for a reference of the possible configuration parameters*

It is also possible to execute makelove without any configuration file (makelove will try to guess every configuration parameter), but `makelove --init` does not take long to execute and will probably give you way better results.

If you want to do unversioned builds, it's simply enough to invoke makelove:

```
makelove
```

If you wish to version your builds, you should pass a version the first time you build:

```
makelove --version-name 0.1
```

For all subsequent builds the version number will simply be bumped unless you specify a version explicitly and an invocation of makelove without arguments is enough.

There are a number of arguments you can specify to customize the build (e.g. to specify a configuration file explicitly, disable hooks, produce more verbose output or check the config file), so make sure to have a look at the help text of makelove:

```
makelove --help
```

## Configuration

All possible configuration values are shown and explained in [makelove_full.toml](makelove_full.toml) (**You should look at this!**) (not a valid makelove configuration).

If you wish to do some extravagant things, have a look at [how_to_x.md](how_to_x.md), which may list what you are trying to do. If there is anything that you want to do, but can't please let me know and I will try to add whatever is needed, if the change is reasonable.

## Versioned & Unversioned Builds

### Unversioned Builds

With unversioned builds there is only one build directory (the one specified in `build_directory`) and in that directory exists a subdirectory for each target.

Whenever a target is built again, the love file will be rebuilt (unless `--resume` is passed) and the target will be overwritten.

### Versioned

For versioned builds on the other hand a new directory (with the version name) is created for each build (the old ones are kept).

You can also build a version + target pair that was already built. If you attempt to rebuild a target, makelove will error, unless you specify `--force`, which will overwrite that target instead. The löve file will not be rebuilt (even with `--force`) as it defines the version itself. If you wish to replace the löve file, you can just delete the version directory and rebuild the version completely.

If a versioned built has been made, a build log is created/updated (in `build_directory/.makelove-buildlog`) that contains a history of the builds (targets built, timestamp, success).

## GitHub Actions
You can find an example YAML file that will run makelove in a GitHub Action here:
[build.yml](https://github.com/pfirsich/lovejam20/blob/349f645ec65db9563b1c58f176f0207051294875/.github/workflows/build.yml).

Since Linux is the only platform that can make builds for every platform, an Action might be useful to get those, even if you do not have a Linux machine easily at your disposal.

The file does need some adaptions in regards to where makelove should be executed and the build directory, but otherwise it should be fairly copy-pastable. **Do read the comments in that file first though!** Also note that this is not meant for versioned builds, since those need an extra manual input (the version). In case you need them, consider taking the version from a file in the repository.

## Hooks

Hooks are simply commands that are executed at specific points in the build. After all preparations are done and before the first filesystem operations are executed, the prebuild hook is executed. The postbuild hook is executed after every other step of the build is done.

The configuration as it is currently will be written to a temporary file, which will also be read back after the hook was executed. Through this mechanism hooks are capable of modifying the configuration.

The commands will be executed with additional environment variables:

| Environment variable | Description |
|--------------------------|-------------------------------------------------------------------------------------------------------------------------------|
| MAKELOVE_TEMP_CONFIG | The path to the temporary configuration file |
| MAKELOVE_VERSION | The version being built. Also in the command `{version}` is being replaced with this. An empty string for unversioned builds. |
| MAKELOVE_TARGETS | The targets being built. |
| MAKELOVE_BUILD_DIRECTORY | The build directory. For versioned builds this is the version's build directory. In the command `{build_directory}` is being replaced with this. |

An example of how to use the parameter replacement in the commands is in [makelove_full.toml](makelove_full.toml).
