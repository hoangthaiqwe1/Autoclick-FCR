# Script cai dat thu vien qua proxy NTLM cong ty
# PowerShell su dung Windows credentials tu dong

$ErrorActionPreference = "Continue"
$packages_dir = "$PSScriptRoot\packages"

# Tao thu muc packages
if (!(Test-Path $packages_dir)) {
    New-Item -ItemType Directory -Path $packages_dir | Out-Null
}

# Cau hinh proxy voi Windows credentials
$proxy = New-Object System.Net.WebProxy("http://10.30.168.246:9090", $true)
$proxy.Credentials = [System.Net.CredentialCache]::DefaultNetworkCredentials
[System.Net.WebRequest]::DefaultWebProxy = $proxy

# Danh sach packages can tai (tu PyPI)
$packages = @(
    @{name="selenium"; version="4.21.0"; url="https://files.pythonhosted.org/packages/py3/s/selenium/selenium-4.21.0-py3-none-any.whl"},
    @{name="python-dotenv"; version="1.0.1"; url="https://files.pythonhosted.org/packages/py3/p/python_dotenv/python_dotenv-1.0.1-py3-none-any.whl"},
    @{name="schedule"; version="1.2.2"; url="https://files.pythonhosted.org/packages/py3/s/schedule/schedule-1.2.2-py3-none-any.whl"},
    @{name="webdriver-manager"; version="4.0.1"; url="https://files.pythonhosted.org/packages/py3/w/webdriver_manager/webdriver_manager-4.0.1-py3-none-any.whl"}
)

Write-Host "=== Dang cai dat thu vien ===" -ForegroundColor Green
Write-Host ""

foreach ($pkg in $packages) {
    Write-Host "[*] Dang cai $($pkg.name)..." -NoNewline
    try {
        pip install $pkg.name --proxy "http://10.30.168.246:9090" --trusted-host pypi.org --trusted-host files.pythonhosted.org 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host " OK" -ForegroundColor Green
        } else {
            Write-Host " Thu cach khac..." -ForegroundColor Yellow
            # Thu tai bang PowerShell (dung Windows auth)
            $wc = New-Object System.Net.WebClient
            $wc.Proxy = $proxy
            $filename = "$packages_dir\$($pkg.name).whl"
            $wc.DownloadFile($pkg.url, $filename)
            pip install $filename 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-Host " OK (offline)" -ForegroundColor Green
            } else {
                Write-Host " FAILED" -ForegroundColor Red
            }
        }
    } catch {
        Write-Host " ERROR: $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== Hoan tat! ===" -ForegroundColor Green
Write-Host "Bay gio ban co the chay: python Run_Portal_Checkin.py"
pause
