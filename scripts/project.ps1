<#
.SYNOPSIS
    DueDil.Agent — start/stop helper for Windows (PowerShell 5.1+ and PowerShell 7+).

.DESCRIPTION
    Nothing in this project runs by itself: the compose services use `restart: "no"`, so
    they never come back after a reboot or a Docker Desktop restart. This script is the
    normal way to bring them up and take them down again, and it mirrors
    scripts/project.sh so the same commands work on Linux and on Windows.

.EXAMPLE
    .\scripts\project.ps1 start
    .\scripts\project.ps1 stop
    .\scripts\project.ps1 status
    .\scripts\project.ps1 logs
    .\scripts\project.ps1 --help

.NOTES
    If PowerShell refuses to run the script, allow it for the current session:
        Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Command = "help",

    [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
    [string[]]$Rest
)

$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectDir

$ComposeFile  = Join-Path $ProjectDir "docker-compose.yml"
$Image        = "duedil-agent:latest"
$Port         = if ($env:DUEDIL_PORT) { $env:DUEDIL_PORT } else { "8501" }

function Write-Say  { param([string]$Text) Write-Host "==> " -ForegroundColor Blue -NoNewline; Write-Host $Text -ForegroundColor White }
function Write-Ok   { param([string]$Text) Write-Host "  ok " -ForegroundColor Green -NoNewline; Write-Host $Text }
function Write-Warn { param([string]$Text) Write-Host "  !  " -ForegroundColor Yellow -NoNewline; Write-Host $Text }
function Write-Die  { param([string]$Text) Write-Host "  error " -ForegroundColor Red -NoNewline; Write-Host $Text; exit 1 }

function Invoke-Compose {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    & docker compose -f $ComposeFile @Args
    if ($LASTEXITCODE -ne 0) { throw "docker compose $($Args -join ' ') failed with exit code $LASTEXITCODE" }
}

function Assert-Docker {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Die "docker is not installed or not on PATH. Install Docker Desktop: https://www.docker.com/products/docker-desktop/"
    }
    & docker compose version *> $null
    if ($LASTEXITCODE -ne 0) { Write-Die "the docker compose plugin is missing (Docker Desktop ships it; make sure it is up to date)" }
    & docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Die "Docker is not responding. Start Docker Desktop from the Start menu and wait for the whale icon to stop animating."
    }
}

function Get-UiId {
    # Compose names containers after the (per-developer) project, so look the id up.
    $id = (& docker compose -f $ComposeFile ps -q ui 2>$null | Select-Object -First 1)
    if ($id) { return $id.Trim() }
    return ""
}

function Get-ProjectName {
    $line = (& docker compose -f $ComposeFile config 2>$null | Select-String -Pattern '^name:\s*(.+)$' | Select-Object -First 1)
    if ($line -and $line.Matches.Count -gt 0) { return $line.Matches[0].Groups[1].Value.Trim() }
    return "duedil-agent"
}

function Get-FreePort {
    param([int]$Start = 8501)
    for ($port = $Start; $port -lt 8600; $port++) {
        $inUse = (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue)
        if (-not $inUse) { return $port }
    }
    return $Start
}

function Get-Port {
    $mapping = (& docker compose -f $ComposeFile port ui 8501 2>$null | Select-Object -First 1)
    if ($mapping -and $mapping -match ":(\d+)\s*$") { return $Matches[1] }
    return $Port
}

function Wait-ForHealth {
    param([string]$PublishedPort)
    $deadline = (Get-Date).AddMinutes(3)
    Write-Host "  waiting for the app to become healthy" -NoNewline
    while ((Get-Date) -lt $deadline) {
        $id = Get-UiId
        $state = if ($id) { (& docker inspect -f "{{.State.Health.Status}}" $id 2>$null) } else { "missing" }
        switch ($state) {
            "healthy" {
                Write-Host ""
                Write-Ok "app is up: http://localhost:$PublishedPort"
                return
            }
            "unhealthy" {
                Write-Host ""
                Write-Die "the container reports unhealthy. Run: .\scripts\project.ps1 logs"
            }
        }
        Write-Host "." -NoNewline
        Start-Sleep -Seconds 3
    }
    Write-Host ""
    Write-Warn "still not healthy after 3 minutes — showing the last log lines"
    Invoke-Compose logs --tail 20 ui
}

function Start-Project {
    Assert-Docker
    Write-Say "Starting DueDil.Agent"
    Invoke-Compose up -d --build
    Wait-ForHealth (Get-Port)
    Write-Host "  Stop it later with: .\scripts\project.ps1 stop" -ForegroundColor DarkGray
}

function Stop-Project {
    Assert-Docker
    Write-Say "Stopping DueDil.Agent"
    Invoke-Compose down --remove-orphans
    Write-Ok "containers removed; generated memos stay in the '$(Get-ProjectName)_duedil-data' volume"
    Write-Host "  The port is free again — other projects on this machine are unaffected." -ForegroundColor DarkGray
}

function Show-Status {
    Assert-Docker
    $name = Get-ProjectName
    Write-Say "Instance $name"
    & docker ps -a --filter "label=com.docker.compose.project=$name" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    $id = Get-UiId
    if ($id) {
        Write-Say "Health"
        & docker inspect -f "  state={{.State.Status}} health={{if .State.Health}}{{.State.Health.Status}}{{else}}n/a{{end}} restart-policy={{.HostConfig.RestartPolicy.Name}}" $id
        Write-Host "  url=http://localhost:$(Get-Port)"
    }
    else {
        Write-Warn "the UI container does not exist: the project is stopped"
    }
    Write-Say "Auto-start settings"
    Write-Host "  Docker Desktop starts with Windows only if you enabled it in its settings."
    Write-Host "  This project's containers never start by themselves (restart policy: no)."
}

function Set-Instance {
    param([string]$Name, [string]$Port)
    $envFile = Join-Path $ProjectDir ".env"

    if (-not $Name) {
        $current = Get-ProjectName
        Write-Say "This checkout's instance"
        Write-Host "  compose project : $current"
        Write-Host "  host port       : $(Get-Port)"
        Write-Host "  url when running: http://localhost:$(Get-Port)"
        Write-Host "  Every developer on a shared server needs their own name and port:" -ForegroundColor DarkGray
        Write-Host "  .\scripts\project.ps1 instance auto   # derive both from your username" -ForegroundColor DarkGray
        return
    }

    if ($Name -eq "auto") {
        $suffix = ($env:USERNAME -replace '[^A-Za-z0-9-]', '').ToLower()
        $Name = "duedil-agent-$suffix"
        $Port = [string](Get-FreePort 8501)
    }
    else {
        $Name = ($Name -replace '[^A-Za-z0-9-]', '').ToLower()
        if (-not $Port) { $Port = [string](Get-FreePort 8501) }
    }

    if (-not $Name) { Write-Die "the instance name must contain letters or digits" }
    # Namespace the name: "alice" alone could collide with another compose project.
    if ($Name -notlike "duedil-agent*") { $Name = "duedil-agent-$Name" }
    if ($Port -notmatch '^\d+$') { Write-Die "the port must be a number, got '$Port'" }

    Write-Say "Configuring this checkout as $Name on port $Port"
    if (-not (Test-Path $envFile)) {
        Write-Warn "no .env yet — copy it first: Copy-Item env.example .env"
        "# Created by .\scripts\project.ps1 instance" | Set-Content -Path $envFile -Encoding utf8
    }
    $kept = Get-Content $envFile | Where-Object { $_ -notmatch '^(COMPOSE_PROJECT_NAME|DUEDIL_PORT)=' }
    $kept += ""
    $kept += "# --- dev instance: written by .\scripts\project.ps1 instance ---"
    $kept += "COMPOSE_PROJECT_NAME=$Name"
    $kept += "DUEDIL_PORT=$Port"
    Set-Content -Path $envFile -Value $kept -Encoding utf8
    Write-Ok "written to .env (kept out of git by .gitignore)"
    Write-Host "  Next: .\scripts\project.ps1 start -> http://localhost:$Port" -ForegroundColor DarkGray
}

function Show-Usage {
    Write-Host ""
    Write-Host "DueDil.Agent — container control" -ForegroundColor White
    Write-Host ""
    Write-Host "  .\scripts\project.ps1 start              " -NoNewline -ForegroundColor Cyan
    Write-Host "build if needed, start, wait until healthy"
    Write-Host "  .\scripts\project.ps1 stop               " -NoNewline -ForegroundColor Cyan
    Write-Host "stop and remove the containers (data kept)"
    Write-Host "  .\scripts\project.ps1 restart            " -NoNewline -ForegroundColor Cyan
    Write-Host "stop, then start"
    Write-Host "  .\scripts\project.ps1 status             " -NoNewline -ForegroundColor Cyan
    Write-Host "what is running, health, auto-start settings"
    Write-Host "  .\scripts\project.ps1 logs               " -NoNewline -ForegroundColor Cyan
    Write-Host "follow the application log"
    Write-Host ""
    Write-Host "  .\scripts\project.ps1 build                build the image"
    Write-Host "  .\scripts\project.ps1 rebuild              build without cache, then restart"
    Write-Host "  .\scripts\project.ps1 shell                shell inside the running container"
    Write-Host "  .\scripts\project.ps1 cli <deck> [url]     run the CLI once, in a throwaway container"
    Write-Host "  .\scripts\project.ps1 clean                remove containers, volumes and image"
    Write-Host ""
    Write-Host "  .\scripts\project.ps1 instance             show this checkout's compose name and port"
    Write-Host "  .\scripts\project.ps1 instance auto        derive both from your username (shared server)"
    Write-Host "  .\scripts\project.ps1 instance <name> [port]   set them explicitly"
    Write-Host ""
    Write-Host "The app is served at http://localhost:$Port while started."
    Write-Host "Nothing starts automatically — including after a reboot."
    Write-Host ""
}

switch ($Command.ToLower()) {
    "start"     { Start-Project }
    "stop"      { Stop-Project }
    "restart"   { Stop-Project; Start-Project }
    "status"    { Show-Status }
    { $_ -in "ps" } { Show-Status }
    "logs"      { Assert-Docker; Invoke-Compose logs -f --tail 80 ui }
    "build"     { Assert-Docker; Write-Say "Building $Image"; Invoke-Compose build --pull ui; Write-Ok "image built" }
    "rebuild"   { Assert-Docker; Write-Say "Rebuilding from scratch (no layer cache)"; Invoke-Compose build --no-cache --pull ui; Stop-Project; Start-Project }
    "shell"     { Assert-Docker; Write-Say "Interactive shell inside the app container"; Invoke-Compose exec ui bash }
    "cli"       {
        Assert-Docker
        if (-not $Rest -or $Rest.Count -eq 0) { Write-Die "usage: .\scripts\project.ps1 cli <deck.pdf> [url] [--out ...]" }
        Invoke-Compose run --rm cli @Rest
    }
    "instance"  { Assert-Docker; Set-Instance -Name $Rest[0] -Port $Rest[1] }
    "clean"     {
        Assert-Docker
        Write-Say "Removing this project's containers, volumes and image"
        Invoke-Compose down --volumes --remove-orphans
        & docker image rm $Image 2>$null
        Write-Ok "nothing of this project is left on the machine (the source tree is untouched)"
    }
    { $_ -in "help", "--help", "-h", "" } { Show-Usage }
    default     { Write-Die "unknown command '$Command' (try --help)" }
}
