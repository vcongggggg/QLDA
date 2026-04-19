param(
    [Parameter(Mandatory = $true)]
    [string]$PostgresDsn,

    [string]$OutputDir = "backups"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outFile = Join-Path $OutputDir "teamswork_$stamp.sql"

$env:PGPASSWORD = ""

# Uses pg_dump from local PostgreSQL client tools.
pg_dump --dbname="$PostgresDsn" --format=plain --no-owner --no-privileges --file="$outFile"

if ($LASTEXITCODE -ne 0) {
    throw "pg_dump failed with exit code $LASTEXITCODE"
}

Write-Host "Backup created: $outFile"
