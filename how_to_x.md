# How do I do X?
Please keep in mind that many things in here could be considered hacks of my own software. I did think about these scenarios though and then decided that they are uncommon enough to not put in extra logic in the application itself and therefore potentially complicate configuration or implementation for the way more common cases.

I took great care in making sure that everything I could make up that anyone could reasonably want to do can be done with makelove, even if it's through one of these hacks.

Not everything in here is tested, but the ideas should be sound. If something is incorrect, let me know!

## Mount `getSourceBaseDirectory()` and store assets next to the .exe
If you just build Windows, just only include the `*.lua` files in `love_files` and all the media in `archive_files`.
I you build appimages too, i.e. you need different .love files for different targets, then you have to simply use different configuration files!
I recommend putting the shared configuration into a separate file and then `cat` it together with your specific configuration before you execute `makelove`. I consciously chose TOML because you can concatenate configurations!

## Execute a build in multiple steps (with different targets)
E.g. you want to execute `makelove win32 win64` on your windows machine, then switch to Linux and execute `makelove appimage` and for some reason Wine does not work for you, so you have to do it that way.

I call this "resumable" builds.

If you don't use versioned builds and no postbuild/prebuild hooks, you don't have to do anything, except pass `--resume` for each invocation of `makelove` after the first.

If you don't use hooks, but versioned builds, just build each target individually and pass the same version each time.

Otherwise just build the first target without a postbuild hook:

```bash
makelove -d postbuild -v 1.2.3 win32 win64
```

Then build all subsequent targets without any hooks:
```
makelove -d all -v 1.2.3 mac (--resume)
```
Optionally pass `--resume` for unversioned builds.

And finally build without prebuild, but with postbuild
```
makelove -d prebuild -v 1.2.3 appimage (--resume)
```
