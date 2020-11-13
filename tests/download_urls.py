from urllib.request import Request, urlopen
from urllib.error import HTTPError

from makelove.util import get_download_url
from makelove.config import all_love_versions

platform_versions = {
    "win32": all_love_versions[: all_love_versions.index("0.6.1")],
    "win64": all_love_versions[: all_love_versions.index("0.7.2")],
    "macos": all_love_versions[: all_love_versions.index("0.6.1")],
}

# Other platforms don't use this function
for platform in ["win32", "win64", "macos"]:
    for version in platform_versions[platform]:
        url = get_download_url(version, platform)
        try:
            resp = urlopen(Request(url, method="HEAD"))
            code = resp.status
        except HTTPError as exc:
            code = exc.code
        print("{} {}: {}".format(platform, version, code))
