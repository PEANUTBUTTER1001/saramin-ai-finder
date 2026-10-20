"""Exercise Windows shortcut creation in isolated folders without starting the app."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "packaging" / "create_shortcut.ps1"
pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows Shell shortcut tool")


def portable_folder(root):
    for relative in ("runtime/pythonw.exe", "runtime/python312._pth", "app/saramin_finder/main.py"):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"test placeholder; never executed")
    shutil.copy2(SCRIPT, root / SCRIPT.name)
    return root


def create_shortcut(root, desktop):
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
         str(root / SCRIPT.name), "-DesktopDirectory", str(desktop)],
        capture_output=True, timeout=30,
    )


def read_shortcut(path):
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command",
         "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
         "$shell = New-Object -ComObject WScript.Shell; "
         "$link = $shell.CreateShortcut($env:SARFINDER_TEST_LINK); "
         "[pscustomobject]@{Target=$link.TargetPath;Arguments=$link.Arguments;"
         "WorkingDirectory=$link.WorkingDirectory;Icon=$link.IconLocation} | ConvertTo-Json -Compress"],
        env={**os.environ, "SARFINDER_TEST_LINK": str(path)},
        capture_output=True, timeout=30, check=True,
    )
    return json.loads(result.stdout.decode("utf-8-sig"))


def test_shortcut_uses_packaged_location_and_updates_after_move(tmp_path):
    desktop = tmp_path / "OneDrive 바탕화면"
    desktop.mkdir()
    first = portable_folder(tmp_path / "앱 폴더 '처음' & 테스트")
    result = create_shortcut(first, desktop)
    assert result.returncode == 0, result.stdout + result.stderr
    path = desktop / "사람인 공고 관리.lnk"
    link = read_shortcut(path)
    assert Path(link["Target"]) == first / "runtime/pythonw.exe"
    assert link["Arguments"] == "-m saramin_finder.main"
    assert Path(link["WorkingDirectory"]) == first
    assert link["Icon"] == str(first / "runtime/pythonw.exe") + ",0"

    second = tmp_path / "이동한 배포 폴더"
    first.rename(second)
    result = create_shortcut(second, desktop)
    assert result.returncode == 0, result.stdout + result.stderr
    link = read_shortcut(path)
    assert Path(link["Target"]) == second / "runtime/pythonw.exe"
    assert Path(link["WorkingDirectory"]) == second
    assert len(list(desktop.glob("*.lnk"))) == 1


def test_incomplete_distribution_preserves_existing_shortcut(tmp_path):
    root = portable_folder(tmp_path / "배포 폴더")
    desktop = tmp_path / "바탕화면"
    desktop.mkdir()
    assert create_shortcut(root, desktop).returncode == 0
    path = desktop / "사람인 공고 관리.lnk"
    original = path.read_bytes()
    (root / "runtime/pythonw.exe").unlink()
    assert create_shortcut(root, desktop).returncode == 1
    assert path.read_bytes() == original


def test_missing_desktop_fails_without_creating_directory(tmp_path):
    root = portable_folder(tmp_path / "배포 폴더")
    desktop = tmp_path / "없는 바탕화면"
    assert create_shortcut(root, desktop).returncode == 1
    assert not desktop.exists()
