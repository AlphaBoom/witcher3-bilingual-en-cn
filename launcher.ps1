# Double-click entry point for install.cmd / check.cmd / restore.cmd.
# Finds the game folder and Python, then runs src/maintain.py.
param(
    [ValidateSet('install', 'check', 'restore')][string]$Action = 'install',
    [string]$GameDir
)
$ErrorActionPreference = 'Stop'
$savedDirFile = Join-Path $PSScriptRoot 'game-dir.txt'

function Test-GameDir([string]$Dir) {
    $Dir -and (Test-Path -LiteralPath (Join-Path $Dir 'bin\x64_dx12\witcher3.exe'))
}

function Find-GameDir {
    $candidates = @()
    if (Test-Path -LiteralPath $savedDirFile) { $candidates += (Get-Content -LiteralPath $savedDirFile -Raw).Trim() }
    # The project may itself sit inside the game folder.
    $dir = $PSScriptRoot
    while ($dir) { $candidates += $dir; $dir = Split-Path -Parent $dir }
    $steam = (Get-ItemProperty 'HKCU:\Software\Valve\Steam' -ErrorAction SilentlyContinue).SteamPath
    if ($steam) {
        $libraries = @($steam)
        $vdf = Join-Path $steam 'steamapps\libraryfolders.vdf'
        if (Test-Path -LiteralPath $vdf) {
            foreach ($m in [regex]::Matches((Get-Content -LiteralPath $vdf -Raw), '"path"\s+"([^"]+)"')) {
                $libraries += $m.Groups[1].Value.Replace('\\', '\')
            }
        }
        # [IO.Path]::Combine tolerates library drives that are not connected.
        foreach ($lib in $libraries) { $candidates += [System.IO.Path]::Combine($lib, 'steamapps\common\The Witcher 3') }
    }
    foreach ($key in 'HKLM:\SOFTWARE\WOW6432Node\GOG.com\Games', 'HKLM:\SOFTWARE\GOG.com\Games') {
        Get-ChildItem $key -ErrorAction SilentlyContinue | ForEach-Object {
            $candidates += (Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue).path
        }
    }
    foreach ($c in $candidates) {
        if (Test-GameDir $c) { return [System.IO.Path]::GetFullPath($c) }
    }
    return $null
}

function Find-Python {
    foreach ($cmd in @(@('py', '-3'), @('python'))) {
        if (-not (Get-Command $cmd[0] -ErrorAction SilentlyContinue)) { continue }
        try {
            $ok = & $cmd[0] @($cmd | Select-Object -Skip 1) -c 'import sys; print(sys.version_info >= (3, 10))' 2>$null
            if ($ok -eq 'True') { return $cmd }
        } catch {}
    }
    return $null
}

function Stop-WithMessage([string[]]$Lines) {
    Write-Host ''
    foreach ($line in $Lines) { Write-Host $line -ForegroundColor Yellow }
    exit 1
}

Write-Host '=== 巫师 3 英中双语字幕 ===' -ForegroundColor Cyan

$python = Find-Python
if (-not $python) {
    Stop-WithMessage @(
        '没有找到 Python 3.10 或更新版本。',
        '请从 https://www.python.org/downloads/windows/ 下载安装，',
        '安装时勾选 "Add python.exe to PATH"，装好后重新双击本文件。'
    )
}

if (-not $GameDir) {
    $found = Find-GameDir
    if ($found) {
        Write-Host "找到游戏目录：$found"
        $answer = Read-Host '直接按回车确认；如果不对，请把正确的游戏文件夹拖进本窗口后按回车'
    } else {
        Write-Host '没有自动找到游戏目录。'
        $answer = Read-Host '请把游戏文件夹（里面有 bin 和 content）拖进本窗口，然后按回车'
    }
    $GameDir = if ($answer.Trim()) { $answer.Trim().Trim('"') } else { $found }
}
if (-not (Test-GameDir $GameDir)) {
    Stop-WithMessage @(
        "这个文件夹不是游戏目录：$GameDir",
        '游戏目录里应该能看到 bin 和 content 两个文件夹，并且有 bin\x64_dx12\witcher3.exe。'
    )
}
$GameDir = [System.IO.Path]::GetFullPath($GameDir)
Set-Content -LiteralPath $savedDirFile -Value $GameDir -Encoding UTF8

if ($Action -ne 'check' -and (Get-Process -Name witcher3 -ErrorAction SilentlyContinue)) {
    Stop-WithMessage @('游戏正在运行，请完全退出游戏后再试。')
}

$maintain = Join-Path $PSScriptRoot 'src\maintain.py'
$arguments = switch ($Action) {
    'install' { @('update', '--game-dir', $GameDir, '--install') }
    default { @($Action, '--game-dir', $GameDir) }
}
if ($Action -eq 'install') { Write-Host '正在备份原文件、生成双语文本并校验，大约需要一两分钟……' }
& $python[0] @($python | Select-Object -Skip 1) $maintain @arguments | Tee-Object -Variable output
$code = $LASTEXITCODE

if ($code -ne 0) {
    Stop-WithMessage @(
        '出错了，没有完成。游戏文件保持原样或已自动回滚，不会处于半安装状态。',
        '常见原因：',
        '  · 游戏刚更新，但旧的双语文件还在 → 先在 Steam 里“验证游戏文件完整性”，再重新双击 install.cmd',
        '  · 提示拒绝访问（Access denied）→ 右键 install.cmd，选择“以管理员身份运行”',
        '其他情况，请把本窗口的全部文字复制到 https://github.com/AlphaBoom/witcher3-bilingual-en-cn/issues'
    )
}

Write-Host ''
switch ($Action) {
    'install' {
        Write-Host '安装完成！' -ForegroundColor Green
        Write-Host '进入游戏后，在 选项 > 语言 中确认：语音 = English，文本 = 简体中文，字幕 = 开启。'
    }
    'restore' {
        Write-Host '已还原为原版中文字幕和原来的语言设置。' -ForegroundColor Green
    }
    'check' {
        $state = ($output | Select-Object -Last 1 | ConvertFrom-Json).state
        $message = switch ($state) {
            'installed' { '已安装，文件完整，和当前游戏版本一致。' }
            'game-updated' { '游戏已更新，双语可能失效。请先在 Steam 里“验证游戏文件完整性”，再双击 install.cmd。' }
            'script-missing-or-changed' { '配套脚本缺失或被改动，请重新双击 install.cmd。' }
            'game-updated-or-file-changed' { '语言文件被游戏更新或其他 mod 改动过，请重新双击 install.cmd。' }
            default { '尚未安装。双击 install.cmd 即可安装。' }
        }
        Write-Host $message -ForegroundColor $(if ($state -eq 'installed') { 'Green' } else { 'Yellow' })
    }
}
