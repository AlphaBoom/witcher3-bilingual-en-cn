param([string]$SettingsPath = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'The Witcher 3\dx12user.settings'))
$ErrorActionPreference = 'Stop'
$taskDirectory = [System.IO.Path]::GetFullPath($PSScriptRoot)
$gameDirectory = [System.IO.Path]::GetFullPath((Split-Path -Parent $taskDirectory))
if (-not (Test-Path -LiteralPath (Join-Path $gameDirectory 'bin\x64_dx12\witcher3.exe'))) { throw 'Expected game executable missing.' }
if (Get-Process -Name witcher3 -ErrorAction SilentlyContinue) { throw 'Close The Witcher 3 before installation.' }
$reportPath = Join-Path $taskDirectory 'report.json'
$reportData = [System.IO.File]::ReadAllText($reportPath) | ConvertFrom-Json
$originalTarget = Join-Path $gameDirectory 'content\content0\cn.w3strings'
$preparedTarget = Join-Path $taskDirectory 'prepared\cn.w3strings'
$backupDirectory = if ($reportData.backup_directory) { Join-Path $taskDirectory $reportData.backup_directory } else { Join-Path $taskDirectory 'backup' }
$backupDirectory = [System.IO.Path]::GetFullPath($backupDirectory)
if (-not $backupDirectory.StartsWith($taskDirectory + [System.IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Unexpected backup directory.' }
$backupTarget = Join-Path $backupDirectory 'cn.w3strings'
$currentVersion = (Get-Item -LiteralPath (Join-Path $gameDirectory 'bin\x64_dx12\witcher3.exe')).VersionInfo.FileVersion.Split('(')[0].Trim()
if ($currentVersion -ne $reportData.game_version) { throw 'Game updated after preparation. Regenerate from current game files.' }
$settingsPath = [System.IO.Path]::GetFullPath($SettingsPath)
$settingsBackup = Join-Path $backupDirectory 'dx12user.settings'
if ((Get-FileHash -LiteralPath $backupTarget -Algorithm SHA256).Hash.ToLowerInvariant() -ne $reportData.source_sha256.cn) { throw 'Backup checksum differs.' }
$currentTargetHash = (Get-FileHash -LiteralPath $originalTarget -Algorithm SHA256).Hash.ToLowerInvariant()
if ($currentTargetHash -notin @($reportData.source_sha256.cn, $reportData.previous_output_sha256, $reportData.output_sha256)) { throw 'Original file changed since preparation.' }
if ((Get-FileHash -LiteralPath $preparedTarget -Algorithm SHA256).Hash.ToLowerInvariant() -ne $reportData.output_sha256) { throw 'Prepared checksum differs.' }
$scriptTarget = Join-Path $gameDirectory 'mods\modBilingualEnCnPlaceholders\content\scripts\local\bilingual_placeholders.ws'
$preparedScript = Join-Path $taskDirectory 'prepared\bilingual_placeholders.ws'
if ((Get-FileHash -LiteralPath $preparedScript -Algorithm SHA256).Hash.ToLowerInvariant() -ne $reportData.script_mod.sha256) { throw 'Prepared script checksum differs.' }
$scriptExisted = Test-Path -LiteralPath $scriptTarget
if ($scriptExisted) {
    $installedPath = Join-Path $taskDirectory 'installed.json'
    $oldInstalled = [System.IO.File]::ReadAllText($installedPath) | ConvertFrom-Json
    $currentScriptHash = (Get-FileHash -LiteralPath $scriptTarget -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($currentScriptHash -notin @($oldInstalled.script_sha256, $reportData.script_mod.sha256)) { throw 'Existing placeholder mod was changed by another edit.' }
}
$settingsBefore = [System.IO.File]::ReadAllText($settingsPath)
foreach ($settingName in @('RequestedTextLanguage', 'TextLanguage')) {
    if ([regex]::Matches($settingsBefore, ('(?m)^' + $settingName + '=[^\r\n]*')).Count -ne 1) {
        throw ('Unexpected setting count: ' + $settingName)
    }
}
$settingsAfter = [regex]::Replace($settingsBefore, '(?m)^RequestedTextLanguage=[^\r\n]*', 'RequestedTextLanguage=CN')
$settingsAfter = [regex]::Replace($settingsAfter, '(?m)^TextLanguage=[^\r\n]*', 'TextLanguage=CN')
if (Test-Path -LiteralPath $settingsBackup) {
    # Retain the original language settings; rollback uses this run's snapshot.
} else {
    Copy-Item -LiteralPath $settingsPath -Destination $settingsBackup
}
$rollbackDirectory = Join-Path $taskDirectory ('history\install-rollback-' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ'))
New-Item -ItemType Directory -Path $rollbackDirectory | Out-Null
$rollbackTarget = Join-Path $rollbackDirectory 'cn.w3strings'
$rollbackSettings = Join-Path $rollbackDirectory 'dx12user.settings'
$rollbackScript = Join-Path $rollbackDirectory 'bilingual_placeholders.ws'
Copy-Item -LiteralPath $originalTarget -Destination $rollbackTarget
Copy-Item -LiteralPath $settingsPath -Destination $rollbackSettings
if ($scriptExisted) { Copy-Item -LiteralPath $scriptTarget -Destination $rollbackScript }
$settingsWasWritten = $false
$scriptWasWritten = $false
try {
    New-Item -ItemType Directory -Path (Split-Path -Parent $scriptTarget) -Force | Out-Null
    $scriptWasWritten = $true
    Copy-Item -LiteralPath $preparedScript -Destination $scriptTarget
    if ((Get-FileHash -LiteralPath $scriptTarget -Algorithm SHA256).Hash.ToLowerInvariant() -ne $reportData.script_mod.sha256) { throw 'Installed script checksum differs.' }
    Copy-Item -LiteralPath $preparedTarget -Destination $originalTarget
    if ((Get-FileHash -LiteralPath $originalTarget -Algorithm SHA256).Hash.ToLowerInvariant() -ne $reportData.output_sha256) { throw 'Installed checksum differs.' }
    if ($settingsAfter -ne $settingsBefore) {
        $settingsWasWritten = $true
        [System.IO.File]::WriteAllText($settingsPath, $settingsAfter, (New-Object System.Text.UTF8Encoding($false)))
    }
    if ([System.IO.File]::ReadAllText($settingsPath) -ne $settingsAfter) { throw 'Settings verification failed.' }
    $installedData = [ordered]@{
        installed_at_utc = [DateTime]::UtcNow.ToString('o')
        game_version = $reportData.game_version
        backup_directory = $reportData.backup_directory
        target = $originalTarget
        target_sha256 = $reportData.output_sha256
        script = $scriptTarget
        script_sha256 = $reportData.script_mod.sha256
        dynamic_bilingual_entries = $reportData.dynamic_bilingual_entries
        settings = $settingsPath
        text_language = 'CN'
        speech_language = 'EN'
    }
    $installedData | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskDirectory 'installed.json') -Encoding UTF8
    Write-Output 'Installed and checksum-verified. English first, Simplified Chinese secondary. Voice remains English.'
} catch {
    if ((Get-FileHash -LiteralPath $originalTarget -Algorithm SHA256).Hash.ToLowerInvariant() -ne $currentTargetHash) {
        Copy-Item -LiteralPath $rollbackTarget -Destination $originalTarget
    }
    if ($scriptWasWritten) {
        if ($scriptExisted) { Copy-Item -LiteralPath $rollbackScript -Destination $scriptTarget }
        elseif (Test-Path -LiteralPath $scriptTarget) { Remove-Item -LiteralPath $scriptTarget }
    }
    if ($settingsWasWritten) { Copy-Item -LiteralPath $rollbackSettings -Destination $settingsPath }
    throw
}
