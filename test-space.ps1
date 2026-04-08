$uri = "https://incognnitamoooddd-ai-procurement-negotiation-agent.hf.space/health"
Write-Host "Testing $uri..."
try {
    $r = Invoke-WebRequest -Uri $uri -Method GET -TimeoutSec 10 -ErrorAction Stop
    Write-Host "Success:" $r.StatusCode
    Write-Host $r.Content
} catch {
    Write-Host "Status:" $_.Exception.Response.StatusCode.value__
    Write-Host "Message:" $_.Exception.Message
}
