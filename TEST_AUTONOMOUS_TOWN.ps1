$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (!(Test-Path $Python)) {
    throw "Project virtual environment not found."
}

Write-Host "`n[1/4] Checking Python syntax..." -ForegroundColor Cyan
& $Python -m compileall -q backend
if ($LASTEXITCODE -ne 0) { throw "Python compilation failed." }

Write-Host "`n[2/4] Running CEO planning validation tests..." -ForegroundColor Cyan
& $Python -m pytest backend\tests\test_ceo_orchestration.py -q
if ($LASTEXITCODE -ne 0) { throw "CEO planning tests failed." }

Write-Host "`n[3/4] Running the complete backend regression suite..." -ForegroundColor Cyan
& $Python -m pytest backend\tests -q
if ($LASTEXITCODE -ne 0) { throw "Backend regression tests failed." }

Write-Host "`n[4/4] Checking scheduler integration..." -ForegroundColor Cyan
$Scheduler = Get-Content "backend\app\scheduler.py" -Raw
$Module = Test-Path "backend\app\ceo_orchestration.py"
$Hook = $Scheduler.Contains("run_ceo_planning_cycle")
$Report = $Scheduler.Contains("AI_MONEY_TOWN_CEO_INTERVAL_SECONDS")

if (!$Module -or !$Hook -or !$Report) {
    throw "CEO integration check failed."
}

Write-Host "`nALL LOCAL TESTS PASSED." -ForegroundColor Green
Write-Host "No cloud deployment was performed."
