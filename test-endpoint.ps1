$uri = "https://incognnitamoooddd-ai-procurement-negotiation-agent.hf.space/reset"
$headers = @{"Content-Type" = "application/json"}
$body = "{}"

try {
    $response = Invoke-WebRequest -Uri $uri -Method Post -Headers $headers -Body $body
    Write-Host "Status: $($response.StatusCode)"
    Write-Host "Body: $($response.Content)"
} catch {
    Write-Host "Error: $_"
    Write-Host "Status Code: $($_.Exception.Response.StatusCode.Value)"
}
