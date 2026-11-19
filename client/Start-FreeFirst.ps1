[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('codex', 'cursor')]
    [string] $Client,
    [switch] $Codex,
    [switch] $AppServer,
    [string] $Prompt,
    [string] $ResumeSession,
    [ValidateSet('free-first-gateway', 'gemini-gemini-3-8-flash')]
    [string] $ProfileName = 'free-first-gateway'
)

$ErrorActionPreference = 'Stop'
$credential = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot "$Client.dpapi")
Add-Type -AssemblyName System.Security
$protected = [Convert]::FromBase64String($credential.Trim())
$plain = [Security.Cryptography.ProtectedData]::Unprotect(
    $protected, $null, [Security.Cryptography.DataProtectionScope]::CurrentUser
)
$env:FREE_FIRST_GATEWAY_KEY = [Text.Encoding]::UTF8.GetString($plain)
[Array]::Clear($plain, 0, $plain.Length)
$env:FREE_FIRST_GATEWAY_URL = (Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'url.txt')).Trim()
$node = (Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'node.txt')).Trim()
try {
    if ($Codex -or $AppServer) {
        if ($Client -ne 'codex') { throw 'The Codex profile requires its own credential' }
        $transport = Join-Path $PSScriptRoot 'codex-transport.mjs'
        if ($AppServer) {
            & $node $transport app-server
        } elseif ($ResumeSession) {
            & $node $transport cli $ProfileName exec --json --sandbox read-only resume --skip-git-repo-check $ResumeSession $Prompt
        } elseif ($Prompt) {
            & $node $transport cli $ProfileName exec --json --sandbox read-only --skip-git-repo-check $Prompt
        } else {
            & $node $transport cli $ProfileName
        }
    } else {
        & $node (Join-Path $PSScriptRoot 'free-first-mcp.mjs')
    }
    exit $LASTEXITCODE
} finally {
    Remove-Item Env:FREE_FIRST_GATEWAY_KEY -ErrorAction SilentlyContinue
    Remove-Item Env:FREE_FIRST_GATEWAY_URL -ErrorAction SilentlyContinue
}
