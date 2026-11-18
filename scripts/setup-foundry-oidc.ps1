# One-time GitHub Actions OIDC identity for Microsoft Foundry.
# Requires Azure CLI login and RBAC role-assignment permission on Foundry.
# Run locally in PowerShell; no Git/GitHub CLI required.
$ErrorActionPreference = "Stop"
$repoOwner = "maciejbrasewicz"
$repoName = "cloudfide-agentic-data-engineering"
$ownerId = "49028274"
$repoId = "1462704606"
$resourceGroup = "daas-analytics"
$foundryAccount = "registry9-claude-resource"
$foundryProject = "registry9-claude"
$appName = "cloudfide-foundry-review-1462704606"
$foundryUserRole = "53ca6127-db72-4b80-b1b0-d745d6d5456d"

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    throw "Azure CLI (az) is not available. Install it and log in first."
}

# Select the subscribed scope that actually owns the existing Foundry resource.
$subscriptions = @(az account list --all --query "[].id" -o tsv)
if ($LASTEXITCODE -ne 0 -or $subscriptions.Count -eq 0) { throw "Azure CLI is not signed in." }
$accountScope = $null
$selectedSubscription = $null
foreach ($subscription in $subscriptions) {
    az account set --subscription $subscription 2>$null
    if ($LASTEXITCODE -ne 0) { continue }
    $scopeCandidate = "/subscriptions/$subscription/resourceGroups/$resourceGroup/providers/Microsoft.CognitiveServices/accounts/$foundryAccount"
    $result = az resource show --ids $scopeCandidate --query id -o tsv 2>$null
    if ($LASTEXITCODE -eq 0 -and $result) {
        $accountScope = $result.Trim()
        $selectedSubscription = $subscription
        break
    }
}
if (-not $accountScope) { throw "Foundry resource not found in accessible subscriptions. Check Azure login." }

$tenant = (az account show --query tenantId -o tsv).Trim()
$projectScope = "$accountScope/projects/$foundryProject"
$existing = @(az ad app list --display-name $appName --query "[].{id:id,appId:appId}" -o json | ConvertFrom-Json)
if ($existing.Count -ge 1) {
    $app = $existing[0]
} else {
    $app = (az ad app create --display-name $appName --sign-in-audience AzureADMyOrg -o json | ConvertFrom-Json)
    if ($LASTEXITCODE -ne 0) { throw "Failed to register Microsoft Entra application." }
}

$sp = az ad sp show --id $app.appId -o json 2>$null | ConvertFrom-Json
if (-not $sp -or $LASTEXITCODE -ne 0) {
    $sp = az ad sp create --id $app.appId -o json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw "Failed to create service principal." }
}

# New GitHub repos (created after July 2026) use immutable owner/repo IDs in OIDC sub.
$subject = "repo:$repoOwner@$ownerId/$repoName@$repoId:ref:refs/heads/main"
# Use braces in PowerShell string expansion to avoid ambiguity around @ and ':'.
$subject = "repo:${repoOwner}@${ownerId}/${repoName}@${repoId}:ref:refs/heads/main"
$credentialName = "github-main-immutable"
$existingCredentials = @(az ad app federated-credential list --id $app.id -o json | ConvertFrom-Json)
if (-not ($existingCredentials | Where-Object { $_.name -eq $credentialName })) {
    $body = @{
        name = $credentialName
        issuer = "https://token.actions.githubusercontent.com"
        subject = $subject
        audiences = @("api://AzureADTokenExchange")
    } | ConvertTo-Json -Depth 4
    $tempFile = Join-Path $env:TEMP "cloudfide-oidc.json"
    [System.IO.File]::WriteAllText($tempFile, $body, (New-Object System.Text.UTF8Encoding($false)))
    az ad app federated-credential create --id $app.id --parameters "@$tempFile" -o none
    if ($LASTEXITCODE -ne 0) { throw "Federated credential creation failed." }
    Remove-Item $tempFile -ErrorAction SilentlyContinue
}

# Scoped to this Foundry project: do not give subscription-wide Contributor.
$existingRole = @(az role assignment list --assignee-object-id $sp.id --scope $projectScope --role $foundryUserRole -o json | ConvertFrom-Json)
if ($existingRole.Count -eq 0) {
    az role assignment create --assignee-object-id $sp.id --assignee-principal-type ServicePrincipal --role $foundryUserRole --scope $projectScope -o none
    if ($LASTEXITCODE -ne 0) { throw "RBAC assignment failed. An Azure role-assignment administrator must grant Foundry User at the project." }
}

Write-Output ""
Write-Output "OIDC CONFIGURATION CREATED (non-secret identifiers):"
@{
    AZURE_CLIENT_ID = $app.appId
    AZURE_TENANT_ID = $tenant
    AZURE_SUBSCRIPTION_ID = $selectedSubscription
    OIDC_SUBJECT = $subject
    PROJECT_SCOPE = $projectScope
} | ConvertTo-Json -Depth 4
