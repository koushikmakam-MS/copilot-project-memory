#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Collects GitHub traffic metrics and appends to historical data.
  Generates docs/ADOPTION.md with trends and visualizations.

.DESCRIPTION
  - Fetches clones, views, referrers, and repo stats from GitHub API
  - Merges new data into metrics/traffic-history.json (deduplicates by date)
  - Generates docs/ADOPTION.md with weekly trends, cumulative totals, and ASCII charts

.EXAMPLE
  ./scripts/collect-metrics.ps1
  ./scripts/collect-metrics.ps1 -RepoOwner "myorg" -RepoName "myrepo"
#>

param(
    [string]$RepoOwner = "koushikmakam-MS",
    [string]$RepoName  = "copilot-project-memory"
)

$ErrorActionPreference = "Stop"
$repo = "$RepoOwner/$RepoName"
$rootDir = Split-Path -Parent $PSScriptRoot
$historyFile = Join-Path (Join-Path $rootDir "metrics") "traffic-history.json"
$adoptionFile = Join-Path (Join-Path $rootDir "docs") "ADOPTION.md"

# Ensure directories exist
New-Item -ItemType Directory -Path (Join-Path $rootDir "metrics") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $rootDir "docs") -Force | Out-Null

Write-Host "Collecting metrics for $repo..." -ForegroundColor Cyan

# --- Fetch data from GitHub API ---
function Invoke-GhApi($endpoint) {
    try {
        $json = gh api "repos/$repo/$endpoint" 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Failed to fetch $endpoint"
            return $null
        }
        return $json | ConvertFrom-Json
    } catch {
        Write-Warning "Failed to fetch $endpoint : $_"
        return $null
    }
}

$cloneData    = Invoke-GhApi "traffic/clones"
$viewData     = Invoke-GhApi "traffic/views"
$referrerData = Invoke-GhApi "traffic/popular/referrers"

# Repo stats endpoint needs no sub-path
try {
    $repoJson = gh api "repos/$repo" 2>$null
    $repoData = $repoJson | ConvertFrom-Json
} catch {
    $repoData = $null
}

# --- Load or initialize history ---
if (Test-Path $historyFile) {
    $history = Get-Content $historyFile -Raw | ConvertFrom-Json
} else {
    $history = [PSCustomObject]@{
        repo         = $repo
        last_updated = $null
        clones       = @()
        views        = @()
        referrers    = @()
        repo_stats   = @()
    }
}

$today = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$todayDate = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd")
$history.last_updated = $today

# --- Merge function: deduplicate by date, keep latest values ---
function Merge-DailyData($existing, $new, $timestampField) {
    $map = [ordered]@{}
    foreach ($entry in $existing) {
        $key = $entry.date
        $map[$key] = $entry
    }
    foreach ($entry in $new) {
        $ts = $entry.$timestampField
        $date = ([datetime]::Parse($ts)).ToString("yyyy-MM-dd")
        if ($entry.count -gt 0 -or -not $map.Contains($date)) {
            $map[$date] = [PSCustomObject]@{
                date    = $date
                count   = [int]$entry.count
                uniques = [int]$entry.uniques
            }
        }
    }
    return @($map.Values | Sort-Object date)
}

# Merge clones and views
if ($cloneData -and $cloneData.clones) {
    $history.clones = Merge-DailyData $history.clones $cloneData.clones "timestamp"
}
if ($viewData -and $viewData.views) {
    $history.views = Merge-DailyData $history.views $viewData.views "timestamp"
}

# Merge referrers (append with today's date, deduplicate by date+referrer)
if ($referrerData) {
    $existingRefs = @($history.referrers)
    foreach ($ref in $referrerData) {
        $existing = $existingRefs | Where-Object { $_.date -eq $todayDate -and $_.referrer -eq $ref.referrer }
        if (-not $existing) {
            $existingRefs += [PSCustomObject]@{
                date     = $todayDate
                referrer = $ref.referrer
                count    = [int]$ref.count
                uniques  = [int]$ref.uniques
            }
        }
    }
    $history.referrers = $existingRefs
}

# Append repo stats snapshot
if ($repoData) {
    $existingStats = @($history.repo_stats)
    $todayStat = $existingStats | Where-Object { $_.date -eq $todayDate }
    if (-not $todayStat) {
        $existingStats += [PSCustomObject]@{
            date     = $todayDate
            stars    = [int]$repoData.stargazers_count
            forks    = [int]$repoData.forks_count
            watchers = [int]$repoData.subscribers_count
        }
    }
    $history.repo_stats = $existingStats
}

# --- Save history ---
$history | ConvertTo-Json -Depth 10 | Set-Content $historyFile -Encoding UTF8
Write-Host "History saved to $historyFile" -ForegroundColor Green

# --- Generate ADOPTION.md ---
Write-Host "Generating adoption report..." -ForegroundColor Cyan

# Calculate weekly aggregates
function Get-WeeklyAggregates($dailyData) {
    $weeks = [ordered]@{}
    foreach ($entry in $dailyData) {
        $date = [datetime]::Parse($entry.date)
        # Week starts on Monday
        $weekStart = $date.AddDays(-([int]$date.DayOfWeek + 6) % 7)
        $weekKey = $weekStart.ToString("yyyy-MM-dd")
        if (-not $weeks.Contains($weekKey)) {
            $weeks[$weekKey] = [PSCustomObject]@{
                week_start = $weekKey
                count      = 0
                uniques    = 0
                days       = 0
            }
        }
        $weeks[$weekKey].count += $entry.count
        $weeks[$weekKey].uniques += $entry.uniques
        $weeks[$weekKey].days += 1
    }
    return @($weeks.Values)
}

$cloneWeeks = Get-WeeklyAggregates $history.clones
$viewWeeks  = Get-WeeklyAggregates $history.views

# Cumulative totals
$totalClones  = ($history.clones | Measure-Object -Property count -Sum).Sum
$totalUniqClones = 0
foreach ($w in $cloneWeeks) { $totalUniqClones += $w.uniques }
$totalViews   = ($history.views | Measure-Object -Property count -Sum).Sum
$totalUniqViews = 0
foreach ($w in $viewWeeks) { $totalUniqViews += $w.uniques }

# Latest repo stats
$latestStats = $history.repo_stats | Sort-Object date | Select-Object -Last 1

# ASCII bar chart helper
function Format-BarChart($data, $property, $maxWidth) {
    if (-not $maxWidth) { $maxWidth = 30 }
    $maxVal = ($data | Measure-Object -Property $property -Maximum).Maximum
    if ($maxVal -eq 0) { $maxVal = 1 }
    $lines = @()
    foreach ($entry in $data) {
        $val = $entry.$property
        $barLen = [math]::Ceiling(($val / $maxVal) * $maxWidth)
        if ($barLen -lt 0) { $barLen = 0 }
        $bar = "#" * $barLen
        $label = if ($entry.week_start) { $entry.week_start } else { $entry.date }
        $lines += "  $label |$bar $val"
    }
    return $lines -join "`n"
}

# Week-over-week trend
function Get-WoWTrend($weeks) {
    if ($weeks.Count -lt 2) { return "Not enough data yet" }
    $current = $weeks[-1]
    $previous = $weeks[-2]
    $cc = $current.count
    $pc = $previous.count
    if ($pc -eq 0) { return "New activity this week ($cc total)" }
    $change = [math]::Round((($cc - $pc) / $pc) * 100, 1)
    $sign = if ($change -gt 0) { "+" } else { "" }
    $dir = if ($change -gt 0) { "UP" } elseif ($change -lt 0) { "DOWN" } else { "FLAT" }
    return "${dir} ${sign}${change}% week-over-week ($pc -> $cc)"
}

# Top referrers (aggregate across all snapshots)
$refAgg = @{}
foreach ($ref in $history.referrers) {
    if (-not $refAgg.ContainsKey($ref.referrer)) {
        $refAgg[$ref.referrer] = [PSCustomObject]@{ referrer = $ref.referrer; count = 0; uniques = 0 }
    }
    $refAgg[$ref.referrer].count += $ref.count
    $refAgg[$ref.referrer].uniques += $ref.uniques
}
$topReferrers = @($refAgg.Values | Sort-Object count -Descending | Select-Object -First 10)

# Date range
$firstDate = ($history.clones | Sort-Object date | Select-Object -First 1).date
$lastDate  = ($history.clones | Sort-Object date | Select-Object -Last 1).date
$trackingDays = if ($firstDate -and $lastDate) {
    ([datetime]::Parse($lastDate) - [datetime]::Parse($firstDate)).Days + 1
} else { 0 }

# Build the markdown using string array (avoids here-string parse issues)
$cloneTrend = Get-WoWTrend $cloneWeeks
$viewTrend  = Get-WoWTrend $viewWeeks
$cloneChart = Format-BarChart $cloneWeeks "count" 35
$viewChart  = Format-BarChart $viewWeeks "count" 35

# Cumulative growth chart
$cumClones = 0
$cumLines = @()
foreach ($w in $cloneWeeks) {
    $cumClones += $w.count
    $cumLines += [PSCustomObject]@{ week_start = $w.week_start; count = $cumClones }
}
$cumChart = Format-BarChart $cumLines "count" 35

# Weekly breakdown table rows
$weeklyRows = ($cloneWeeks | ForEach-Object {
    $cw = $_
    $vw = $viewWeeks | Where-Object { $_.week_start -eq $cw.week_start }
    $vc = if ($vw) { $vw.count } else { 0 }
    $vu = if ($vw) { $vw.uniques } else { 0 }
    "| $($cw.week_start) | $($cw.count) | $($cw.uniques) | $vc | $vu |"
}) -join "`n"

# Referrer table rows
$refRows = ($topReferrers | ForEach-Object {
    "| $($_.referrer) | $($_.count) | $($_.uniques) |"
}) -join "`n"

# Daily detail rows (last 14 days)
$last14Clones = @($history.clones | Sort-Object date -Descending | Select-Object -First 14)
$last14Views  = @($history.views)
$dailyRows = ($last14Clones | Sort-Object date | ForEach-Object {
    $c = $_
    $v = $last14Views | Where-Object { $_.date -eq $c.date }
    $vc = if ($v) { $v.count } else { 0 }
    $vu = if ($v) { $v.uniques } else { 0 }
    "| $($c.date) | $($c.count) | $($c.uniques) | $vc | $vu |"
}) -join "`n"

# Adoption health signals
$healthVelocity = if ($cloneWeeks.Count -gt 0 -and $cloneWeeks[-1].count -gt 0) {
    "Active -- clones this week"
} else { "Stalled -- no clones this week" }

$healthDiscovery = if ($topReferrers.Count -gt 1) {
    "Multiple referrer sources"
} else { "Single source -- needs more visibility" }

$healthEngagement = if ($totalViews -gt 0 -and ($totalClones / [math]::Max($totalViews,1)) -gt 0.5) {
    "High clone-to-view ratio (people who find it, install it)"
} else { "Moderate -- some viewers don't clone" }

$healthRetention = if ($cloneWeeks.Count -ge 2 -and $cloneWeeks[-1].count -gt 0 -and $cloneWeeks[-2].count -gt 0) {
    "Multi-week activity"
} else { "Needs sustained engagement" }

# Recommendations
$recs = @()
if ($cloneWeeks.Count -ge 2 -and $cloneWeeks[-1].count -lt $cloneWeeks[-2].count) {
    $recs += "- **Re-engage**: Clone activity is declining. Consider a demo, blog post, or Teams announcement."
}
if ($latestStats.stars -lt 5) {
    $recs += "- **Visibility**: Ask early adopters to star the repo -- social proof drives discovery."
}
if ($latestStats.forks -eq 0) {
    $recs += "- **Contribution**: No forks yet. Highlight contribution opportunities (CONTRIBUTING.md)."
}
if ($topReferrers.Count -le 2) {
    $recs += "- **Distribution**: Share in more channels (Slack, email, wiki, onboarding docs)."
}
$recs += "- **Track active users**: Search org repos for ``copilot-project-memory`` exports to find active users."
$recsText = $recs -join "`n"

$stars = $latestStats.stars
$forks = $latestStats.forks

$md = @()
$md += "# Copilot Project Memory -- Adoption Metrics"
$md += ""
$md += "> Auto-generated by [collect-metrics.ps1](../scripts/collect-metrics.ps1) | Last updated: **$todayDate**"
$md += "> Tracking since: **$firstDate** ($trackingDays days)"
$md += ""
$md += "---"
$md += ""
$md += "## Key Numbers"
$md += ""
$md += "| Metric | Total | Trend |"
$md += "|--------|-------|-------|"
$md += "| **Git Clones** | $totalClones | $cloneTrend |"
$md += "| **Unique Cloners** | ~$totalUniqClones | Unique users who cloned |"
$md += "| **Page Views** | $totalViews | $viewTrend |"
$md += "| **Unique Visitors** | ~$totalUniqViews | Unique viewers |"
$md += "| **Stars** | $stars | |"
$md += "| **Forks** | $forks | |"
$md += ""
$md += "> **Unique cloners = approx install base.** Each clone likely = one person installing the tool."
$md += ""
$md += "---"
$md += ""
$md += "## Weekly Clone Trend"
$md += ""
$md += '```'
$md += $cloneChart
$md += '```'
$md += ""
$md += "### Weekly Breakdown"
$md += ""
$md += "| Week Starting | Clones | Unique | Views | Unique |"
$md += "|---------------|--------|--------|-------|--------|"
$md += $weeklyRows
$md += ""
$md += "---"
$md += ""
$md += "## Weekly Page View Trend"
$md += ""
$md += '```'
$md += $viewChart
$md += '```'
$md += ""
$md += "---"
$md += ""
$md += "## Top Referrers (How People Find Us)"
$md += ""
$md += "| Source | Views | Unique Visitors |"
$md += "|--------|-------|-----------------|"
$md += $refRows
$md += ""
$md += "---"
$md += ""
$md += "## Daily Detail (Last 14 Days)"
$md += ""
$md += "| Date | Clones | Unique | Views | Unique |"
$md += "|------|--------|--------|-------|--------|"
$md += $dailyRows
$md += ""
$md += "---"
$md += ""
$md += "## Cumulative Growth"
$md += ""
$md += '```'
$md += $cumChart
$md += '```'
$md += ""
$md += "---"
$md += ""
$md += "## Adoption Health"
$md += ""
$md += "| Signal | Status |"
$md += "|--------|--------|"
$md += "| **Install velocity** | $healthVelocity |"
$md += "| **Organic discovery** | $healthDiscovery |"
$md += "| **Engagement depth** | $healthEngagement |"
$md += "| **Retention signal** | $healthRetention |"
$md += ""
$md += "---"
$md += ""
$md += "## Recommendations"
$md += ""
$md += $recsText
$md += ""
$md += "---"
$md += ""
$md += "*Historical data: [metrics/traffic-history.json](../metrics/traffic-history.json) | Generated by [scripts/collect-metrics.ps1](../scripts/collect-metrics.ps1)*"

$md = $md -join "`n"

$md | Set-Content $adoptionFile -Encoding UTF8
Write-Host "Report saved to $adoptionFile" -ForegroundColor Green

# Summary output
Write-Host ""
Write-Host "  Adoption Summary" -ForegroundColor Cyan
Write-Host "  ===================" -ForegroundColor Cyan
Write-Host "  Total Clones:    $totalClones `($totalUniqClones unique`)" -ForegroundColor White
Write-Host "  Total Views:     $totalViews `($totalUniqViews unique`)" -ForegroundColor White
Write-Host "  Stars:           $stars" -ForegroundColor White
Write-Host "  Forks:           $forks" -ForegroundColor White
Write-Host "  Tracking Since:  $firstDate `($trackingDays days`)" -ForegroundColor White
Write-Host ""
