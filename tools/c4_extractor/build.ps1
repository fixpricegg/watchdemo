$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    $env:CGO_ENABLED = '0'
    $env:GOOS = 'windows'
    $env:GOARCH = 'amd64'
    go build -buildvcs=false -trimpath -ldflags='-s -w' -o bin/c4-extractor-windows-amd64.exe .
    if ($LASTEXITCODE -ne 0) { throw 'C4 extractor build failed' }
} finally {
    Pop-Location
}
