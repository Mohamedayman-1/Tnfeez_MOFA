# Phase 4 API Testing Script - PowerShell Version
# Tests all Phase 4 REST API endpoints for User Segment Access & Abilities
#
# Prerequisites:
# 1. Server running: python manage.py runserver
# 2. Update $JWT_TOKEN variable with valid authentication token
#
# Usage: powershell -ExecutionPolicy Bypass -File test_phase4_api.ps1

# =============================================================================
# CONFIGURATION
# =============================================================================

$BASE_URL = "http://127.0.0.1:8000"
$JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzYyNzYxMzEzLCJpYXQiOjE3NjI3NTk1MTMsImp0aSI6IjA4ZTdkOTlmMzVkYzRiZWViMWI0NzhjODMwZTI2YjQwIiwidXNlcl9pZCI6NX0.OcpdB55b_fGLmSr8tTfxtTzHCFcgLahsMYuEEcCypyI"

$Headers = @{
    "Authorization" = "Bearer $JWT_TOKEN"
    "Content-Type" = "application/json"
}

# Test tracking
$TotalTests = 0
$PassedTests = 0
$FailedTests = 0
$TestResults = @()

function Log-Test {
    param(
        [string]$TestName,
        [bool]$Success,
        [string]$Details = ""
    )
    
    $script:TotalTests++
    
    if ($Success) {
        $script:PassedTests++
        $Status = "[PASS]"
        Write-Host "$Status Test $script:TotalTests`: $TestName" -ForegroundColor Green
    } else {
        $script:FailedTests++
        $Status = "[FAIL]"
        Write-Host "$Status Test $script:TotalTests`: $TestName" -ForegroundColor Red
    }
    
    if ($Details) {
        Write-Host "      $Details" -ForegroundColor Gray
    }
    
    $script:TestResults += @{
        TestNumber = $script:TotalTests
        TestName = $TestName
        Success = $Success
        Details = $Details
    }
}

function Print-Summary {
    Write-Host "`n$('=' * 80)" -ForegroundColor Cyan
    Write-Host "PHASE 4 API TEST SUMMARY" -ForegroundColor Cyan
    Write-Host "$('=' * 80)" -ForegroundColor Cyan
    Write-Host "Total Tests:   $TotalTests"
    $PassPercent = if ($TotalTests -gt 0) { [math]::Round(($PassedTests / $TotalTests) * 100, 1) } else { 0 }
    Write-Host "Passed:        $PassedTests ($PassPercent%)" -ForegroundColor Green
    $FailPercent = if ($TotalTests -gt 0) { [math]::Round(($FailedTests / $TotalTests) * 100, 1) } else { 0 }
    Write-Host "Failed:        $FailedTests ($FailPercent%)" -ForegroundColor $(if ($FailedTests -gt 0) { 'Red' } else { 'Gray' })
    Write-Host "$('=' * 80)" -ForegroundColor Cyan
    
    if ($FailedTests -gt 0) {
        Write-Host "`nFailed Tests:" -ForegroundColor Red
        foreach ($result in $TestResults) {
            if (-not $result.Success) {
                Write-Host "  - Test $($result.TestNumber): $($result.TestName)" -ForegroundColor Red
                if ($result.Details) {
                    Write-Host "    $($result.Details)" -ForegroundColor Gray
                }
            }
        }
    }
}

# =============================================================================
# MAIN TEST EXECUTION
# =============================================================================

Write-Host "$('=' * 80)" -ForegroundColor Cyan
Write-Host "PHASE 4 API TESTING: User Segment Access & Abilities" -ForegroundColor Cyan
Write-Host "$('=' * 80)" -ForegroundColor Cyan
Write-Host "`nStarted at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host "Base URL: $BASE_URL"
Write-Host "Token: $($JWT_TOKEN.Substring(0, [Math]::Min(20, $JWT_TOKEN.Length)))..."

# Get test user IDs from query params (will be set after first tests)
$TestUser1Id = 0
$TestUser2Id = 0

# =============================================================================
# USER SEGMENT ACCESS API TESTS
# =============================================================================

Write-Host "`n$('=' * 80)" -ForegroundColor Yellow
Write-Host "TESTING: User Segment Access APIs" -ForegroundColor Yellow
Write-Host "$('=' * 80)" -ForegroundColor Yellow

# Test 1: Grant access to Entity E001
Write-Host "`n[TEST 1] Grant user access to Entity E001..."
try {
    $Body = @{
        user_id = 1  # Will be updated with actual user ID
        segment_type_id = 1
        segment_code = "E001"
        access_level = "EDIT"
        notes = "Test access grant"
    } | ConvertTo-Json
    
    $Response = Invoke-RestMethod -Uri "$BASE_URL/api/auth/phase4/access/grant" `
        -Method Post -Headers $Headers -Body $Body -ErrorAction Stop
    
    if ($Response.success -and $Response.access) {
        $TestUser1Id = $Response.access.user_id
        Log-Test "Grant Access" $true "Access ID: $($Response.access.id), Level: $($Response.access.access_level)"
    } else {
        Log-Test "Grant Access" $false "Unexpected response"
    }
} catch {
    Log-Test "Grant Access" $false "Exception: $($_.Exception.Message)"
}

# Test 2: Check user has access
Write-Host "`n[TEST 2] Check user has access to Entity E001..."
try {
    $Body = @{
        user_id = $TestUser1Id
        segment_type_id = 1
        segment_code = "E001"
        required_level = "VIEW"
    } | ConvertTo-Json
    
    $Response = Invoke-RestMethod -Uri "$BASE_URL/api/auth/phase4/access/check" `
        -Method Post -Headers $Headers -Body $Body -ErrorAction Stop
    
    if ($Response.success -and $Response.has_access) {
        Log-Test "Check Access" $true "Has access: $($Response.has_access), Level: $($Response.access_level)"
    } else {
        Log-Test "Check Access" $false "Access check failed"
    }
} catch {
    Log-Test "Check Access" $false "Exception: $($_.Exception.Message)"
}

# Test 3: Bulk grant access
Write-Host "`n[TEST 3] Bulk grant access to multiple segments..."
try {
    $Body = @{
        user_id = $TestUser1Id
        accesses = @(
            @{
                segment_type_id = 2
                segment_code = "A100"
                access_level = "VIEW"
                notes = "Salaries view"
            },
            @{
                segment_type_id = 2
                segment_code = "A200"
                access_level = "EDIT"
                notes = "Equipment edit"
            },
            @{
                segment_type_id = 3
                segment_code = "P001"
                access_level = "APPROVE"
                notes = "Project approval"
            }
        )
    } | ConvertTo-Json -Depth 3
    
    $Response = Invoke-RestMethod -Uri "$BASE_URL/api/auth/phase4/access/bulk-grant" `
        -Method Post -Headers $Headers -Body $Body -ErrorAction Stop
    
    if ($Response.success -and $Response.granted -eq 3) {
        Log-Test "Bulk Grant Access" $true "Granted: $($Response.granted)/$($Response.total)"
    } else {
        Log-Test "Bulk Grant Access" $false "Expected 3 grants, got $($Response.granted)"
    }
} catch {
    Log-Test "Bulk Grant Access" $false "Exception: $($_.Exception.Message)"
}

# Test 4: List all accesses
Write-Host "`n[TEST 4] List user's all accesses..."
try {
    $Response = Invoke-RestMethod -Uri "$BASE_URL/api/auth/phase4/access/list?user_id=$TestUser1Id" `
        -Method Get -Headers $Headers -ErrorAction Stop
    
    if ($Response.success -and $Response.count -ge 4) {
        Log-Test "List Accesses" $true "Found $($Response.count) accesses"
    } else {
        Log-Test "List Accesses" $false "Expected >= 4 accesses, got $($Response.count)"
    }
} catch {
    Log-Test "List Accesses" $false "Exception: $($_.Exception.Message)"
}

# Test 5: Get user allowed segments
Write-Host "`n[TEST 5] Get user's allowed segments for Entity type..."
try {
    $Response = Invoke-RestMethod -Uri "$BASE_URL/api/auth/phase4/access/user-segments?user_id=$TestUser1Id&segment_type_id=1" `
        -Method Get -Headers $Headers -ErrorAction Stop
    
    if ($Response.success -and $Response.count -ge 1) {
        Log-Test "Get User Segments" $true "Found $($Response.count) segments"
    } else {
        Log-Test "Get User Segments" $false "Expected >= 1 segments, got $($Response.count)"
    }
} catch {
    Log-Test "Get User Segments" $false "Exception: $($_.Exception.Message)"
}

# Test 6: Grant access with children (hierarchical)
Write-Host "`n[TEST 6] Grant access to parent with children..."
try {
    $Body = @{
        user_id = 2  # Different user
        segment_type_id = 1
        segment_code = "E001"
        access_level = "APPROVE"
        apply_to_children = $true
        notes = "Department manager with hierarchy"
    } | ConvertTo-Json
    
    $Response = Invoke-RestMethod -Uri "$BASE_URL/api/auth/phase4/access/grant-with-children" `
        -Method Post -Headers $Headers -Body $Body -ErrorAction Stop
    
    $TestUser2Id = 2
    
    if ($Response.success -and $Response.children_granted -ge 3) {
        Log-Test "Grant With Children" $true "Total granted: $($Response.total_granted) (parent + $($Response.children_granted) children)"
    } else {
        Log-Test "Grant With Children" $false "Expected >= 3 children granted"
    }
} catch {
    Log-Test "Grant With Children" $false "Exception: $($_.Exception.Message)"
}

# Test 7: Hierarchical access check
Write-Host "`n[TEST 7] Check hierarchical access on child segment..."
try {
    $Body = @{
        user_id = $TestUser2Id
        segment_type_id = 1
        segment_code = "E001-A-1"
        required_level = "VIEW"
    } | ConvertTo-Json
    
    $Response = Invoke-RestMethod -Uri "$BASE_URL/api/auth/phase4/access/hierarchical-check" `
        -Method Post -Headers $Headers -Body $Body -ErrorAction Stop
    
    if ($Response.success -and $Response.has_access) {
        $InheritedFrom = if ($Response.inherited_from) { $Response.inherited_from } else { "direct" }
        Log-Test "Hierarchical Check" $true "Has access, inherited from: $InheritedFrom"
    } else {
        Log-Test "Hierarchical Check" $false "Access check failed"
    }
} catch {
    Log-Test "Hierarchical Check" $false "Exception: $($_.Exception.Message)"
}

# Test 8: Get effective access level
Write-Host "`n[TEST 8] Get effective access level..."
try {
    $Body = @{
        user_id = $TestUser2Id
        segment_type_id = 1
        segment_code = "E001-B"
    } | ConvertTo-Json
    
    $Response = Invoke-RestMethod -Uri "$BASE_URL/api/auth/phase4/access/effective-level" `
        -Method Post -Headers $Headers -Body $Body -ErrorAction Stop
    
    if ($Response.success -and $Response.access_level) {
        $Source = if ($Response.source_segment) { $Response.source_segment } else { "direct" }
        Log-Test "Get Effective Level" $true "Level: $($Response.access_level), Source: $Source"
    } else {
        Log-Test "Get Effective Level" $false "Unexpected result"
    }
} catch {
    Log-Test "Get Effective Level" $false "Exception: $($_.Exception.Message)"
}

# Test 9: Get segment users
Write-Host "`n[TEST 9] Get users with access to segment..."
try {
    $Response = Invoke-RestMethod -Uri "$BASE_URL/api/auth/phase4/access/segment-users?segment_type_id=1&segment_code=E001" `
        -Method Get -Headers $Headers -ErrorAction Stop
    
    if ($Response.success -and $Response.count -ge 2) {
        Log-Test "Get Segment Users" $true "Found $($Response.count) users"
    } else {
        Log-Test "Get Segment Users" $false "Expected >= 2 users, got $($Response.count)"
    }
} catch {
    Log-Test "Get Segment Users" $false "Exception: $($_.Exception.Message)"
}

# Test 10: Revoke access
Write-Host "`n[TEST 10] Revoke user access..."
try {
    $Body = @{
        user_id = $TestUser1Id
        segment_type_id = 2
        segment_code = "A100"
        access_level = "VIEW"
        soft_delete = $true
    } | ConvertTo-Json
    
    $Response = Invoke-RestMethod -Uri "$BASE_URL/api/auth/phase4/access/revoke" `
        -Method Post -Headers $Headers -Body $Body -ErrorAction Stop
    
    if ($Response.success -and $Response.revoked_count -ge 1) {
        Log-Test "Revoke Access" $true "Revoked $($Response.revoked_count) access(es)"
    } else {
        Log-Test "Revoke Access" $false "Unexpected result"
    }
} catch {
    Log-Test "Revoke Access" $false "Exception: $($_.Exception.Message)"
}

# =============================================================================
# USER SEGMENT ABILITY API TESTS
# =============================================================================

Write-Host "`n$('=' * 80)" -ForegroundColor Yellow
Write-Host "TESTING: User Segment Ability APIs" -ForegroundColor Yellow
Write-Host "$('=' * 80)" -ForegroundColor Yellow

# Test 11: Grant ability
Write-Host "`n[TEST 11] Grant user ability on segment combination..."
try {
    $Body = @{
        user_id = $TestUser1Id
        ability_type = "APPROVE"
        segment_combination = @{
            "1" = "E001"
            "2" = "A200"
        }
        notes = "Budget approval ability"
    } | ConvertTo-Json -Depth 3
    
    $Response = Invoke-RestMethod -Uri "$BASE_URL/api/auth/phase4/abilities/grant" `
        -Method Post -Headers $Headers -Body $Body -ErrorAction Stop
    
    if ($Response.success -and $Response.ability) {
        Log-Test "Grant Ability" $true "Ability ID: $($Response.ability.id), Type: $($Response.ability.ability_type)"
    } else {
        Log-Test "Grant Ability" $false "Unexpected response"
    }
} catch {
    Log-Test "Grant Ability" $false "Exception: $($_.Exception.Message)"
}

# Test 12: Check user has ability
Write-Host "`n[TEST 12] Check user has ability..."
try {
    $Body = @{
        user_id = $TestUser1Id
        ability_type = "APPROVE"
        segment_combination = @{
            "1" = "E001"
            "2" = "A200"
        }
    } | ConvertTo-Json -Depth 3
    
    $Response = Invoke-RestMethod -Uri "$BASE_URL/api/auth/phase4/abilities/check" `
        -Method Post -Headers $Headers -Body $Body -ErrorAction Stop
    
    if ($Response.success -and $Response.has_ability) {
        Log-Test "Check Ability" $true "Has ability: $($Response.has_ability)"
    } else {
        Log-Test "Check Ability" $false "Ability check failed"
    }
} catch {
    Log-Test "Check Ability" $false "Exception: $($_.Exception.Message)"
}

# Test 13: Bulk grant abilities
Write-Host "`n[TEST 13] Bulk grant abilities..."
try {
    $Body = @{
        user_id = $TestUser1Id
        abilities = @(
            @{
                ability_type = "EDIT"
                segment_combination = @{ "1" = "E002" }
                notes = "IT department edit"
            },
            @{
                ability_type = "TRANSFER"
                segment_combination = @{
                    "1" = "E001"
                    "3" = "P001"
                }
                notes = "Transfer between HR and Project"
            }
        )
    } | ConvertTo-Json -Depth 4
    
    $Response = Invoke-RestMethod -Uri "$BASE_URL/api/auth/phase4/abilities/bulk-grant" `
        -Method Post -Headers $Headers -Body $Body -ErrorAction Stop
    
    if ($Response.success -and $Response.granted -eq 2) {
        Log-Test "Bulk Grant Abilities" $true "Granted: $($Response.granted)/$($Response.total)"
    } else {
        Log-Test "Bulk Grant Abilities" $false "Expected 2 grants, got $($Response.granted)"
    }
} catch {
    Log-Test "Bulk Grant Abilities" $false "Exception: $($_.Exception.Message)"
}

# Test 14: List abilities
Write-Host "`n[TEST 14] List user's abilities..."
try {
    $Response = Invoke-RestMethod -Uri "$BASE_URL/api/auth/phase4/abilities/list?user_id=$TestUser1Id" `
        -Method Get -Headers $Headers -ErrorAction Stop
    
    if ($Response.success -and $Response.count -ge 3) {
        Log-Test "List Abilities" $true "Found $($Response.count) abilities"
    } else {
        Log-Test "List Abilities" $false "Expected >= 3 abilities, got $($Response.count)"
    }
} catch {
    Log-Test "List Abilities" $false "Exception: $($_.Exception.Message)"
}

# Test 15: Get user abilities with filter
Write-Host "`n[TEST 15] Get user abilities with filter..."
try {
    $Response = Invoke-RestMethod -Uri "$BASE_URL/api/auth/phase4/abilities/user-abilities?user_id=$TestUser1Id&ability_type=APPROVE" `
        -Method Get -Headers $Headers -ErrorAction Stop
    
    if ($Response.success -and $Response.count -ge 1) {
        Log-Test "Get User Abilities" $true "Found $($Response.count) APPROVE abilities"
    } else {
        Log-Test "Get User Abilities" $false "Expected >= 1 abilities, got $($Response.count)"
    }
} catch {
    Log-Test "Get User Abilities" $false "Exception: $($_.Exception.Message)"
}

# Test 16: Validate ability for operation
Write-Host "`n[TEST 16] Validate ability for operation..."
try {
    $Body = @{
        user_id = $TestUser1Id
        operation = "approve_transfer"
        segment_combination = @{
            "1" = "E001"
            "2" = "A200"
        }
    } | ConvertTo-Json -Depth 3
    
    $Response = Invoke-RestMethod -Uri "$BASE_URL/api/auth/phase4/abilities/validate-operation" `
        -Method Post -Headers $Headers -Body $Body -ErrorAction Stop
    
    if ($Response.success -and $Response.allowed) {
        Log-Test "Validate Operation" $true "Allowed: $($Response.allowed), Required: $($Response.required_ability)"
    } else {
        Log-Test "Validate Operation" $false "Validation failed"
    }
} catch {
    Log-Test "Validate Operation" $false "Exception: $($_.Exception.Message)"
}

# Test 17: Get users with ability
Write-Host "`n[TEST 17] Get users with specific ability..."
try {
    $Response = Invoke-RestMethod -Uri "$BASE_URL/api/auth/phase4/abilities/users-with-ability?ability_type=APPROVE" `
        -Method Get -Headers $Headers -ErrorAction Stop
    
    if ($Response.success -and $Response.count -ge 1) {
        Log-Test "Get Users With Ability" $true "Found $($Response.count) users with APPROVE"
    } else {
        Log-Test "Get Users With Ability" $false "Expected >= 1 users, got $($Response.count)"
    }
} catch {
    Log-Test "Get Users With Ability" $false "Exception: $($_.Exception.Message)"
}

# Test 18: Revoke ability
Write-Host "`n[TEST 18] Revoke user ability..."
try {
    $Body = @{
        user_id = $TestUser1Id
        ability_type = "EDIT"
        segment_combination = @{ "1" = "E002" }
        soft_delete = $true
    } | ConvertTo-Json -Depth 3
    
    $Response = Invoke-RestMethod -Uri "$BASE_URL/api/auth/phase4/abilities/revoke" `
        -Method Post -Headers $Headers -Body $Body -ErrorAction Stop
    
    if ($Response.success -and $Response.revoked_count -ge 1) {
        Log-Test "Revoke Ability" $true "Revoked $($Response.revoked_count) ability(ies)"
    } else {
        Log-Test "Revoke Ability" $false "Unexpected result"
    }
} catch {
    Log-Test "Revoke Ability" $false "Exception: $($_.Exception.Message)"
}

# =============================================================================
# FINAL SUMMARY
# =============================================================================

Print-Summary

Write-Host "`nCompleted at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host "`n$('=' * 80)" -ForegroundColor Cyan

# Exit with appropriate code
if ($FailedTests -gt 0) {
    exit 1
} else {
    exit 0
}
