# create_shortcut.ps1 — Creates desktop shortcut for Shira Lab
# Uses the script's own location as the project root (no hardcoded paths).
# The shortcut uses shira.ico which is regenerated when palette changes.
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = $ScriptDir
$ShortcutPath = Join-Path $ProjectRoot "Shira Lab.lnk"
$TargetPath = Join-Path $ProjectRoot "launch.bat"
$IconPath = Join-Path $ProjectRoot "shira.ico"

$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetPath
$Shortcut.IconLocation = "$IconPath,0"
$Shortcut.WorkingDirectory = $ProjectRoot
$Shortcut.Description = "Shira Lab - Terminal UI Application"
$Shortcut.Save()
Write-Host "Shortcut created at: $ShortcutPath"
Write-Host "Icon: $IconPath (regenerated when palette changes)"

# Also try to refresh the desktop shortcut icon cache
# This forces Windows to reload the .lnk icon
try {
    $sig = '[DllImport("user32.dll")] public static extern bool SendMessageTimeout(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam, uint fuFlags, uint uTimeout, out IntPtr lpdwResult);'
    $type = Add-Type -MemberDefinition $sig -Name "Win32SendMessageTimeout" -Namespace Win32 -PassThru
    $HWND_BROADCAST = [IntPtr]0xffff
    $WM_SETTINGCHANGE = 0x1A
    $result = [IntPtr]::Zero
    $type::SendMessageTimeout($HWND_BROADCAST, $WM_SETTINGCHANGE, [IntPtr]::Zero, [IntPtr]::Zero, 2, 5000, [ref]$result) | Out-Null
} catch {
    # Silently ignore refresh errors
}