param(
    [string]$AppDirectory = $PSScriptRoot,
    [string]$DesktopDirectory = [Environment]::GetFolderPath('DesktopDirectory')
)

$ErrorActionPreference = 'Stop'

try {
    $appRoot = (Resolve-Path -LiteralPath $AppDirectory).ProviderPath
    $pythonPath = Join-Path $appRoot 'runtime\pythonw.exe'
    foreach ($relativePath in @('runtime\pythonw.exe', 'runtime\python312._pth', 'app\saramin_finder\main.py')) {
        if (-not (Test-Path -LiteralPath (Join-Path $appRoot $relativePath) -PathType Leaf)) {
            throw "배포 파일이 없습니다: $relativePath. 배포 폴더 전체를 복원해 주세요."
        }
    }
    if ([string]::IsNullOrWhiteSpace($DesktopDirectory) -or
        -not (Test-Path -LiteralPath $DesktopDirectory -PathType Container)) {
        throw '바탕화면 폴더를 찾을 수 없습니다.'
    }
    $desktopRoot = (Resolve-Path -LiteralPath $DesktopDirectory).ProviderPath
    $shortcutPath = Join-Path $desktopRoot '사람인 공고 관리.lnk'
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $pythonPath
    $shortcut.Arguments = '-m saramin_finder.main'
    $shortcut.WorkingDirectory = $appRoot
    $shortcut.IconLocation = "$pythonPath,0"
    $shortcut.Description = '사람인 공고 관리 PC 앱'
    $shortcut.Save()
    Write-Host "바탕화면 바로가기 생성 완료: $shortcutPath"
    exit 0
} catch {
    Write-Host "바로가기 생성 실패: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
