param([string]$SettingsPath = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'The Witcher 3\dx12user.settings'))
$ErrorActionPreference = 'Stop'

# Use .NET directly: child Windows PowerShell may not expose Get-FileHash.
function Get-BilingualFileHash {
    param([string]$LiteralPath, [string]$Algorithm = 'SHA256')
    if ($Algorithm -ne 'SHA256') { throw 'Only SHA256 is supported.' }
    $stream = [System.IO.File]::OpenRead($LiteralPath)
    $hasher = [System.Security.Cryptography.SHA256]::Create()
    try {
        [PSCustomObject]@{ Hash = ([BitConverter]::ToString($hasher.ComputeHash($stream))).Replace('-', '') }
    } finally {
        $hasher.Dispose()
        $stream.Dispose()
    }
}

$taskDirectory = [System.IO.Path]::GetFullPath($PSScriptRoot)
$gameDirectory = [System.IO.Path]::GetFullPath((Split-Path -Parent $taskDirectory))
if (-not (Test-Path -LiteralPath (Join-Path $gameDirectory 'bin\x64_dx12\witcher3.exe'))) { throw 'Expected game executable missing.' }
if (Get-Process -Name witcher3 -ErrorAction SilentlyContinue) { throw 'Close The Witcher 3 before restoring.' }
$reportData = [System.IO.File]::ReadAllText((Join-Path $taskDirectory 'report.json')) | ConvertFrom-Json
$targetPath = Join-Path $gameDirectory 'content\content0\cn.w3strings'
$backupDirectory = if ($reportData.backup_directory) { Join-Path $taskDirectory $reportData.backup_directory } else { Join-Path $taskDirectory 'backup' }
$backupDirectory = [System.IO.Path]::GetFullPath($backupDirectory)
if (-not $backupDirectory.StartsWith($taskDirectory + [System.IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Unexpected backup directory.' }
$backupPath = Join-Path $backupDirectory 'cn.w3strings'
$installedHash = (Get-BilingualFileHash -LiteralPath $targetPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($installedHash -notin @($reportData.output_sha256, $reportData.source_sha256.cn)) {
    throw 'Game text changed after installation. Stop to avoid overwriting an update or another mod.'
}
if ((Get-BilingualFileHash -LiteralPath $backupPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $reportData.source_sha256.cn) { throw 'Backup checksum differs.' }
$scriptTarget = Join-Path $gameDirectory 'mods\modBilingualEnCnPlaceholders\content\scripts\local\bilingual_placeholders.ws'
if (Test-Path -LiteralPath $scriptTarget) {
    if ((Get-BilingualFileHash -LiteralPath $scriptTarget -Algorithm SHA256).Hash.ToLowerInvariant() -ne $reportData.script_mod.sha256) { throw 'Placeholder script changed after installation. Inspect before restoring.' }
}
$settingsPath = [System.IO.Path]::GetFullPath($SettingsPath)
$settingsBackup = Join-Path $backupDirectory 'dx12user.settings'
$currentSettings = [System.IO.File]::ReadAllText($settingsPath)
$previousSettings = [System.IO.File]::ReadAllText($settingsBackup)
$restoredSettings = $currentSettings
foreach ($settingName in @('RequestedTextLanguage', 'TextLanguage')) {
    $settingPattern = '(?m)^' + $settingName + '=[^\r\n]*'
    $oldSetting = [regex]::Match($previousSettings, $settingPattern).Value
    if (-not $oldSetting) { throw 'Original language setting missing.' }
    $restoredSettings = [regex]::Replace($restoredSettings, $settingPattern, $oldSetting)
}
Copy-Item -LiteralPath $backupPath -Destination $targetPath
if ((Get-BilingualFileHash -LiteralPath $targetPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $reportData.source_sha256.cn) { throw 'Restored checksum differs.' }
if ($restoredSettings -ne $currentSettings) {
    [System.IO.File]::WriteAllText($settingsPath, $restoredSettings, (New-Object System.Text.UTF8Encoding($false)))
}
if (Test-Path -LiteralPath $scriptTarget) { Remove-Item -LiteralPath $scriptTarget }
Write-Output 'Restored the original subtitle file and previous text language. Other game settings were retained.'
