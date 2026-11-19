#Requires -Version 7.0
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [uri] $Gateway,
    [Parameter(Mandatory)] [string] $SshConfig,
    [Parameter(Mandatory)] [ValidatePattern('^[a-zA-Z0-9][a-zA-Z0-9_-]*$')] [string] $SshHost,
    [switch] $MigrateApprovedFlashProfile
)

$ErrorActionPreference = 'Stop'
if ($Gateway.Scheme -ne 'https' -or $Gateway.AbsolutePath -ne '/v1' -or
    $Gateway.UserInfo -or $Gateway.Query -or $Gateway.Fragment) {
    throw 'Expected the approved HTTPS gateway URL ending in /v1'
}
$root = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'FreeFirstGateway'
$codex = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.codex'
$cursor = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.cursor'
$profile = Join-Path $codex 'free-first-gateway.config.toml'
$oldFlash = Join-Path $codex 'gemini-gemini-3-8-flash.config.toml'
$cursorConfig = Join-Path $cursor 'mcp.json'
$marker = '# Managed by FreeFirstGateway'
if ((Test-Path -LiteralPath $profile) -and
    (Get-Content -LiteralPath $profile -TotalCount 1) -ne $marker) {
    throw 'A user-managed Free-First profile already exists'
}
if ($MigrateApprovedFlashProfile) {
    $prior = Get-Content -Raw -LiteralPath $oldFlash
    if ($prior -notmatch '(?m)^# Managed by FreeFirstGateway\r?$' -and
        ($prior -notmatch '(?m)^model\s*=\s*"gemini/gemini-3\.8-flash"\s*$' -or
         $prior -notmatch '(?m)^model_provider\s*=\s*"omniroute"\s*$')) {
        throw 'Legacy Flash profile does not match the approved migration'
    }
}
$config = Get-Content -Raw -LiteralPath $cursorConfig | ConvertFrom-Json -AsHashtable
if ($null -eq $config.mcpServers) { throw 'Cursor MCP configuration unavailable' }

Add-Type -AssemblyName System.Security.Cryptography.ProtectedData
$secrets = @{}
$ssh = @('-F', $SshConfig, '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=15', $SshHost)
foreach ($name in 'codex', 'cursor') {
    $key = & ssh.exe @ssh "cat /opt/9router-clean/client-keys/$name.key"
    if ($LASTEXITCODE -ne 0 -or $key -isnot [string] -or $key -notmatch '^\S+$') {
        throw "Cannot retrieve the scoped $name credential"
    }
    $headers = @{Authorization = "Bearer $key"}
    $model = 'free/gemini-3.8-flash'
    $catalog = Invoke-RestMethod -Uri "$($Gateway.AbsoluteUri)/models" -Headers $headers -MaximumRedirection 0 -TimeoutSec 15
    if ($catalog.data.Count -ne 1 -or $catalog.data[0].id -ne $model) {
        throw "Unexpected model catalog for $name"
    }
    $request = @{
        Uri = "$($Gateway.AbsoluteUri)/chat/completions"; Method = 'Post'; Headers = $headers
        ContentType = 'application/json'; MaximumRedirection = 0; TimeoutSec = 15; SkipHttpErrorCheck = $true
        Body = @{model = 'free/gemini-3.1-pro-preview'; messages = @(@{role = 'user'; content = 'policy probe'})} | ConvertTo-Json -Compress
    }
    $deny = Invoke-WebRequest @request
    if ($deny.StatusCode -ne 403) { throw "Forbidden model did not return 403 for $name" }
    $plain = [Text.Encoding]::UTF8.GetBytes($key)
    $protected = [Security.Cryptography.ProtectedData]::Protect(
        $plain, $null, [Security.Cryptography.DataProtectionScope]::CurrentUser
    )
    [Array]::Clear($plain, 0, $plain.Length)
    $secrets[$name] = [Convert]::ToBase64String($protected)
    Remove-Variable key,headers,request
    Write-Output "$name verified: one approved model and forbidden request HTTP 403"
}

function Set-ClientFile($path, $content) {
    $staged = $path + '.new'
    [IO.File]::WriteAllText($staged, $content)
    [IO.File]::Move($staged, $path, $true)
}

$backup = Join-Path $root ('backup-' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssffffZ'))
New-Item -ItemType Directory -Path $backup -Force | Out-Null
Copy-Item -LiteralPath $cursorConfig -Destination (Join-Path $backup 'cursor-mcp.json')
if (Test-Path -LiteralPath $profile) { Copy-Item -LiteralPath $profile -Destination $backup }
if ($MigrateApprovedFlashProfile) { Copy-Item -LiteralPath $oldFlash -Destination $backup }
foreach ($file in 'Start-FreeFirst.ps1', 'free-first-mcp.mjs', 'codex-transport.mjs') {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $file) -Destination $root
}
foreach ($name in 'codex', 'cursor') { Set-ClientFile (Join-Path $root "$name.dpapi") $secrets[$name] }
Set-ClientFile (Join-Path $root 'url.txt') $Gateway.AbsoluteUri
Set-ClientFile (Join-Path $root 'node.txt') (Get-Command node.exe -ErrorAction Stop).Source
Set-ClientFile (Join-Path $root 'codex.txt') (Get-Command codex.exe -ErrorAction Stop).Source

$windowsPs = (Get-Command powershell.exe -ErrorAction Stop).Source
$launcher = Join-Path $root 'Start-FreeFirst.ps1'
$stdio = @('-NoLogo', '-NoProfile', '-NonInteractive', '-File', $launcher, '-Client')
$codexArgs = ConvertTo-Json -InputObject ($stdio + 'codex') -Compress
$psToml = ConvertTo-Json -InputObject $windowsPs -Compress
$urlToml = ConvertTo-Json -InputObject $Gateway.AbsoluteUri -Compress
Set-ClientFile $profile @"
$marker
model_provider = "free_first_gateway"
model = "free/gemini-3.8-flash"
web_search = "disabled"

[model_providers.free_first_gateway]
name = "Free-First Gateway"
base_url = $urlToml
env_key = "FREE_FIRST_GATEWAY_KEY"
wire_api = "responses"
requires_openai_auth = false
supports_websockets = false
request_max_retries = 0
stream_max_retries = 0

[mcp_servers.free-first-gateway]
command = $psToml
args = $codexArgs
tool_timeout_sec = 135

[mcp_servers.omniroute-germany]
enabled = false

[mcp_servers.9router-candidate-combos]
enabled = false
"@
if ($MigrateApprovedFlashProfile) {
    Set-ClientFile $oldFlash (Get-Content -Raw -LiteralPath $profile)
    Write-Output 'Migrated the saved exact Flash profile to Free-First'
}
$runtime = @(
    '-c', 'web_search="disabled"',
    '-c', 'model_providers.free_first_gateway.name="Free-First Gateway"',
    '-c', 'model_providers.free_first_gateway.wire_api="responses"',
    '-c', 'model_providers.free_first_gateway.requires_openai_auth=false',
    '-c', 'model_providers.free_first_gateway.supports_websockets=false',
    '-c', 'model_providers.free_first_gateway.request_max_retries=0',
    '-c', 'model_providers.free_first_gateway.stream_max_retries=0',
    '-c', "mcp_servers.free-first-gateway.command=$psToml",
    '-c', "mcp_servers.free-first-gateway.args=$codexArgs",
    '-c', 'mcp_servers.free-first-gateway.tool_timeout_sec=135',
    '-c', 'mcp_servers.omniroute-germany.enabled=false',
    '-c', 'mcp_servers.9router-candidate-combos.enabled=false'
)
Set-ClientFile (Join-Path $root 'codex-runtime.json') (ConvertTo-Json -InputObject $runtime -Compress)
$config.mcpServers['free-first-gateway'] = @{command = $windowsPs; args = $stdio + 'cursor'}
Set-ClientFile $cursorConfig ($config | ConvertTo-Json -Depth 30)
Write-Output 'Installed the persistent Free-First Codex profile and Cursor MCP registration'
Write-Output "Configuration backup: $backup"
