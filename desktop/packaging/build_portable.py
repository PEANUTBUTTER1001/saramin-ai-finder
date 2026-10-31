"""Build a no-installer Windows folder with 실행.bat and private Python.

Run on Windows x64 with any Python 3.9+ that has pip, and internet access.
Packages are fetched as Python 3.12 win_amd64 wheels to match the bundled
runtime. The target machine needs no Python or pip installation.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

DESKTOP = Path(__file__).resolve().parents[1]
ROOT = DESKTOP.parent
DIST_ROOT = DESKTOP / "dist"
OUTPUT = DIST_ROOT / "SaraminFinder"
CACHE = DESKTOP / ".cache"
PYTHON_VERSION = "3.12.10"
EMBED_NAME = f"python-{PYTHON_VERSION}-embed-amd64.zip"
EMBED_URL = f"https://www.python.org/ftp/python/{PYTHON_VERSION}/{EMBED_NAME}"
PACKAGES = ("PySide6==6.11.2", "requests==2.34.2", "beautifulsoup4==4.14.3")


def main():
    if sys.platform != "win32" or platform.machine().upper() not in {"AMD64", "X86_64"}:
        raise RuntimeError("Windows 64비트에서 빌드해 주세요.")
    DIST_ROOT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    # Never remove a caller-provided or escaped filesystem path.
    if OUTPUT.resolve().parent != DIST_ROOT.resolve() or OUTPUT.name != "SaraminFinder":
        raise RuntimeError("배포 출력 경로가 예상 위치가 아닙니다.")
    shutil.rmtree(DIST_ROOT / "SaraminFinder.old", ignore_errors=True)
    if OUTPUT.exists():
        try:
            # A running app locks its DLLs; renaming fails before anything is deleted.
            stale = OUTPUT.rename(DIST_ROOT / "SaraminFinder.old")
        except OSError:
            raise RuntimeError("사람인 공고 관리 앱을 종료한 뒤 다시 실행해 주세요.") from None
        shutil.rmtree(stale)
    runtime = OUTPUT / "runtime"
    vendor = OUTPUT / "vendor"
    app = OUTPUT / "app"
    runtime.mkdir(parents=True)
    archive = CACHE / EMBED_NAME
    if not archive.exists():
        print(f"Downloading official Python embeddable runtime: {EMBED_URL}", flush=True)
        urllib.request.urlretrieve(EMBED_URL, archive)
    with zipfile.ZipFile(archive) as source:
        source.extractall(runtime)
    pth = runtime / "python312._pth"
    pth.write_text("python312.zip\n.\n..\\app\n..\\vendor\nimport site\n", encoding="utf-8")
    print("Installing pinned packages into the portable folder...", flush=True)
    subprocess.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
                    "--no-warn-script-location", "--target", str(vendor),
                    "--platform", "win_amd64", "--python-version", "3.12",
                    "--implementation", "cp", "--only-binary=:all:", *PACKAGES], check=True)
    shutil.copytree(DESKTOP / "src" / "saramin_finder", app / "saramin_finder",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(DESKTOP / "font", OUTPUT / "font")
    shutil.copy2(DESKTOP / "packaging" / "실행.bat", OUTPUT / "실행.bat")
    (OUTPUT / "README.txt").write_text(
        "사람인 공고 관리 PC 앱\n\n실행.bat를 더블클릭하세요. 실행 중 CMD 창은 남지 않습니다.\n"
        "데이터와 로그: %LOCALAPPDATA%\\SaraminAIFinder\\\n"
        "Python 설치 및 pip 실행은 필요하지 않습니다.\n", encoding="utf-8")
    print(f"Portable app ready: {OUTPUT}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        sys.exit(str(exc))
