import argparse
import contextlib
import os
import platform
import plistlib
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from pathlib import Path

import toml

from makelove.config import all_love_versions
from makelove.util import parse_love_version


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "capability-project"
PROJECT_NAME = "CapabilityProject"
SMOKE_VERSION_FILE = "version.txt"
LEGACY_APPIMAGE_VERSIONS = {"11.3", "0.10.2", "0.9.2"}
DEFAULT_CACHE_HOME = REPO_ROOT / ".makelove-ci-cache"
LEGACY_MACOS_SMOKE_VERSIONS = {"0.9.1", "0.9.0"}

# App images fail because mpg123_info2 is not part of bundled libmpg123.so.0
AFFECTED_BY_MPG123_INFO2 = {"11.3", "0.10.2", "0.9.2"}


class Result(Enum):
    NOT_RUN = "not run"
    PASS = "pass"
    FAIL = "fail"


SUPPORTED_VERSIONS = {
    "win32": all_love_versions[: all_love_versions.index("0.6.1")],
    "win64": all_love_versions[: all_love_versions.index("0.7.2")],
    "macos": all_love_versions[: all_love_versions.index("0.6.1")],
    "appimage": [
        v
        for v in all_love_versions
        if tuple(parse_love_version(v)) >= (11, 4) or v in LEGACY_APPIMAGE_VERSIONS
    ],
    "lovejs": [v for v in all_love_versions if v.startswith("11.")],
}

RUNNER_TARGETS = {
    "Linux": ["win32", "win64", "macos", "appimage", "lovejs"],
    "macOS": ["win32", "win64", "macos", "lovejs"],
    "Windows": ["win32", "win64", "macos", "lovejs"],
}


@dataclass
class MatrixRow:
    target: str
    version: str
    supported: bool
    result: Result
    error: str = ""


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner-os", default=os.environ.get("RUNNER_OS", "Linux"))
    parser.add_argument("--target", choices=SUPPORTED_VERSIONS)
    parser.add_argument("--love-version")
    parser.add_argument("--list", action="store_true")
    return parser.parse_args()


def cases(runner_os, target=None, love_version=None):
    targets = [target] if target else RUNNER_TARGETS[runner_os]
    versions = [love_version] if love_version else all_love_versions
    for current_target in targets:
        for version in versions:
            yield current_target, version


def is_supported(target, love_version):
    return love_version in SUPPORTED_VERSIONS[target]


@contextlib.contextmanager
def github_log_group(title):
    print(f"::group::{title}", flush=True)
    try:
        yield
    finally:
        print("::endgroup::", flush=True)


def github_error(message):
    print(f"::error::{message}", flush=True)


def make_project(workdir, version, target):
    project = workdir / "project"
    shutil.copytree(FIXTURE, project)

    config_path = project / "makelove.toml"
    config = toml.load(config_path)
    config["love_version"] = version
    config["default_targets"] = [target]
    config["build_directory"] = "build"
    if target == "appimage":
        config["appimage"] = {"artifacts": ["appimage", "appdir"]}
    with config_path.open("w") as config_file:
        toml.dump(config, config_file)

    conf_path = project / "conf.lua"
    conf = conf_path.read_text()
    conf = conf.replace('t.version = "11.5"', f't.version = "{version}"')
    conf_path.write_text(conf)

    main_path = project / "main.lua"
    main_file = main_path.read_text()
    main_file = main_file.replace("__MAKELOVE_EXPECTED_VERSION__", version)
    main_path.write_text(main_file)
    return project


def run_makelove(project, target, version):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["XDG_CACHE_HOME"] = os.environ.get("MAKELOVE_CI_CACHE", str(DEFAULT_CACHE_HOME))
    env["APPIMAGE_EXTRACT_AND_RUN"] = "1"

    command = [
        sys.executable,
        "-m",
        "makelove",
        "--version-name",
        version,
        "--force",
        target,
    ]
    subprocess.run(command, cwd=project, env=env, check=True)


def assert_smoke_output(command, cwd, love_version):
    print(f"Smoke run: {command}", flush=True)
    env = os.environ.copy()
    env["MAKELOVE_CAPABILITY_SMOKE"] = "1"
    env["APPIMAGE_EXTRACT_AND_RUN"] = "1"
    env["SDL_AUDIODRIVER"] = "dummy"
    env["SDL_VIDEODRIVER"] = "dummy"

    version_path = Path(cwd) / SMOKE_VERSION_FILE
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        timeout=20,
    )
    smoke_version = version_path.read_text().strip() if version_path.exists() else ""
    detail = (
        f"returncode={result.returncode}\n"
        f"stdout={result.stdout!r}\n"
        f"stderr={result.stderr!r}\n"
        f"{SMOKE_VERSION_FILE}={smoke_version!r}"
    )
    assert result.returncode == 0, detail
    assert smoke_version == love_version, detail


def assert_love_file(path, love_version):
    assert path.is_file(), f"missing {path}"
    assert_love_archive(path, love_version)


def assert_love_archive(path_or_file, love_version):
    with zipfile.ZipFile(path_or_file) as love_zip:
        names = set(love_zip.namelist())
        assert {"main.lua", "conf.lua"} <= names
        conf = love_zip.read("conf.lua").decode()
        main_file = love_zip.read("main.lua").decode()
        assert f't.version = "{love_version}"' in conf
        assert f'io.open("{SMOKE_VERSION_FILE}", "w")' in main_file


def assert_win(project, target, love_version, runner_os):
    archive = project / "build" / love_version / target / f"{PROJECT_NAME}-{target}.zip"
    assert archive.is_file(), f"missing {archive}"
    with zipfile.ZipFile(archive) as output:
        names = set(output.namelist())
        exe_name = f"{PROJECT_NAME}.exe"
        assert exe_name in names
        assert "license.txt" in names
        exe = output.read(exe_name)
        assert b"main.lua" in exe
        assert b"conf.lua" in exe

        if can_run_windows_artifact(love_version, runner_os):
            with tempfile.TemporaryDirectory() as tmpdir:
                output.extractall(tmpdir)
                exe_path = Path(tmpdir) / exe_name
                assert_smoke_output([str(exe_path)], tmpdir, love_version)
        else:
            print(
                f"Smoke skip: {target} LOVE {love_version} on {runner_os}", flush=True
            )


def can_run_windows_artifact(love_version, runner_os):
    if runner_os != "Windows":
        return False
    # 0.7.1 has issues with headless (OpenGL not found)
    return love_version != "0.7.1"


def can_run_macos_artifact(love_version, runner_os):
    if runner_os != "macOS":
        return False
    if platform.machine() == "arm64":
        return tuple(parse_love_version(love_version)) >= (11, 4)
    return (
        tuple(parse_love_version(love_version)) >= (11, 4)
        or love_version in LEGACY_MACOS_SMOKE_VERSIONS
    )


def assert_macos(project, love_version, runner_os):
    archive = project / "build" / love_version / "macos" / f"{PROJECT_NAME}-macos.zip"
    assert archive.is_file(), f"missing {archive}"
    love_path = f"{PROJECT_NAME}.app/Contents/Resources/{PROJECT_NAME}.love"
    plist_path = f"{PROJECT_NAME}.app/Contents/Info.plist"
    exe_path = f"{PROJECT_NAME}.app/Contents/MacOS/love"
    with zipfile.ZipFile(archive) as output:
        names = set(output.namelist())
        assert love_path in names
        assert plist_path in names
        assert exe_path in names
        plist = plistlib.loads(output.read(plist_path))
        assert plist["CFBundleShortVersionString"] == love_version
        assert_love_archive(BytesIO(output.read(love_path)), love_version)

        if can_run_macos_artifact(love_version, runner_os):
            with tempfile.TemporaryDirectory() as tmpdir:
                output.extractall(tmpdir)
                executable = Path(tmpdir) / exe_path
                executable.chmod(executable.stat().st_mode | 0o111)
                assert_smoke_output([str(executable)], tmpdir, love_version)
        else:
            print(f"Smoke skip: macos LOVE {love_version} on {runner_os}", flush=True)


def assert_lovejs(project, love_version):
    archive = project / "build" / love_version / "lovejs" / f"{PROJECT_NAME}-lovejs.zip"
    assert archive.is_file(), f"missing {archive}"
    with zipfile.ZipFile(archive) as output:
        names = set(output.namelist())
        assert f"{PROJECT_NAME}/index.html" in names
        assert f"{PROJECT_NAME}/game.data" in names
        game_data = BytesIO(output.read(f"{PROJECT_NAME}/game.data"))
        assert_love_archive(game_data, love_version)


def assert_appimage(project, love_version, runner_os):
    target_dir = project / "build" / love_version / "appimage"
    appimage = target_dir / f"{PROJECT_NAME}.AppImage"
    appimage_name = PROJECT_NAME.replace(" ", "")
    appdir = target_dir / "AppDir"

    assert appimage.is_file(), f"missing {appimage}"
    assert os.access(appimage, os.X_OK), f"{appimage} is not executable"
    assert appdir.is_dir(), f"missing {appdir}"
    assert (appdir / f"{appimage_name}.desktop").is_file()
    executable_paths = [
        "bin/love",
        "usr/bin/wrapper-love",
    ]
    assert any((appdir / path).is_file() for path in executable_paths), (
        f"missing AppImage executable; expected one of {executable_paths}"
    )

    if runner_os == "Linux" and love_version not in AFFECTED_BY_MPG123_INFO2:
        assert_smoke_output([str(appimage)], target_dir, love_version)
    else:
        print(f"Smoke skip: appimage LOVE {love_version} on {runner_os}", flush=True)


def validate(project, target, love_version, runner_os):
    love_path = project / "build" / love_version / "love" / f"{PROJECT_NAME}.love"
    assert_love_file(love_path, love_version)

    if target in ["win32", "win64"]:
        assert_win(project, target, love_version, runner_os)
    elif target == "macos":
        assert_macos(project, love_version, runner_os)
    elif target == "appimage":
        assert_appimage(project, love_version, runner_os)
    elif target == "lovejs":
        assert_lovejs(project, love_version)


def run_case(target, love_version, runner_os):
    try:
        with tempfile.TemporaryDirectory(
            prefix=f"makelove-{target}-{love_version}-"
        ) as workdir:
            project = make_project(Path(workdir), love_version, target)
            run_makelove(project, target, love_version)
            validate(project, target, love_version, runner_os)
        return MatrixRow(target, love_version, True, Result.PASS)
    except Exception as exc:
        if isinstance(exc, subprocess.CalledProcessError):
            error = f"makelove exited {exc.returncode}"
        else:
            error = str(exc)
        return MatrixRow(target, love_version, True, Result.FAIL, error)


def print_matrix(rows):
    print("\nCompatibility matrix")
    print("target   version  supported  result       error")
    print("-------  -------  ---------  -----------  -----")
    for row in rows:
        print(
            "{target:<7}  {version:<7}  {supported:<9}  {result:<11}  {error}".format(
                target=row.target,
                version=row.version,
                supported="yes" if row.supported else "no",
                result=row.result.value,
                error=row.error,
            )
        )


def main():
    args = parse_args()
    selected_cases = list(cases(args.runner_os, args.target, args.love_version))
    if args.list:
        for target, love_version in selected_cases:
            supported = "yes" if is_supported(target, love_version) else "no"
            print(f"{args.runner_os}: {target} {love_version} supported={supported}")
        return

    rows = []
    for target, love_version in selected_cases:
        supported = is_supported(target, love_version)
        if not supported:
            rows.append(MatrixRow(target, love_version, False, Result.NOT_RUN))
            continue

        with github_log_group(f"{target} LOVE {love_version}"):
            row = run_case(target, love_version, args.runner_os)
        rows.append(row)
        if row.result == Result.FAIL:
            github_error(f"{target} LOVE {love_version}: {row.error}")

    print_matrix(rows)
    if any(row.result == Result.FAIL for row in rows):
        failed = sum(row.result == Result.FAIL for row in rows)
        print(f"\n{failed} supported capability build(s) failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
