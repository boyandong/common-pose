<#
.SYNOPSIS
  Resumable parallel fetcher for the official Ninapro DB9 per-subject archives.

.DESCRIPTION
  The network here is ~450 kbit/s and shared with other work, so downloads must
  be (a) parallel, (b) resumable, (c) verifiable.  curl.exe already handles
  Range-based resume correctly via `-C -`, and measured 4-way parallelism gives
  ~75 KB/s aggregate versus ~13 KB/s single-stream.  PowerShell jobs give the
  parallelism without re-implementing HTTP.

  Every subject is downloaded to <Out>/s_<n>_angles.zip and only accepted when
  its byte length equals the Content-Length reported by the server.  A JSON
  manifest with size + sha256 + Last-Modified is written so the corpus stays
  auditable after the fact.

  NOTE ON ARGUMENT PARSING: this script is normally launched as
      powershell -File tools/fetch_db9.ps1 -Subjects 1-16;68-73 ...
  A comma inside a -File argument is consumed by PowerShell's array constructor,
  so SPLIT ON SEMICOLONS (commas are still accepted when the script is
  dot-sourced).  The subject list is echoed at startup so a mis-parse is
  immediately visible rather than silently downloading the wrong corpus.

.EXAMPLE
  powershell -File tools/fetch_db9.ps1 -Subjects '1-16;68-73' -Workers 4 -Out ../data/ninapro_db9/raw
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$Subjects,
  [Parameter(Mandatory = $true)][string]$Out,
  [int]$Workers = 4,
  [int]$MaxRounds = 40
)

$ErrorActionPreference = 'Stop'
$Base = 'https://ninapro.hevs.ch/files/DB9'

# Official subject -> source-database layout, transcribed from the DB9 page:
# subjects 1-27 come from DB1, 28-67 from DB2, 68-77 from DB5.
function Get-SourceDbName([int]$n) {
  if ($n -ge 1 -and $n -le 27) { 'DB1' }
  elseif ($n -ge 28 -and $n -le 67) { 'DB2' }
  elseif ($n -ge 68 -and $n -le 77) { 'DB5' }
  else { throw "subject $n is outside the official DB9 numbering (1-77)" }
}

function Expand-SubjectSpec([string]$spec) {
  $list = New-Object System.Collections.ArrayList
  foreach ($chunk in ($spec -split '[,;]')) {
    $c = $chunk.Trim()
    if ($c -eq '') { continue }
    if ($c -match '^(\d+)\s*-\s*(\d+)$') {
      foreach ($n in ([int]$Matches[1])..([int]$Matches[2])) { [void]$list.Add($n) }
    } elseif ($c -match '^\d+$') {
      [void]$list.Add([int]$c)
    } else {
      throw "unparsable subject token '$c'"
    }
  }
  return @($list | Sort-Object -Unique)
}

New-Item -ItemType Directory -Force -Path $Out | Out-Null
$subjects = @(Expand-SubjectSpec $Subjects)
if ($subjects.Count -eq 0) { throw "no subjects parsed from '$Subjects'" }
Write-Host "[fetch] parsed $($subjects.Count) subjects: $($subjects -join ',')"

# --- build the plan once: subject -> url + destination -----------------------
$plan = @()
foreach ($s in $subjects) {
  $db = Get-SourceDbName $s
  $plan += [pscustomobject]@{
    Subject = $s
    Db      = $db
    Url     = "$Base/$db/s_$($s)_angles.zip"
    Dest    = (Join-Path $Out "s_$($s)_angles.zip")
    Expect  = [int64]0
  }
}

# --- resolve expected sizes so completeness is checkable ---------------------
foreach ($p in $plan) {
  $len = $null
  foreach ($try in 1..5) {
    $h = & curl.exe -sSI --max-time 45 $p.Url 2>$null
    $m = ($h | Select-String -Pattern '^Content-Length:\s*(\d+)').Matches
    if ($m.Count -gt 0) { $len = [int64]$m[0].Groups[1].Value; break }
    Start-Sleep -Seconds 2
  }
  if ($null -ne $len) { $p.Expect = $len } else { Write-Host "[warn] HEAD failed for s_$($p.Subject)" }
}
$known = @($plan | Where-Object { $_.Expect -gt 0 })
$totalMb = [math]::Round((($known | Measure-Object -Property Expect -Sum).Sum) / 1MB, 1)
Write-Host "[fetch] $($known.Count)/$($plan.Count) sizes resolved; $totalMb MB total; $Workers workers"

$pending = @($known | ForEach-Object { $_.Subject })

for ($round = 1; $round -le $MaxRounds -and $pending.Count -gt 0; $round++) {
  Write-Host "[round $round] pending: $($pending -join ',')"
  $batch = @($pending | Select-Object -First $Workers)
  $jobs = @()
  foreach ($s in $batch) {
    $p = $plan | Where-Object { $_.Subject -eq $s }
    $jobs += Start-Job -ScriptBlock {
      param($url, $dest)
      for ($i = 1; $i -le 4; $i++) {
        & curl.exe -sS -C - --max-time 1800 --retry 3 --retry-delay 3 -o $dest $url 2>$null
        if ($LASTEXITCODE -eq 0) { return 0 }
        Start-Sleep -Seconds (2 * $i)
      }
      return 1
    } -ArgumentList $p.Url, $p.Dest
  }
  $jobs | Wait-Job | Out-Null
  $jobs | Remove-Job -Force
  foreach ($s in $batch) {
    $p = $plan | Where-Object { $_.Subject -eq $s }
    $have = if (Test-Path $p.Dest) { (Get-Item $p.Dest).Length } else { 0 }
    if ($have -eq $p.Expect) {
      $pending = @($pending | Where-Object { $_ -ne $s })
      Write-Host ("  [ok]    s_{0,-3} {1,10:N0} bytes" -f $s, $have)
    } else {
      Write-Host ("  [retry] s_{0,-3} {1,10:N0} / {2,10:N0}" -f $s, $have, $p.Expect)
    }
  }
}

# --- manifest ---------------------------------------------------------------
$files = [ordered]@{}
foreach ($p in $plan) {
  if (-not (Test-Path $p.Dest)) { continue }
  $item = Get-Item $p.Dest
  $files["s_$($p.Subject)"] = [ordered]@{
    subject        = $p.Subject
    source_db      = $p.Db
    url            = $p.Url
    path           = $item.FullName
    bytes          = $item.Length
    expected_bytes = $p.Expect
    complete       = ($p.Expect -gt 0 -and $item.Length -eq $p.Expect)
    sha256         = (Get-FileHash -Algorithm SHA256 -Path $p.Dest).Hash.ToLower()
    last_write     = $item.LastWriteTime.ToString('o')
  }
}
$manifest = [ordered]@{
  source        = 'https://ninapro.hevs.ch/instructions/DB9.html'
  paper         = 'Jarque-Bou, Atzori, Muller, Sci Data 7:12 (2020), doi:10.1038/s41597-019-0349-2'
  retrieved_utc = (Get-Date).ToUniversalTime().ToString('o')
  files         = $files
}
$manifestPath = Join-Path $Out 'manifest.json'
$manifest | ConvertTo-Json -Depth 6 | Set-Content -Path $manifestPath -Encoding UTF8
$ok = @($files.Values | Where-Object { $_.complete }).Count
Write-Host "[done] $ok/$($plan.Count) complete. manifest -> $manifestPath"
if ($ok -ne $plan.Count) { exit 1 }
