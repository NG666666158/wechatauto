$stamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
$distDir = ".next-build-$stamp"
$artifactsDir = Join-Path $PSScriptRoot "..\build-artifacts"
$tsconfigPath = Join-Path $PSScriptRoot "..\tsconfig.json"
$originalTsconfig = Get-Content -Raw -Encoding utf8 $tsconfigPath

New-Item -ItemType Directory -Force -Path $artifactsDir | Out-Null
$env:NEXT_DIST_DIR = $distDir

Write-Host "[frontend-build] distDir=$distDir"

try {
  node .\node_modules\next\dist\bin\next build --webpack
  if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
  }
}
finally {
  Set-Content -Path $tsconfigPath -Value $originalTsconfig -Encoding utf8
}

Set-Content -Path (Join-Path $artifactsDir "last-build-dir.txt") -Value $distDir -Encoding utf8
