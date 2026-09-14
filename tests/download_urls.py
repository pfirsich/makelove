from urllib.error import HTTPError
from urllib.request import Request, urlopen

from makelove.config import all_love_versions
from makelove.util import get_download_url

platform_versions = {
    "win32": all_love_versions[: all_love_versions.index("0.6.1")],
    "win64": all_love_versions[: all_love_versions.index("0.7.2")],
    "macos": all_love_versions[: all_love_versions.index("0.6.1")],
}

# Other platforms don't use this function
for platform in ["win32", "win64", "macos"]:
    for version in platform_versions[platform]:
        url = get_download_url(version, platform)
        assert platform[:3] in url
        try:
            resp = urlopen(Request(url, method="HEAD"))
            code = resp.status
        except HTTPError as exc:
            code = exc.code
        assert code == 200
        print(f"{platform} {version}: {url} => {code}")
