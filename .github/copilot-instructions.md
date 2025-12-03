# AI Agent Instructions for Tnfeez MOFA Budget Transfer System

## System Overview

**Tnfeez** is a Django REST API for budget transfer management across organizational segments (Entity, Account, Project). The system has evolved from hardcoded 3-segment logic to **dynamic, configuration-driven architecture** supporting 2-30 segments per client.

### Core Architecture Stack
- **Framework**: Django 4.x + Django REST Framework
- **Database**: SQLite (dev) / Oracle (prod)
- **Async**: Celery + Redis (background tasks)
- **Notifications**: WebSocket (via `__NOTIFICATIONS_SETUP__/`)
- **Integration**: Oracle FBDI (Financial Business Documents Interface)

---

## Key Architectural Components

### 1. **Dynamic Segment Model** (Foundation)
**Files**: `account_and_entitys/models.py`, `account_and_entitys/managers/segment_manager.py`

The system uses three core models for dynamic segments:
```python
# XX_SegmentType: Metadata (how many segments, what names, required flags)
# XX_Segment: Actual values (codes like "12345", "67890")
# XX_TransactionSegment: Links transfers to segment values (many-to-many bridge)
```

**Key Pattern**: Segment data flows through:
1. User submits segments dict: `{"1": {"code": "12345"}, "2": {"code": "67890"}}`
2. Backend validates via `SegmentManager.validate_transaction_segments()`
3. Stored as `XX_TransactionSegment` records (one per segment type per transfer)
4. Retrieved as dict via `transfer.get_segments_dict()` → `{"entity": {...}, "account": {...}}`

### 2. **Transaction Transfer Model** (Business Logic)
**Files**: `transaction/models.py`, `transaction/views.py`, `transaction/serializers.py`

```python
xx_TransactionTransfer:
  - Legacy: cost_center_code, account_code, project_code (deprecated)
  - Financial: from_center, to_center, approved_budget, available_budget, encumbrance
  - Relationships: transaction_segments (FK to XX_TransactionSegment)
```

**Two supported formats**:
- **NEW SIMPLIFIED** (preferred): `segments: {"1": {"code": "12345"}}` (direction via from_center/to_center)
- **OLD FORMAT** (legacy): `cost_center_code`, `account_code`, `project_code` (hardcoded 3 segments)

### 3. **Manager Classes Pattern** (Business Logic Encapsulation)
Located in `account_and_entitys/managers/`:
- **SegmentManager**: Validates, caches segment config, handles hierarchies
- **EnvelopeBalanceManager**: Calculates budget consumption across segments
- **EnvelopeManager**: Legacy—maintained for backward compatibility
- **SegmentTransferLimitManager**: Permission rules for source/target combinations

**Key Principle**: All complex logic lives in manager classes, views remain thin.

### 4. **Oracle Integration** (FBDI Export)
**Files**: `oracle_fbdi_integration/`, `test_upload_fbdi/`

Flow: Transaction approved → Excel (GL_INTERFACE sheet) → CSV → ZIP → Oracle SOAP API

Critical: Segment codes MUST match Oracle chart of accounts exactly.

---

## Developer Workflow & Patterns

### Adding New Segments (Multi-Client Support)

**For existing client**: Edit `config/segments_config.json`, then:
```bash
python manage.py setup_client --config-file config/segments_config.json --overwrite
python manage.py migrate
```

**For new client**: 
```bash
python manage.py setup_client --interactive  # Wizard-driven setup
```

### Creating Transaction Transfers (API)

**Endpoint**: `POST /api/transfers/create/`

**NEW FORMAT** (use this):
```json
{
  "transaction": 123,
  "from_center": "10000.00",
  "to_center": "0.00",
  "reason": "Budget reduction",
  "segments": {
    "1": {"code": "12345"},
    "2": {"code": "67890"},
    "3": {"code": "98765"}
  }
}
```

**Direction Logic**: If `from_center > 0` → SOURCE transfer (taking funds). If `to_center > 0` → DESTINATION transfer (receiving funds). Use ONE direction only.

### Validation Pipeline (Critical)

Located in `transaction/views.py`:
1. `validate_transaction_dynamic()` - Checks required segments, amounts
2. `validate_transaction_transfer_dynamic()` - Checks PivotFund combinations, transfer permissions
3. `_get_mofa_cost2_available()` / `_get_total_budget()` - Budget envelope checks (MOFA-specific)

**Pattern**: Validation errors collected in list, returned with `is_valid` flag.

### Retrieving Transfers with Dynamic Segments

**Endpoint**: `GET /api/transfers/?transaction=123`

**Response includes**:
```json
{
  "summary": {
    "total_from": 50000,
    "total_to": 50000,
    "balanced": true
  },
  "transfers": [
    {
      "transfer_id": 1,
      "segments": {
        "1": {"segment_name": "Entity", "from_code": "100", "to_code": "101"},
        "2": {"segment_name": "Account", ...}
      },
      "validation_errors": [],
      "control_budgets": [...],
      "is_valid": true
    }
  ]
}
```

---

## Critical Integration Points

### 1. **Segment Validation vs Budget Balance**

Two separate concerns:
- **Segment validation** (`validate_transaction_dynamic`): Are segment codes valid and required?
- **Budget validation** (`_get_mofa_cost2_available`): Is there enough budget in envelope?

Both must pass for `is_valid: true`.

### 2. **Oracle Balance Reports** (`OracleBalanceReportManager`)

Called during transfer listing to populate `available_budget`, `encumbrance`, etc.

**Key logic** (in `TransactionTransferListView.get()`):
```python
# Build segment filters from transfer's XX_TransactionSegment records
segment_filters = {}
for trans_seg in transaction_segments:
    # Use FROM segments if source transfer, TO if destination
    segment_code = trans_seg.from_segment_value.code if is_source else trans_seg.to_segment_value.code
    segment_filters[segment_type_id] = segment_code

# Query Oracle balance
result = balance_manager.get_segments_fund(segment_filters)
```

### 3. **Celery Task Notifications**

**File**: `__NOTIFICATIONS_SETUP__/code/` (DO NOT COPY—import directly)

Usage: `from __NOTIFICATIONS_SETUP__.code.task_notifications import notify_user`

### 4. **Approval Workflow** (`approvals/models.py`)

Transfers linked to `ApprovalWorkflowInstance`. Status progression:
- `1` = Pending (not sent for approval)
- `2` = Submitted
- `3`/`4` = Approval levels
- `< 1` = Rejected

---

## Common Pitfalls & Solutions

| Problem | Cause | Solution |
|---------|-------|----------|
| Validation fails with "Required segment missing" | Segment not in database | Run `python manage.py setup_client` to register XX_SegmentType |
| Oracle FBDI upload fails | Segment codes don't match Oracle | Verify codes in XX_Segment match Oracle chart of accounts |
| `from_center > half_available` error | Transfer exceeds MOFA_COST_2 limit | Check `_get_mofa_cost2_available()` logic; MOFA-specific 50% rule |
| Segment hierarchy queries slow | Missing indexes | Add index: `DB INDEX on (segment_type_id, parent_code)` |
| "Duplicate transfer" error | Same segment combo already exists | Check `validate_transaction_dynamic()` for existing transfer logic |
| Segment dropdown empty in frontend | Configuration not loaded | Ensure `GET /api/segments/types/config/` returns segment types |

---

## Testing Strategy

### Unit Tests
- Segment validation: `account_and_entitys/tests/test_dynamic_segments.py`
- Manager logic: `account_and_entitys/managers/test_*.py`

### Integration Tests
- API endpoints: `transaction/tests/test_views.py`
- Run: `python manage.py test transaction`

### Manual Testing
1. Create budget transfer (Django admin)
2. Call `POST /api/transfers/create/` with segment data
3. Verify via `GET /api/transfers/?transaction=X`
4. Submit for approval: `POST /api/transfers/submit/`

---

## Code Style & Conventions

### Segment Data Representation
```python
# NEW SIMPLIFIED FORMAT (preferred for new code)
segments = {
    "1": {"code": "12345"},  # segment_id -> code
    "2": {"code": "67890"}
}

# OLD FORMAT (legacy, still supported)
segments = {
    "1": {"from_code": "100", "to_code": "101"},  # segment_id -> from/to codes
    "2": {"from_code": "200", "to_code": "201"}
}
```

### Manager Method Pattern
```python
@staticmethod
def validate_something(data):
    """Process data, return dict with 'valid' and 'errors' keys."""
    errors = []
    # ... validation logic
    return {'valid': len(errors) == 0, 'errors': errors}
```

### Serializer Pattern
```python
# Use TransactionTransferDynamicSerializer for segment details
# Use TransactionTransferSerializer for legacy format
# Both support the same API but different response structures
```

---

## Key Files Reference Map

| File | Purpose | Key Functions |
|------|---------|---|
| `account_and_entitys/managers/segment_manager.py` | Central segment logic | `validate_transaction_segments()`, `get_segment_config()` |
| `account_and_entitys/managers/envelope_balance_manager.py` | Budget calculations | `get_segments_fund()` |
| `transaction/views.py` | API endpoints | `TransactionTransferListView.get()`, `TransactionTransferCreateView.post()` |
| `transaction/serializers.py` | Response formatting | `TransactionTransferDynamicSerializer` |
| `account_and_entitys/models.py` | Data models | `XX_SegmentType`, `XX_Segment`, `XX_TransactionSegment` |
| `oracle_fbdi_integration/core/journal_manager.py` | FBDI generation | `create_journal_entry_data_dynamic()` |
| `__NOTIFICATIONS_SETUP__/code/` | WebSocket notifications | `notify_user()` (import, don't copy) |

---

## When to Reference Documentation

- **Architecture deep-dive**: `__CLIENT_SETUP_DOCS__/01_DYNAMIC_SEGMENTS_ARCHITECTURE.md`
- **API reference**: `__CLIENT_SETUP_DOCS__/PHASE_3_API_GUIDE.md`
- **Oracle integration**: `__CLIENT_SETUP_DOCS__/04_ORACLE_INTEGRATION_DEPLOYMENT.md`
- **Notification setup**: `__NOTIFICATIONS_SETUP__/ARCHITECTURE.md`
- **Visual flows**: `__CLIENT_SETUP_DOCS__/05_VISUAL_DIAGRAMS.md`

---

## User Segment Access Control (Phase 4)

Users can be assigned access to specific segments, and the segment listing API respects these assignments.

### Access Control Behavior

- **SuperAdmin users**: See ALL segments (can bypass filter with `bypass_access_filter=true`)
- **Admin/Regular users**: Only see segments they have been granted access to via `XX_UserSegmentAccess`
- **No access**: Users without any segment grants see an empty list

### Key Models
```python
XX_UserSegmentAccess:  # User-to-segment access grants
    - user: FK to xx_User
    - segment_type: FK to XX_SegmentType
    - segment: FK to XX_Segment
    - access_level: VIEW/EDIT/APPROVE/ADMIN
    - is_active: bool
```

### API Endpoints for User Segment Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/phase4/required-segments/types` | GET | Get all required segment types |
| `/api/auth/phase4/required-segments/user-status` | GET | Check user's segment access status |
| `/api/auth/phase4/required-segments/assign` | POST | Bulk assign segments to user |
| `/api/auth/phase4/required-segments/available` | GET | Get available segments for assignment |
| `/api/auth/phase4/my-segments` | GET | Get current user's own segment access |

### Assigning Segments to Users

**Bulk Assignment** (preferred for initial setup):
```json
POST /api/auth/phase4/required-segments/assign
{
    "user_id": 5,
    "assignments": {
        "1": ["E001", "E002"],     // Entity segment type
        "2": ["A100", "A200"],     // Account segment type  
        "3": ["P001"]              // Project segment type
    },
    "access_level": "VIEW",
    "validate_required": true,
    "notes": "Initial access setup"
}
```

**Single Grant**:
```json
POST /api/auth/phase4/access/grant
{
    "user_id": 5,
    "segment_type_id": 1,
    "segment_code": "E001",
    "access_level": "EDIT",
    "notes": "Department manager access"
}
```

### Required Segments

When `is_required=true` on `XX_SegmentType`, the system can validate that users have access to at least one segment of each required type:

```json
GET /api/auth/phase4/required-segments/user-status?user_id=5

Response:
{
    "all_required_segments_assigned": false,
    "missing_required_types": [
        {"segment_type_id": 2, "segment_type_name": "Account"}
    ]
}
```

### Segment List Filtering

The `SegmentListView` now includes access control:

```json
GET /api/account-entitys/segments/list?segment_type=1

Response (for non-superadmin):
{
    "data": [...],  // Only user's assigned segments
    "access_control": {
        "user_is_superadmin": false,
        "access_filter_applied": true,
        "user_allowed_segments_count": 3
    }
}
```

### Manager Class Usage

```python
from user_management.managers import UserSegmentAccessManager

# Grant access
result = UserSegmentAccessManager.grant_access(
    user=user,
    segment_type_id=1,
    segment_code='E001',
    access_level='EDIT',
    granted_by=admin_user
)

# Check access
check = UserSegmentAccessManager.check_user_has_access(
    user=user,
    segment_type_id=1,
    segment_code='E001',
    required_level='VIEW'
)

# Get user's allowed segments
allowed = UserSegmentAccessManager.get_user_allowed_segments(
    user=user,
    segment_type_id=1
)
```

---

## Migration from Hardcoded to Dynamic

**Never edit hardcoded fields directly** (`cost_center_code`, `account_code`, `project_code`). Instead:
1. Use dynamic segment API
2. Manager classes will auto-populate legacy fields if needed
3. Both formats coexist during transition period

**Clean the cache** after segment changes:
```python
from account_and_entitys.managers.segment_manager import SegmentManager
SegmentManager.clear_cache()
```

---

## Deployment Checklist

- [ ] All segment types registered (`XX_SegmentType`)
- [ ] Segment values loaded (`XX_Segment`)
- [ ] Oracle chart of accounts matches segment codes
- [ ] Approval workflow configured
- [ ] Redis running (for Celery tasks)
- [ ] Email backend configured (for notifications)
- [ ] Static files collected
- [ ] Database backups before migration

---

**Last Updated**: November 2025  
**For**: AI Coding Agents & Developers  
**Version**: 2.0 (Dynamic Architecture Era)
