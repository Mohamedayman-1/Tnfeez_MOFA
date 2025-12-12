# Phase 3 API Testing Guide

## Prerequisites

```bash
# Set your access token
$token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo2MSwidXNlcm5hbWUiOiJQcm9kTWFuYWdlckB0bmZlZXouY29tIiwiZW1haWwiOiJQcm9kTWFuYWdlckB0bmZlZXouY29tIiwiZXhwIjoxNzM5NzgwNDU1fQ.T-xNTtN7-4dRvwlp91g82qO28OQ5JHJcXaT7QYrN3xo"

# Base URL
$baseUrl = "http://localhost:8000/api/accounts-entities/phase3"

# Headers
$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}
```

## 1. Envelope Management APIs

### Create Envelope
```powershell
$body = @{
    segment_combination = @{
        "1" = "E100"
        "2" = "A100"
    }
    envelope_amount = "150000.00"
    fiscal_year = "FY2026"
    description = "Q1 2026 Budget for HR-Personnel"
    is_active = $true
} | ConvertTo-Json

Invoke-RestMethod -Uri "$baseUrl/envelopes/" -Method POST -Headers $headers -Body $body
```

### List Envelopes
```powershell
# Get all envelopes
Invoke-RestMethod -Uri "$baseUrl/envelopes/" -Method GET -Headers $headers

# Filter by fiscal year
Invoke-RestMethod -Uri "$baseUrl/envelopes/?fiscal_year=FY2025" -Method GET -Headers $headers

# Filter by segment type
Invoke-RestMethod -Uri "$baseUrl/envelopes/?segment_type=1" -Method GET -Headers $headers
```

### Get Envelope Detail
```powershell
$envelopeId = 74  # Replace with actual envelope ID
Invoke-RestMethod -Uri "$baseUrl/envelopes/$envelopeId/" -Method GET -Headers $headers
```

### Update Envelope
```powershell
$envelopeId = 74
$body = @{
    envelope_amount = "120000.00"
    description = "Updated budget amount"
} | ConvertTo-Json

Invoke-RestMethod -Uri "$baseUrl/envelopes/$envelopeId/" -Method PUT -Headers $headers -Body $body
```

### Delete Envelope (Soft Delete)
```powershell
$envelopeId = 74
Invoke-RestMethod -Uri "$baseUrl/envelopes/$envelopeId/" -Method DELETE -Headers $headers
```

### Check Balance (with Hierarchy Support)
```powershell
# Test 1: Child with no envelope (should find parent)
$body = @{
    segment_combination = @{
        "1" = "E102"
    }
    required_amount = "5000.00"
    fiscal_year = "FY2025"
    use_hierarchy = $true
} | ConvertTo-Json

Invoke-RestMethod -Uri "$baseUrl/envelopes/check-balance/" -Method POST -Headers $headers -Body $body
```

**Expected Response**:
```json
{
    "available": true,
    "envelope_amount": "100000.00",
    "consumed_amount": "0.00",
    "remaining_balance": "100000.00",
    "sufficient": true,
    "envelope_source": "parent",
    "envelope_segment_combination": {"1": "E100"}
}
```

```powershell
# Test 2: Insufficient balance
$body = @{
    segment_combination = @{
        "1": "E101"
    }
    required_amount = "50000.00"
    fiscal_year = "FY2025"
    use_hierarchy = $false
} | ConvertTo-Json

Invoke-RestMethod -Uri "$baseUrl/envelopes/check-balance/" -Method POST -Headers $headers -Body $body
```

**Expected Response**:
```json
{
    "available": true,
    "envelope_amount": "10000.00",
    "consumed_amount": "0.00",
    "remaining_balance": "10000.00",
    "sufficient": false,
    "envelope_source": "exact",
    "envelope_segment_combination": {"1": "E101"}
}
```

### Get Envelope Summary
```powershell
$body = @{
    segment_combination = @{
        "1" = "E102"
        "2" = "A100"
    }
    fiscal_year = "FY2025"
    use_hierarchy = $true
} | ConvertTo-Json

Invoke-RestMethod -Uri "$baseUrl/envelopes/summary/" -Method POST -Headers $headers -Body $body
```

## 2. Mapping Management APIs

### Create Mapping
```powershell
$body = @{
    segment_type_id = 2  # Account type
    source_code = "A101"
    target_code = "A200"
    mapping_type = "STANDARD"
    description = "Map salaries to capital expenses"
    is_active = $true
} | ConvertTo-Json

Invoke-RestMethod -Uri "$baseUrl/mappings/" -Method POST -Headers $headers -Body $body
```

### List Mappings
```powershell
# Get all mappings
Invoke-RestMethod -Uri "$baseUrl/mappings/" -Method GET -Headers $headers

# Filter by segment type
Invoke-RestMethod -Uri "$baseUrl/mappings/?segment_type=2" -Method GET -Headers $headers

# Filter by source code
Invoke-RestMethod -Uri "$baseUrl/mappings/?source_code=A101" -Method GET -Headers $headers
```

### Get Mapping Detail
```powershell
$mappingId = 1
Invoke-RestMethod -Uri "$baseUrl/mappings/$mappingId/" -Method GET -Headers $headers
```

### Update Mapping
```powershell
$mappingId = 1
$body = @{
    mapping_type = "CONSOLIDATION"
    description = "Updated mapping type"
} | ConvertTo-Json

Invoke-RestMethod -Uri "$baseUrl/mappings/$mappingId/" -Method PUT -Headers $headers -Body $body
```

### Delete Mapping
```powershell
$mappingId = 1
Invoke-RestMethod -Uri "$baseUrl/mappings/$mappingId/" -Method DELETE -Headers $headers
```

### Mapping Lookup (3 Modes)

#### Mode 1: Forward Lookup (Source → Targets)
```powershell
$body = @{
    segment_type_id = 2
    source_code = "A101"
} | ConvertTo-Json

Invoke-RestMethod -Uri "$baseUrl/mappings/lookup/" -Method POST -Headers $headers -Body $body
```

**Expected Response**:
```json
{
    "mode": "forward",
    "source_code": "A101",
    "target_codes": ["A200"]
}
```

#### Mode 2: Reverse Lookup (Target → Sources)
```powershell
$body = @{
    segment_type_id = 2
    target_code = "A200"
} | ConvertTo-Json

Invoke-RestMethod -Uri "$baseUrl/mappings/lookup/" -Method POST -Headers $headers -Body $body
```

**Expected Response**:
```json
{
    "mode": "reverse",
    "target_code": "A200",
    "source_codes": ["A101", "A100"]
}
```

#### Mode 3: Apply Mapping to Combination
```powershell
$body = @{
    apply_to_combination = @{
        "1" = "E101"
        "2" = "A101"
    }
} | ConvertTo-Json

Invoke-RestMethod -Uri "$baseUrl/mappings/lookup/" -Method POST -Headers $headers -Body $body
```

**Expected Response**:
```json
{
    "mode": "apply",
    "original_combination": {"1": "E101", "2": "A101"},
    "mapped_combination": {"1": "E102", "2": "A200"}
}
```

## 3. Transfer Limit Management APIs

### Create Transfer Limit
```powershell
$body = @{
    segment_combination = @{
        "1" = "E100"
        "2" = "A100"
    }
    fiscal_year = "FY2025"
    max_transfers_as_source = 10
    max_transfers_as_target = 15
    allow_as_source = $true
    allow_as_target = $true
    description = "Transfer limits for HR-Personnel"
    is_active = $true
} | ConvertTo-Json

Invoke-RestMethod -Uri "$baseUrl/transfer-limits/" -Method POST -Headers $headers -Body $body
```

### List Transfer Limits
```powershell
# Get all limits
Invoke-RestMethod -Uri "$baseUrl/transfer-limits/" -Method GET -Headers $headers

# Filter by fiscal year
Invoke-RestMethod -Uri "$baseUrl/transfer-limits/?fiscal_year=FY2025" -Method GET -Headers $headers
```

### Get Transfer Limit Detail
```powershell
$limitId = 98
Invoke-RestMethod -Uri "$baseUrl/transfer-limits/$limitId/" -Method GET -Headers $headers
```

### Update Transfer Limit
```powershell
$limitId = 98
$body = @{
    max_transfers_as_source = 20
    description = "Increased source limit"
} | ConvertTo-Json

Invoke-RestMethod -Uri "$baseUrl/transfer-limits/$limitId/" -Method PUT -Headers $headers -Body $body
```

### Delete Transfer Limit
```powershell
$limitId = 98
Invoke-RestMethod -Uri "$baseUrl/transfer-limits/$limitId/" -Method DELETE -Headers $headers
```

### Validate Transfer
```powershell
# Test 1: Validate as source
$body = @{
    segment_combination = @{
        "1" = "E100"
        "2" = "A100"
    }
    direction = "source"
    fiscal_year = "FY2025"
} | ConvertTo-Json

Invoke-RestMethod -Uri "$baseUrl/transfer-limits/validate/" -Method POST -Headers $headers -Body $body
```

**Expected Response**:
```json
{
    "allowed": true,
    "reason": null,
    "current_source_count": 0,
    "max_source_count": 10,
    "current_target_count": 0,
    "max_target_count": 15
}
```

```powershell
# Test 2: Validate as target
$body = @{
    segment_combination = @{
        "1" = "E102"
    }
    direction = "target"
    fiscal_year = "FY2025"
} | ConvertTo-Json

Invoke-RestMethod -Uri "$baseUrl/transfer-limits/validate/" -Method POST -Headers $headers -Body $body
```

## 4. End-to-End Transfer Workflow Test

```powershell
# Step 1: Check source has sufficient balance
$checkBalance = @{
    segment_combination = @{
        "1" = "E101"
        "2" = "A101"
    }
    required_amount = "3000.00"
    fiscal_year = "FY2025"
    use_hierarchy = $true
} | ConvertTo-Json

$balanceResult = Invoke-RestMethod -Uri "$baseUrl/envelopes/check-balance/" -Method POST -Headers $headers -Body $checkBalance

Write-Host "Balance Check: $($balanceResult.sufficient)"

# Step 2: Validate source transfer permission
$validateSource = @{
    segment_combination = @{
        "1" = "E101"
        "2" = "A101"
    }
    direction = "source"
    fiscal_year = "FY2025"
} | ConvertTo-Json

$sourceResult = Invoke-RestMethod -Uri "$baseUrl/transfer-limits/validate/" -Method POST -Headers $headers -Body $validateSource

Write-Host "Source Allowed: $($sourceResult.allowed)"

# Step 3: Apply mapping to get target combination
$applyMapping = @{
    apply_to_combination = @{
        "1" = "E101"
        "2" = "A101"
    }
} | ConvertTo-Json

$mappingResult = Invoke-RestMethod -Uri "$baseUrl/mappings/lookup/" -Method POST -Headers $headers -Body $applyMapping

Write-Host "Mapped Target: $($mappingResult.mapped_combination | ConvertTo-Json)"

# Step 4: Validate target transfer permission
$validateTarget = @{
    segment_combination = $mappingResult.mapped_combination
    direction = "target"
    fiscal_year = "FY2025"
} | ConvertTo-Json

$targetResult = Invoke-RestMethod -Uri "$baseUrl/transfer-limits/validate/" -Method POST -Headers $headers -Body $validateTarget

Write-Host "Target Allowed: $($targetResult.allowed)"

# Step 5: Check target has envelope (may be inherited)
$checkTarget = @{
    segment_combination = $mappingResult.mapped_combination
    required_amount = "3000.00"
    fiscal_year = "FY2025"
    use_hierarchy = $true
} | ConvertTo-Json

$targetEnvelope = Invoke-RestMethod -Uri "$baseUrl/envelopes/check-balance/" -Method POST -Headers $headers -Body $checkTarget

Write-Host "Target Has Envelope: $($targetEnvelope.available)"

# Summary
Write-Host "`nTransfer Workflow Result:"
if ($balanceResult.sufficient -and $sourceResult.allowed -and $targetResult.allowed -and $targetEnvelope.available) {
    Write-Host "  [SUCCESS] Transfer can proceed!" -ForegroundColor Green
} else {
    Write-Host "  [BLOCKED] Transfer cannot proceed" -ForegroundColor Red
}
```

## Common Error Responses

### 400 Bad Request
```json
{
    "error": "Missing required field: segment_combination"
}
```

### 401 Unauthorized
```json
{
    "detail": "Authentication credentials were not provided."
}
```

### 404 Not Found
```json
{
    "error": "Envelope not found"
}
```

### 500 Internal Server Error
```json
{
    "error": "An error occurred: [detailed error message]"
}
```

## Testing Checklist

- [ ] Create envelope via API
- [ ] List envelopes with filters
- [ ] Get envelope detail with balance calculation
- [ ] Update envelope amount
- [ ] Delete envelope (soft delete)
- [ ] Check balance with hierarchy enabled
- [ ] Check balance with hierarchy disabled
- [ ] Get envelope summary with transparency
- [ ] Create segment mapping
- [ ] Forward mapping lookup
- [ ] Reverse mapping lookup
- [ ] Apply mapping to combination
- [ ] Create transfer limit
- [ ] Validate transfer as source
- [ ] Validate transfer as target
- [ ] End-to-end transfer workflow

---

**Last Updated**: 2025-01-09
**Status**: Ready for Testing
