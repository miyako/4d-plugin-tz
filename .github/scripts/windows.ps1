param([Parameter(Mandatory=$true)][ValidateSet("clean", "collect")][string]$Phase)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$source = "TZ.4dbase/plugins/TZ.bundle/contents/windows64/TZ.4DX"
$destination = "test/Plugins/TZ.bundle/Contents/Windows64/TZ.4DX"
$root = [IO.Path]::GetFullPath((Get-Location).Path)

function Get-OptionalItem([string]$path) {
    try {
        Get-Item -Force -LiteralPath $path -ErrorAction Stop
    } catch [System.Management.Automation.ItemNotFoundException] {
        return $null
    }
}

function Assert-Safe([string]$path) {
    $full = [IO.Path]::GetFullPath((Join-Path $root $path))
    if (-not $full.StartsWith($root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::Ordinal)) {
        throw "Output escapes checkout: $path"
    }
    $ancestor = $full
    while ($ancestor -and $ancestor -ne $root) {
        $marker = Get-OptionalItem (Join-Path $ancestor ".git")
        if ([IO.Path]::GetFileName($ancestor) -eq ".git" -or
            $null -ne $marker) {
            throw "Nested Git output: $ancestor"
        }
        $item = Get-OptionalItem $ancestor
        if ($null -ne $item) {
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "Symlink/reparse output: $ancestor"
            }
        }
        $ancestor = [IO.Path]::GetDirectoryName($ancestor)
    }
}

Assert-Safe $source
Assert-Safe $destination
if ($Phase -eq "clean") {
    Assert-Safe "Objs/Release"
    if (Test-Path -LiteralPath "Objs/Release") {
        if (-not (Get-Item -Force -LiteralPath "Objs/Release").PSIsContainer) {
            throw "Expected intermediate directory"
        }
        foreach ($item in Get-ChildItem -Force -Recurse -LiteralPath "Objs/Release") {
            Assert-Safe $item.FullName
        }
    }
    foreach ($path in @($source, $destination)) {
        if ((Test-Path -LiteralPath $path) -and (Get-Item -Force -LiteralPath $path).PSIsContainer) {
            throw "Expected regular output leaf: $path"
        }
    }
    foreach ($path in @($source, $destination)) {
        if (Test-Path -LiteralPath $path) {
            Remove-Item -Force -LiteralPath $path
        }
    }
    if (Test-Path -LiteralPath "Objs/Release") {
        Remove-Item -Recurse -Force -LiteralPath "Objs/Release"
    }
} else {
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Missing exact fresh Windows output" }
    $item = Get-Item -Force -LiteralPath $source
    if ($item.Length -le 0) { throw "Empty Windows output" }
    $resolved = (Resolve-Path -LiteralPath $source).Path
    $expected = [IO.Path]::GetFullPath((Join-Path $root $source))
    $comparison = if ($IsWindows) { [StringComparison]::OrdinalIgnoreCase } else { [StringComparison]::Ordinal }
    if (-not $resolved.Equals($expected, $comparison)) { throw "Unexpected resolved Windows output" }
    if (Test-Path -LiteralPath $destination -PathType Container) { throw "Expected regular destination" }
    New-Item -ItemType Directory -Force -Path (Split-Path $destination) | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination -Force
    Assert-Safe $destination
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $source).Hash -ne
        (Get-FileHash -Algorithm SHA256 -LiteralPath $destination).Hash) {
        throw "Windows artifact copy differs"
    }
}
