$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
py -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
$shell = New-Object -ComObject WScript.Shell
$startup = [Environment]::GetFolderPath('Startup')
$shortcut = $shell.CreateShortcut((Join-Path $startup 'Lil-Bot.lnk'))
$shortcut.TargetPath = Join-Path $env:WINDIR 'System32\wscript.exe'
$shortcut.Arguments = '"' + (Join-Path $PSScriptRoot 'start_background.vbs') + '"'
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.Save()
Write-Host 'Lil-Bot will start silently when you sign in. Keep this folder in its current location.'
Start-Process wscript.exe -ArgumentList ('"' + (Join-Path $PSScriptRoot 'start_background.vbs') + '"')
