<#
FE Credit Auto Check-in/Check-out - PowerShell Version
=======================================================
Chay: .\Run_Portal_Checkin.ps1
#>

# ==================== CAU HINH ====================
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$HR_PORTAL_URL = "https://hrportal.fecredit.com.vn/work-attendance"
$CDP_PORT = 9222
$LOG_FILE = Join-Path $ScriptDir "auto_checkin.log"
$CHECKIN_RECORD_FILE = Join-Path $ScriptDir "last_checkin.txt"

# Doc file .env
$envFile = Join-Path $ScriptDir ".env"
$HR_USERNAME = ""
$HR_PASSWORD = ""
$CHECKOUT_HOUR = 20
$CHECKOUT_MINUTE = 0

if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $parts = $line.Split("=", 2)
            $key = $parts[0].Trim()
            $val = $parts[1].Trim()
            switch ($key) {
                "HR_USERNAME"    { $script:HR_USERNAME = $val }
                "HR_PASSWORD"    { $script:HR_PASSWORD = $val }
                "CHECKOUT_HOUR"  { $script:CHECKOUT_HOUR = [int]$val }
                "CHECKOUT_MINUTE"{ $script:CHECKOUT_MINUTE = [int]$val }
            }
        }
    }
}

$CHROME_PATHS = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "C:\Program Files\Microsoft\Edge\Application\msedge.exe"
)

# ==================== FUNCTIONS ====================

function Write-Log($msg) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$timestamp] $msg"
    Write-Host $line
    try { Add-Content -Path $LOG_FILE -Value $line -Encoding UTF8 } catch {}
}

function Test-PortOpen($port) {
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $tcp.Connect("127.0.0.1", $port)
        $tcp.Close()
        return $true
    } catch {
        return $false
    }
}

function Find-Chrome {
    foreach ($p in $CHROME_PATHS) {
        if (Test-Path $p) { return $p }
    }
    return $null
}

function Start-ChromeBrowser($url) {
    if (Test-PortOpen $CDP_PORT) { return $true }
    $chrome = Find-Chrome
    if (-not $chrome) { Write-Log "ERROR: Khong tim thay Chrome!"; return $false }
    $userData = Join-Path $ScriptDir "chrome_profile"
    Start-Process -FilePath $chrome -ArgumentList "--remote-debugging-port=$CDP_PORT", "--user-data-dir=$userData", "--no-first-run", "--no-default-browser-check", $url -WindowStyle Normal
    for ($i = 0; $i -lt 30; $i++) {
        if (Test-PortOpen $CDP_PORT) { return $true }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Invoke-CDP($endpoint) {
    try {
        $response = Invoke-RestMethod -Uri "http://127.0.0.1:${CDP_PORT}${endpoint}" -TimeoutSec 10 -Proxy ""
        return $response
    } catch {
        return $null
    }
}

function Get-PageTabs {
    return Invoke-CDP "/json"
}

function Send-WebSocketMessage($wsUrl, $message) {
    # WebSocket handshake va send message qua CDP
    $uri = [System.Uri]$wsUrl
    $host_ = $uri.Host
    $port_ = $uri.Port
    $path_ = $uri.PathAndQuery

    $tcp = New-Object System.Net.Sockets.TcpClient
    $tcp.Connect($host_, $port_)
    $stream = $tcp.GetStream()
    $stream.ReadTimeout = 30000

    # Generate WebSocket key
    $keyBytes = New-Object byte[] 16
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($keyBytes)
    $key = [Convert]::ToBase64String($keyBytes)

    # Handshake
    $handshake = "GET $path_ HTTP/1.1`r`nHost: ${host_}:${port_}`r`nUpgrade: websocket`r`nConnection: Upgrade`r`nSec-WebSocket-Key: $key`r`nSec-WebSocket-Version: 13`r`n`r`n"
    $handshakeBytes = [System.Text.Encoding]::UTF8.GetBytes($handshake)
    $stream.Write($handshakeBytes, 0, $handshakeBytes.Length)

    # Read handshake response
    $buffer = New-Object byte[] 4096
    $responseStr = ""
    while (-not $responseStr.Contains("`r`n`r`n")) {
        $read = $stream.Read($buffer, 0, $buffer.Length)
        $responseStr += [System.Text.Encoding]::UTF8.GetString($buffer, 0, $read)
    }

    # Send frame
    $payload = [System.Text.Encoding]::UTF8.GetBytes($message)
    $frame = [System.Collections.Generic.List[byte]]::new()
    $frame.Add(0x81)  # FIN + Text

    $maskKey = New-Object byte[] 4
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($maskKey)
    $len = $payload.Length

    if ($len -lt 126) {
        $frame.Add([byte](0x80 -bor $len))
    } elseif ($len -lt 65536) {
        $frame.Add([byte](0x80 -bor 126))
        $frame.Add([byte](($len -shr 8) -band 0xFF))
        $frame.Add([byte]($len -band 0xFF))
    }

    $frame.AddRange($maskKey)
    for ($i = 0; $i -lt $payload.Length; $i++) {
        $frame.Add([byte]($payload[$i] -bxor $maskKey[$i % 4]))
    }

    $frameBytes = $frame.ToArray()
    $stream.Write($frameBytes, 0, $frameBytes.Length)

    # Read response
    Start-Sleep -Milliseconds 500
    $respBuffer = New-Object byte[] 65536
    $respLen = 0
    if ($stream.DataAvailable) {
        $respLen = $stream.Read($respBuffer, 0, $respBuffer.Length)
    } else {
        Start-Sleep -Seconds 2
        if ($stream.DataAvailable) {
            $respLen = $stream.Read($respBuffer, 0, $respBuffer.Length)
        }
    }

    $tcp.Close()

    if ($respLen -lt 2) { return $null }

    # Parse WebSocket frame
    $secondByte = $respBuffer[1] -band 0x7F
    $offset = 2
    if ($secondByte -eq 126) { $offset = 4 }
    elseif ($secondByte -eq 127) { $offset = 10 }

    $payloadData = [System.Text.Encoding]::UTF8.GetString($respBuffer, $offset, $respLen - $offset)
    try {
        return $payloadData | ConvertFrom-Json
    } catch {
        return $payloadData
    }
}

function Invoke-JS($code) {
    $tabs = Get-PageTabs
    if (-not $tabs) { return $null }

    $tab = $tabs | Where-Object { $_.type -eq "page" } | Select-Object -First 1
    if (-not $tab) { $tab = $tabs | Select-Object -First 1 }
    if (-not $tab) { return $null }

    $ws = $tab.webSocketDebuggerUrl
    if (-not $ws) { return $null }

    $command = @{
        id = 1
        method = "Runtime.evaluate"
        params = @{
            expression = $code
            returnByValue = $true
            awaitPromise = $true
        }
    } | ConvertTo-Json -Depth 5

    try {
        return Send-WebSocketMessage $ws $command
    } catch {
        return $null
    }
}

# === LOGIN ===
function Wait-AndLogin {
    for ($attempt = 1; $attempt -le 8; $attempt++) {
        Start-Sleep -Seconds 5
        $tabs = Get-PageTabs
        if (-not $tabs) { continue }

        $url = ""
        foreach ($t in $tabs) {
            if ($t.type -eq "page") { $url = $t.url; break }
        }

        Write-Log "  [$attempt] $($url.Substring(0, [Math]::Min($url.Length, 70)))"

        if ($url -match "work-attendance" -or ($url -match "hrportal" -and $url -notmatch "sign-in")) {
            Write-Log "  Login thanh cong!"
            return $true
        }

        if ($url -match "sign-in" -and $url -notmatch "microsoftonline") {
            # Click "Dong y" neu co popup "Phien lam viec sap het han"
            Invoke-JS "(function(){var btns=document.querySelectorAll('button');for(var i=0;i<btns.length;i++){if(btns[i].textContent.indexOf('ng ')!==-1||btns[i].textContent.indexOf('Dong')!==-1||btns[i].textContent.indexOf('ồng')!==-1){btns[i].click();return'CLICKED_DONGY';}}return'NO_POPUP';})()" | Out-Null
            Start-Sleep -Seconds 2
            # Click Azure AD
            Invoke-JS "(function(){var b=document.querySelectorAll('button,a');for(var i=0;i<b.length;i++){if(b[i].textContent.indexOf('Azure')!==-1){b[i].click();return;}}})()"|Out-Null
            Start-Sleep -Seconds 8
            continue
        }

        if ($url -match "microsoftonline|login\.live") {
            # Pick account
            $r = Invoke-JS "(function(){var t=document.getElementById('tilesHolder');if(t){var f=t.querySelector('div[tabindex],div.table-row,[data-test-id]');if(f){f.click();return'PICKED';}}var rows=document.querySelectorAll('.table-row,[role=""button""]');for(var i=0;i<rows.length;i++){if(rows[i].textContent.indexOf('thai.dang')!==-1||rows[i].textContent.indexOf('fecredit')!==-1){rows[i].click();return'PICKED';}}return'NO';})()"
            $rStr = "$r"

            if ($rStr -match "PICKED") {
                # Cho redirect (Face Auth)
                for ($w = 0; $w -lt 12; $w++) {
                    Start-Sleep -Seconds 5
                    $tabs = Get-PageTabs
                    if ($tabs) {
                        foreach ($t in $tabs) { if ($t.type -eq "page") { $url = $t.url; break } }
                        if ($url -match "work-attendance" -or ($url -match "hrportal" -and $url -notmatch "sign-in")) {
                            Write-Log "  Login thanh cong (Face Auth)!"
                            return $true
                        }
                        if ($url -match "microsoftonline") {
                            $check = Invoke-JS "(function(){if(document.querySelector('input[name=""passwd""],#i0118'))return'PASS';if(document.getElementById('idSIButton9'))return'BTN';return'WAIT';})()"
                            if ("$check" -match "PASS|BTN") { break }
                            continue
                        } else { break }
                    }
                }

                # Check URL
                $tabs = Get-PageTabs
                if ($tabs) {
                    foreach ($t in $tabs) { if ($t.type -eq "page") { $url = $t.url; break } }
                    if ($url -match "work-attendance" -or ($url -match "hrportal" -and $url -notmatch "sign-in")) {
                        Write-Log "  Login thanh cong!"
                        return $true
                    }
                }
            }

            # Nhap Email
            for ($i = 0; $i -lt 5; $i++) {
                Start-Sleep -Seconds 2
                $r = Invoke-JS "(function(){var f=document.querySelector('input[name=""loginfmt""],#i0116');if(f){f.focus();f.value='$HR_USERNAME';f.dispatchEvent(new Event('input',{bubbles:true}));return'OK';}if(document.querySelector('input[name=""passwd""],#i0118'))return'PASS';return'W';})()"
                $rStr = "$r"
                if ($rStr -match "OK|PASS") { break }
            }

            if ($rStr -notmatch "PASS") {
                Start-Sleep -Seconds 1
                Invoke-JS "(function(){var b=document.getElementById('idSIButton9')||document.querySelector('input[type=""submit""]');if(b)b.click();})()" | Out-Null
            }

            # Nhap Password
            for ($i = 0; $i -lt 5; $i++) {
                Start-Sleep -Seconds 2
                $tabs = Get-PageTabs
                if ($tabs) {
                    foreach ($t in $tabs) { if ($t.type -eq "page") { $url = $t.url; break } }
                    if ($url -match "work-attendance" -or ($url -match "hrportal" -and $url -notmatch "sign-in")) {
                        Write-Log "  Login thanh cong!"
                        return $true
                    }
                }
                $r = Invoke-JS "(function(){var f=document.querySelector('input[name=""passwd""],#i0118');if(f){f.focus();f.value='$HR_PASSWORD';f.dispatchEvent(new Event('input',{bubbles:true}));return'OK';}return'W';})()"
                if ("$r" -match "OK") { break }
            }

            Start-Sleep -Seconds 1
            Invoke-JS "(function(){var b=document.getElementById('idSIButton9')||document.querySelector('input[type=""submit""]');if(b)b.click();})()" | Out-Null
            Start-Sleep -Seconds 6

            # Cho MFA/redirect
            for ($mfa = 0; $mfa -lt 24; $mfa++) {
                $tabs = Get-PageTabs
                if ($tabs) {
                    foreach ($t in $tabs) { if ($t.type -eq "page") { $url = $t.url; break } }
                    if ($url -match "work-attendance" -or ($url -match "hrportal" -and $url -notmatch "sign-in")) {
                        Write-Log "  Login thanh cong!"
                        return $true
                    }
                    if ($url -match "microsoftonline") {
                        Invoke-JS "(function(){var b=document.getElementById('idSIButton9')||document.querySelector('input[type=""submit""]');if(b)b.click();})()" | Out-Null
                        if ($mfa -eq 0) { Write-Log "  Dang cho xac thuc MFA..." }
                        Start-Sleep -Seconds 5
                        continue
                    } else { return $true }
                }
                Start-Sleep -Seconds 5
            }
            Write-Log "  Het thoi gian cho MFA"
            return $true
        }
    }
    return $false
}

# === CHECK-IN / CHECK-OUT ===
function Get-TodayAttendance {
    $js = @"
(function() {
    return fetch('https://hrportal.fecredit.com.vn/api/v1/employee-attendance/account-info', {
        method: 'GET',
        headers: {'Accept': 'application/json'},
        credentials: 'include'
    }).then(function(r) { return r.text(); })
    .catch(function(e) { return 'ERR:' + e.message; });
})()
"@
    $r = Invoke-JS $js
    if ($r -and $r.result -and $r.result.result -and $r.result.result.value) {
        $value = $r.result.result.value
        if ($value -notmatch "^ERR:") {
            try {
                $data = $value | ConvertFrom-Json
                if ($data.status -eq $true -and $data.data) {
                    $checkin = ""
                    $checkout = ""
                    if ($data.data.checkInTime) {
                        try { $checkin = ([datetime]::Parse($data.data.checkInTime)).ToString("HH:mm:ss") } catch { $checkin = $data.data.checkInTime }
                    }
                    if ($data.data.checkOutTime) {
                        try { $checkout = ([datetime]::Parse($data.data.checkOutTime)).ToString("HH:mm:ss") } catch { $checkout = $data.data.checkOutTime }
                    }
                    return @{ checkin = $checkin; checkout = $checkout; status = $data.data.status; fullName = $data.data.fullName }
                }
            } catch {}
        }
    }
    return $null
}

function Invoke-CheckIn {
    Write-Log ">>> CHECK-IN"
    $js = "(function(){return fetch('https://hrportal.fecredit.com.vn/api/v1/employee-attendance/check-in',{method:'POST',headers:{'Accept':'application/json','Content-Type':'application/json'},credentials:'include'}).then(function(r){return r.text().then(function(t){return'STATUS:'+r.status+' '+t;});}).catch(function(e){return'ERR:'+e.message;});})()"
    $r = Invoke-JS $js
    $rStr = "$r"
    Write-Log "  $rStr"

    if ($rStr -match "STATUS:200|STATUS:201") {
        Set-Content -Path $CHECKIN_RECORD_FILE -Value (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
        Write-Log "  CHECK-IN THANH CONG!"
        Invoke-JS "window.location.href='https://hrportal.fecredit.com.vn/work-attendance';" | Out-Null
        return $true
    } elseif ($rStr -match "CHECKIN_FAILED|`"code`":`"11`"") {
        Set-Content -Path $CHECKIN_RECORD_FILE -Value (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
        Write-Log "  Da check-in truoc do roi (API tra CHECKIN_FAILED)"
        return $true
    }
    return $false
}

function Invoke-CheckOut {
    Write-Log ">>> CHECK-OUT"
    $js = "(function(){return fetch('https://hrportal.fecredit.com.vn/api/v1/employee-attendance/check-out',{method:'POST',headers:{'Accept':'application/json','Content-Type':'application/json'},credentials:'include'}).then(function(r){return r.text().then(function(t){return'STATUS:'+r.status+' '+t;});}).catch(function(e){return'ERR:'+e.message;});})()"
    $r = Invoke-JS $js
    $rStr = "$r"
    Write-Log "  $rStr"

    if ($rStr -match "STATUS:200|STATUS:201") {
        Write-Log "  CHECK-OUT THANH CONG!"
        Invoke-JS "window.location.href='https://hrportal.fecredit.com.vn/work-attendance';" | Out-Null
        return $true
    }
    return $false
}

function Test-AlreadyCheckedIn {
    if (Test-Path $CHECKIN_RECORD_FILE) {
        $content = Get-Content $CHECKIN_RECORD_FILE -Raw
        return $content.Trim().StartsWith((Get-Date -Format "yyyy-MM-dd"))
    }
    return $false
}

# === MAIN ===
function Main {
    Write-Host ""
    Write-Host ("=" * 50)
    Write-Host "   FE CREDIT - AUTO CHAM CONG (PowerShell)"
    Write-Host ("=" * 50)
    Write-Host ""

    # Buoc 1: Mo Chrome va Login
    Write-Log "Buoc 1: Mo Chrome va login..."
    if (-not (Start-ChromeBrowser $HR_PORTAL_URL)) {
        Write-Log "Khong mo duoc Chrome!"
        Read-Host "Nhan Enter de dong"
        return
    }

    if (-not (Wait-AndLogin)) {
        Write-Log "Khong login duoc!"
        Read-Host "Nhan Enter de dong"
        return
    }

    Write-Log "LOGIN THANH CONG!"
    Write-Host ""

    # Navigate ve work-attendance
    Invoke-JS "window.location.href='https://hrportal.fecredit.com.vn/work-attendance';" | Out-Null
    # Cho trang load xong
    for ($w = 0; $w -lt 10; $w++) {
        Start-Sleep -Seconds 3
        $tabs = Get-PageTabs
        if ($tabs) {
            $currentUrl = ($tabs | Where-Object { $_.type -eq "page" } | Select-Object -First 1).url
            if ($currentUrl -match "work-attendance" -and $currentUrl -notmatch "sign-in") { break }
        }
    }

    # Buoc 2: Kiem tra check-in
    Write-Log "Buoc 2: Kiem tra check-in..."
    $attendance = Get-TodayAttendance
    # Retry neu lan dau fail
    if (-not $attendance) {
        Start-Sleep -Seconds 3
        $attendance = Get-TodayAttendance
    }

    if ($attendance) {
        Write-Log "  API: check-in=$($attendance.checkin), status=$($attendance.status)"
    }

    if (($attendance -and $attendance.checkin) -or (Test-AlreadyCheckedIn)) {
        $checkinDisplay = if ($attendance -and $attendance.checkin) { $attendance.checkin } else { "?" }
        Write-Log "  Da check-in luc $checkinDisplay"
    } else {
        Write-Log "  Chua check-in, dang check-in..."
        Start-Sleep -Seconds 2
        Invoke-CheckIn | Out-Null
        Start-Sleep -Seconds 3
        $attendance = Get-TodayAttendance
    }

    Write-Host ""

    # Buoc 3: Set gio check-out
    $defaultCheckout = (Get-Date).Date.AddHours($CHECKOUT_HOUR).AddMinutes($CHECKOUT_MINUTE)
    if ($defaultCheckout -le (Get-Date)) {
        $defaultCheckout = $defaultCheckout.AddDays(1)
    }

    $checkinDisplay = if ($attendance -and $attendance.checkin) { $attendance.checkin } else { "N/A" }
    Write-Host "  Check-in luc (API):   $checkinDisplay"
    Write-Host "  Check-out mac dinh:   $($defaultCheckout.ToString('HH:mm'))"
    Write-Host ""

    # Hoi gio check-out (30 giay)
    Write-Host "  Nhap gio check-out (VD: 17:30) [30s]: " -NoNewline
    $checkoutTime = $defaultCheckout
    
    # Input with timeout using background job
    $userInput = $null
    $job = Start-Job -ScriptBlock { [Console]::ReadLine() }
    if (Wait-Job $job -Timeout 30) {
        $userInput = Receive-Job $job
    }
    Remove-Job $job -Force -ErrorAction SilentlyContinue

    if ($userInput -and $userInput.Trim()) {
        try {
            $parts = $userInput.Trim().Replace("h", ":").Replace("H", ":").Split(":")
            $h = [int]$parts[0]
            $m = if ($parts.Length -gt 1) { [int]$parts[1] } else { 0 }
            $checkoutTime = (Get-Date).Date.AddHours($h).AddMinutes($m)
            if ($checkoutTime -le (Get-Date)) { $checkoutTime = $checkoutTime.AddDays(1) }
            Write-Log "  Set check-out: $($checkoutTime.ToString('HH:mm'))"
        } catch {
            Write-Log "  Gio khong hop le! Dung mac dinh."
            $checkoutTime = $defaultCheckout
        }
    } else {
        Write-Host ""
        Write-Host "  (Het 30s, dung mac dinh)"
        $checkoutTime = $defaultCheckout
        Write-Log "  Dung mac dinh: $($checkoutTime.ToString('HH:mm'))"
    }

    Write-Host ""
    Write-Host ("=" * 50)
    Write-Log "  Se check-out luc: $($checkoutTime.ToString('HH:mm'))"
    Write-Host "  KHONG DONG CUA SO NAY!"
    Write-Host ("=" * 50)
    Write-Host ""

    # Buoc 4: Doi den gio check-out
    while ($true) {
        $remaining = ($checkoutTime - (Get-Date)).TotalSeconds

        if ($remaining -le 0) {
            Write-Log "DEN GIO CHECK-OUT!"
            Start-Sleep -Seconds 2
            Invoke-CheckOut | Out-Null
            Write-Host ""
            Write-Log "=== HOAN TAT! ==="
            Read-Host "`nNhan Enter de dong"
            return
        }

        $hoursLeft = [Math]::Floor($remaining / 3600)
        $minsLeft = [Math]::Floor(($remaining % 3600) / 60)
        Write-Log "  Con ${hoursLeft}h ${minsLeft}p -> check-out luc $($checkoutTime.ToString('HH:mm'))"

        # Auto click "Dong y" neu popup phien het han xuat hien
        Invoke-JS "(function(){var btns=document.querySelectorAll('button');for(var i=0;i<btns.length;i++){var t=btns[i].textContent;if(t.indexOf('ồng')!==-1||t.indexOf('Dong')!==-1){btns[i].click();return'OK';}}return'NO';})()" | Out-Null

        if ($remaining -lt 60) { Start-Sleep -Seconds 10 }
        elseif ($remaining -lt 300) { Start-Sleep -Seconds 30 }
        else { Start-Sleep -Seconds 300 }
    }
}

# === RUN ===
try {
    Main
} catch {
    Write-Log "LOI: $_"
    Write-Host $_.ScriptStackTrace
    Read-Host "`nNhan Enter de dong"
}
