$errors = $null
$tokens = $null
$null = [System.Management.Automation.Language.Parser]::ParseFile("$PSScriptRoot\Run_Portal_Checkin.ps1", [ref]$tokens, [ref]$errors)
if ($errors.Count -gt 0) {
    Write-Host "ERRORS FOUND: $($errors.Count)"
    foreach ($e in $errors) {
        Write-Host "Line $($e.Extent.StartLineNumber): $($e.Message)"
    }
} else {
    Write-Host "NO ERRORS"
}
