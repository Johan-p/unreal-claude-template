<#
.SYNOPSIS
    PreToolUse guard: keeps each agent's file writes inside its declared lane.

.DESCRIPTION
    CLAUDE.md assigns every path an owner, but an agent's system prompt is
    advisory - nothing stops a Write. This hook makes the two lanes that matter
    structural:

        architect -> may only write specs under docs/architect/ (plus scratch)
        builder   -> may only write inside the Unreal project (minus VibeUE)
                     and scratch space

    Both lanes are ALLOW-LISTS. That is deliberate: a deny-list here was
    bypassable with a Win32 device prefix (\\?\C:\...), because GetFullPath
    passes those through verbatim so the path never StartsWith the denied root.
    With an allow-list, any path the guard cannot canonicalize falls outside the
    permitted root and is denied, so novel path-encoding tricks fail closed.

    No machine paths are hardcoded. The scaffold root comes from
    CLAUDE_PROJECT_DIR (falling back to this script's location), and the Unreal
    project directory is read from LOCAL.md at run time, so a machine move stays
    a one-file edit.

    Written in PowerShell so the hook needs no interpreter path of its own -
    this machine has no system Python, only the engine-bundled one.

.NOTES
    ASCII ONLY. PowerShell 5.1 reads .ps1 as ANSI when there is no BOM, so a
    stray em-dash or smart quote corrupts into a quote character and breaks
    parsing - and a hook that fails to parse fails OPEN, silently disabling the
    guard. Keep every character in this file 7-bit. Verify with:
        [System.Management.Automation.Language.Parser]::ParseFile(path,[ref]$null,[ref]$errs)

    Deny only. The hook never returns "allow", because an allow decision
    bypasses the normal permission flow; staying silent lets it apply as usual.
    Covers Write/Edit/NotebookEdit only - Bash redirects and MCP
    execute_python_code write outside this guard entirely.
#>

$ErrorActionPreference = 'Stop'

function Write-Deny {
    param([string]$Reason)
    $payload = @{
        hookSpecificOutput = @{
            hookEventName            = 'PreToolUse'
            permissionDecision       = 'deny'
            permissionDecisionReason = $Reason
        }
    }
    $payload | ConvertTo-Json -Depth 5 -Compress | Write-Output
    exit 0
}

function Get-CanonicalPath {
    param([string]$Path)
    # GetFullPath resolves '..', '.' and forward slashes, but passes Win32
    # extended-length and device prefixes through verbatim - so '\\?\C:\x'
    # never StartsWith 'C:\x'. Strip them before comparing.
    $Path = $Path -replace '^[\\/]{2}[?.][\\/]', ''
    $Path = $Path -replace '^UNC[\\/]', '\\'
    return [System.IO.Path]::GetFullPath($Path)
}

function Test-IsUnder {
    param([string]$Path, [string]$Root)
    if ([string]::IsNullOrWhiteSpace($Root)) { return $false }
    try {
        $full = Get-CanonicalPath $Path
        $base = (Get-CanonicalPath $Root).TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
    } catch { return $false }
    return $full.StartsWith($base, [StringComparison]::OrdinalIgnoreCase)
}

# --- read the hook payload -------------------------------------------------
try {
    $raw = [Console]::In.ReadToEnd()
    if ([string]::IsNullOrWhiteSpace($raw)) { exit 0 }
    $hook = $raw | ConvertFrom-Json
} catch {
    # A guard that cannot parse its input must not block real work.
    exit 0
}

$agent = $hook.agent_type
if ([string]::IsNullOrWhiteSpace($agent)) { exit 0 }   # not inside a subagent

$target = $hook.tool_input.file_path
if ([string]::IsNullOrWhiteSpace($target)) { $target = $hook.tool_input.notebook_path }
if ([string]::IsNullOrWhiteSpace($target)) { exit 0 }  # nothing path-shaped to check

# Relative paths resolve against the tool call's working directory. A path this
# malformed is not something the guard should die on - let the tool reject it.
try {
    if (-not [System.IO.Path]::IsPathRooted($target)) {
        $base = $hook.cwd
        if ([string]::IsNullOrWhiteSpace($base)) { $base = (Get-Location).Path }
        $target = Join-Path $base $target
    }
} catch {
    exit 0
}

# --- locate the two repos --------------------------------------------------
$scaffold = $env:CLAUDE_PROJECT_DIR
if ([string]::IsNullOrWhiteSpace($scaffold)) {
    $scaffold = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
}

$unrealDir = $null
$localMd = Join-Path $scaffold 'LOCAL.md'
if (Test-Path $localMd) {
    $match = Select-String -Path $localMd -Pattern '\*\*UnrealProjectDir\*\*[^`]*`([^`]+)`' |
             Select-Object -First 1
    if ($match) { $unrealDir = $match.Matches[0].Groups[1].Value.Trim() }
}

# Scratch/temp writes are always fine - they touch neither repo.
if (Test-IsUnder $target ([System.IO.Path]::GetTempPath())) { exit 0 }

# --- lane rules ------------------------------------------------------------
switch ($agent) {

    'architect' {
        $specs = Join-Path $scaffold 'docs\architect'
        if (-not (Test-IsUnder $target $specs)) {
            Write-Deny ("The architect designs and does not implement: it writes specs " +
                        "under docs/architect/ and nothing else. Blocked write to '$target'. " +
                        "Put the decision in the spec and let a builder execute it.")
        }
    }

    'builder' {
        if ($unrealDir) {
            $vibe = Join-Path $unrealDir 'Plugins\VibeUE'
            if (Test-IsUnder $target $vibe) {
                Write-Deny ("Plugins/VibeUE is a separate git repository (our fork) and is not " +
                            "edited as part of feature work. Blocked write to '$target'. " +
                            "Flag the needed plugin change to the maintainer instead.")
            }
            if (-not (Test-IsUnder $target $unrealDir)) {
                Write-Deny ("The builder writes inside the Unreal project and scratch space, " +
                            "nowhere else. The scaffold repo (docs, specs, slices, skills, " +
                            "agents) belongs to the main session. Blocked write to '$target'. " +
                            "Report the change in your final message and let the main session " +
                            "make it.")
            }
        }
        else {
            # LOCAL.md unreadable: the allow-list root is unknown, so fall back to
            # the one rule that still holds, and say so rather than weakening silently.
            if (Test-IsUnder $target $scaffold) {
                Write-Deny ("The scaffold repo belongs to the main session, not the builder. " +
                            "Blocked write to '$target'.")
            }
            $warn = @{ systemMessage = ("guard-agent-paths: LOCAL.md gave no UnrealProjectDir, " +
                       "so the builder guard is running degraded (scaffold-only deny). " +
                       "Run /setup-local-md to restore full enforcement.") }
            $warn | ConvertTo-Json -Compress | Write-Output
        }
    }
}

exit 0
