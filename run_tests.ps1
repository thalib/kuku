# Run Tests Script
# Options: --all, --e2e, --unit

function Show-Help {
    Write-Host "Usage: .\run_tests.ps1 [option]" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Yellow
    Write-Host "  --all     Run all tests"
    Write-Host "  --e2e     Run only e2e tests"
    Write-Host "  --unit    Run all tests except e2e"
    Write-Host "  --help    Show this help message (default)"
}

$args_list = $args -join " "

switch -regex ($args_list) {
    "all"   { uv run pytest }
    "e2e"   { uv run pytest tests/e2e/ }
    "unit"  { uv run pytest --ignore=tests/e2e/ }
    default { Show-Help }
}
