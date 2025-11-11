# Legacy to Dynamic Segment Migration Plan

## Overview
This document outlines the complete migration plan from legacy hardcoded segment models to the new dynamic segment system. Each task is analyzed for backend usage patterns and data relationships.

---

## Task Breakdown

### ✅ **TASK 1: Segment Type Configuration (XX_SEGMENT_TYPE_XX)**
**Priority**: CRITICAL - Must be done first (foundation for all other tasks)

**Legacy Source**: None (new configuration based on existing Entity, Account, Project usage)

**Analysis**:
- **Backend Usage**: Core configuration table referenced by ALL dynamic models
- **Fields to Create**:
  - segment_id: 1 (Entity), 2 (Account), 3 (Project)
  - segment_name: Display names
  - segment_type: Technical identifiers (cost_center, account, project)
  - oracle_segment_number: Maps to SEGMENT1, SEGMENT2, SEGMENT3
  - is_required: All three are required = True
  - has_hierarchy: Entity and Account have parent relationships = True
  - max_depth: 10 for hierarchical types
  - is_active: True

**Action**: Create 3 XX_SegmentType records manually or via script

**Dependencies**: None

**Impact**: Foundation for all other migrations

---

### ✅ **TASK 2: Segment Master Data (XX_SEGMENT_XX)**
**Priority**: CRITICAL - Required before any transaction/user data

**Legacy Sources**:
1. **XX_ACCOUNT_XX** → XX_Segment (segment_type_id=2)
2. **XX_ENTITY_XX** → XX_Segment (segment_type_id=1)
3. **XX_PROJECT_XX** → XX_Segment (segment_type_id=3)

**Field Mapping**:

**From XX_ACCOUNT_XX**:
```python
XX_Account.id → XX_Segment.legacy_id
XX_Account.account → XX_Segment.code
XX_Account.alias_default → XX_Segment.alias
XX_Account.parent → XX_Segment.parent_code (lookup to get parent XX_Segment)
segment_type_id = 2 (Account)
```

**From XX_ENTITY_XX**:
```python
XX_Entity.id → XX_Segment.legacy_id
XX_Entity.entity → XX_Segment.code
XX_Entity.alias_default → XX_Segment.alias
XX_Entity.parent → XX_Segment.parent_code
segment_type_id = 1 (Entity/Cost Center)
```

**From XX_PROJECT_XX**:
```python
XX_Project.id → XX_Segment.legacy_id
XX_Project.project → XX_Segment.code
XX_Project.alias_default → XX_Segment.alias
XX_Project.parent → XX_Segment.parent_code
segment_type_id = 3 (Project)
```

**Backend Usage Analysis**:
- **Code field**: Used in all queries, filters, displays
- **Alias field**: Used for user-friendly names in UI
- **Parent relationship**: Used for hierarchical queries, rollups
- **is_active**: Controls visibility in dropdowns, filters

**Validation Rules**:
- Code must be unique within segment_type
- Parent must exist in same segment_type (if specified)
- No circular parent references

**Estimated Records**: 
- Entities: ~100-500
- Accounts: ~1000-5000
- Projects: ~50-200

---

### ✅ **TASK 3: Segment Mappings (XX_SEGMENT_MAPPING_XX)**
**Priority**: HIGH - Required for transfer validation

**Legacy Sources**:
1. **XX_ACCOUNT_MAPPING__elies_XX** → Account mappings
2. **XX_ENTITY_MAPPING__elies_XX** → Entity mappings
3. **XX_ACCOUNT_MAPPING_LEGACY_XX** → Additional account mappings

**Field Mapping**:

**From XX_ACCOUNT_MAPPING__elies_XX**:
```python
source_account (code) → lookup XX_Segment where segment_type_id=2, code=source_account
  → from_segment_id
target_account (code) → lookup XX_Segment where segment_type_id=2, code=target_account
  → to_segment_id
is_active → is_active
```

**From XX_ENTITY_MAPPING__elies_XX**:
```python
source_entity → lookup XX_Segment (segment_type_id=1) → from_segment_id
target_entity → lookup XX_Segment (segment_type_id=1) → to_segment_id
is_active → is_active
```

**Backend Usage Analysis**:
- **Where Used**: Transaction validation during transfer creation
- **Logic**: Checks if from_segment can transfer to to_segment
- **Views**: `transaction/views.py` - validation before save
- **Queries**: `XX_SegmentMapping.objects.filter(from_segment=..., to_segment=..., is_active=True)`

**Business Rules**:
- Unidirectional: A→B doesn't imply B→A
- Type-specific: Entity mappings separate from Account mappings
- Active flag controls current validity

**Estimated Records**: ~500-2000 mappings

---

### ✅ **TASK 4: Transaction Segments (XX_TRANSACTION_SEGMENT_XX)**
**Priority**: CRITICAL - Core business data

**Legacy Source**: **XX_TRANSACTION_TRANSFER_XX**

**Field Mapping**:
```python
For each xx_TransactionTransfer record, create 3 XX_TransactionSegment records:

1. Entity Segment:
   transaction_transfer_id = transfer.transfer_id
   segment_type_id = 1 (Entity)
   segment_value_id = lookup XX_Segment where segment_type_id=1, code=transfer.cost_center_code
   from_segment_value_id = same as segment_value_id
   to_segment_value_id = same as segment_value_id (for transfers within same entity)
   
2. Account Segment:
   transaction_transfer_id = transfer.transfer_id
   segment_type_id = 2 (Account)
   segment_value_id = lookup XX_Segment where segment_type_id=2, code=transfer.account_code
   from_segment_value_id = same
   to_segment_value_id = same
   
3. Project Segment:
   transaction_transfer_id = transfer.transfer_id
   segment_type_id = 3 (Project)
   segment_value_id = lookup XX_Segment where segment_type_id=3, code=transfer.project_code
   from_segment_value_id = same
   to_segment_value_id = same
```

**Backend Usage Analysis**:
- **Critical Path**: Transaction display, editing, approval workflows
- **Views Used**:
  - `transaction/views.py::TransactionTransferListView`
  - `transaction/views.py::TransactionTransferDetailView`
  - Budget transfer serializers
- **Query Patterns**:
  ```python
  transfer.transaction_segments.all()
  transfer.transaction_segments.filter(segment_type_id=1)
  transfer.transaction_segments.select_related('segment_type', 'from_segment_value', 'to_segment_value')
  ```

**Special Cases**:
- **Null codes**: Some transfers may have NULL project_code → skip Project segment
- **FROM/TO logic**: For actual transfers, from_segment_value ≠ to_segment_value
- **segment_value**: Currently required NOT NULL → use from_segment_value as default

**Data Volume**: 3 records × number of transactions (could be 10,000s)

---

### ✅ **TASK 5: Segment Transfer Limits (XX_SEGMENT_TRANSFER_LIMIT_XX)**
**Priority**: HIGH - Required for transfer validation

**Legacy Source**: **XX_ACCOUNT_ENTITY_LIMIT_XX**

**Field Mapping**:
```python
For each XX_ACCOUNT_ENTITY_LIMIT record:

segment_combination (JSON) = {
    "1": entity_id,  # Entity segment type
    "2": account_id,  # Account segment type
    "3": project_id  # Project segment type (if not NULL)
}

is_transfer_allowed_as_source = (is_transer_allowed_for_source == "True" or "Yes")
is_transfer_allowed_as_target = (is_transer_allowed_for_target == "True" or "Yes")
is_transfer_allowed = (is_transer_allowed == "True" or "Yes")
source_usage_count = source_count (default 0)
target_usage_count = target_count (default 0)
```

**Backend Usage Analysis**:
- **Where Used**: Transfer validation before approval
- **Logic**: Checks if segment combination is allowed as source/target
- **Views**: `transaction/views.py` - validate before creating transfer
- **Query Pattern**:
  ```python
  XX_SegmentTransferLimit.objects.filter(
      segment_combination={'1': 'E001', '2': 'A100', '3': 'P001'}
  ).first()
  ```

**Business Rules**:
- Combination must exist to allow transfer
- Separate flags for source vs target
- Usage counts track historical activity
- Unique constraint on segment_combination JSON

**Data Volume**: ~1000-5000 combinations

---

### ✅ **TASK 6: Segment Envelopes (XX_SEGMENT_ENVELOPE_XX)**
**Priority**: MEDIUM - Budget limit tracking

**Legacy Source**: **XX_PROJECT_ENVELOPE_XX** (Project_Envelope model)

**Field Mapping**:
```python
For each Project_Envelope record:

segment_type_id = 3 (Project)
segment_value_id = lookup XX_Segment where segment_type_id=3, code=project_envelope.project
envelope_amount = project_envelope.envelope
period_name = "Sep-25" (default - adjust based on business logic)
is_active = True
```

**Backend Usage Analysis**:
- **Where Used**: Budget ceiling validation
- **Logic**: Prevents project budgets from exceeding envelope limit
- **Views**: Dashboard, budget approval workflows
- **Query**: `XX_SegmentEnvelope.objects.filter(segment_value__code='P001', is_active=True)`

**Business Rules**:
- One envelope per segment per period
- Envelope > sum of all budgets assigned to that segment
- Used in budget allocation validation

**Future Expansion**: Can add envelopes for Entity and Account segments

**Data Volume**: ~50-200 project envelopes

---

### ✅ **TASK 7: Balance Report Segments (XX_BALANCE_REPORT_SEGMENT_XX + XX_DYNAMIC_BALANCE_REPORT_XX)**
**Priority**: MEDIUM - Historical reporting data

**Legacy Source**: **XX_BALANCE_REPORT_XX**

**Migration Strategy**: Two options:

**Option A: Preserve Legacy Table (Recommended for Phase 1)**
- Keep XX_BALANCE_REPORT_XX with segment1/2/3 columns
- NEW reports use XX_DYNAMIC_BALANCE_REPORT_XX + XX_BALANCE_REPORT_SEGMENT_XX
- Gradual migration as reports are regenerated

**Option B: Full Migration (Recommended for Phase 2)**
```python
For each XX_BALANCE_REPORT record:

1. Create XX_DYNAMIC_BALANCE_REPORT:
   control_budget_name = original.control_budget_name
   ledger_name = original.ledger_name
   as_of_period = original.as_of_period
   encumbrance_ytd = original.encumbrance_ytd
   other_ytd = original.other_ytd
   actual_ytd = original.actual_ytd
   funds_available_asof = original.funds_available_asof
   budget_ytd = original.budget_ytd
   
2. Create 3 XX_BALANCE_REPORT_SEGMENT records:
   
   Entity Segment:
   balance_report_id = new_report.id
   segment_type_id = 1
   segment_value_id = lookup XX_Segment(segment_type_id=1, code=original.segment1)
   segment_code = original.segment1 (denormalized)
   oracle_field_name = "SEGMENT1"
   oracle_field_number = 1
   
   Account Segment:
   balance_report_id = new_report.id
   segment_type_id = 2
   segment_value_id = lookup XX_Segment(segment_type_id=2, code=original.segment2)
   segment_code = original.segment2
   oracle_field_name = "SEGMENT2"
   oracle_field_number = 2
   
   Project Segment:
   balance_report_id = new_report.id
   segment_type_id = 3
   segment_value_id = lookup XX_Segment(segment_type_id=3, code=original.segment3)
   segment_code = original.segment3
   oracle_field_name = "SEGMENT3"
   oracle_field_number = 3
```

**Backend Usage Analysis**:
- **Where Used**: Transaction balance checking, dashboards
- **Views**: `transaction/views.py::TransactionTransferListView` - get() method
- **Query Pattern**:
  ```python
  # OLD
  balance_report = XX_BalanceReport.objects.filter(
      control_budget_name='MIC_HQ_MONTHLY',
      segment1='E001',
      segment2='A100',
      segment3='P001'
  ).first()
  
  # NEW
  from account_and_entitys.oracle import OracleBalanceReportManager
  manager = OracleBalanceReportManager()
  result = manager.get_balance_report_data(
      segment_filters={1: 'E001', 2: 'A100', 3: 'P001'}
  )
  ```

**Recommendation**: Start with Option A (keep legacy), migrate to Option B after testing

**Data Volume**: Could be 100,000+ balance report records

---

### ✅ **TASK 8: User Segment Abilities (XX_USER_SEGMENT_ABILITY_XX)**
**Priority**: HIGH - Access control

**Legacy Source**: **XX_USER_ABILITY_XX** (xx_UserAbility model)

**Field Mapping**:
```python
For each xx_UserAbility record:

user_id = user_ability.user_id
segment_type_id = 1 (Entity - legacy only tracked entity abilities)
segment_value_id = lookup XX_Segment where segment_type_id=1, code=user_ability.Entity.entity
ability_type = user_ability.Type (choices: 'edit', 'approve')
is_active = True
```

**Backend Usage Analysis**:
- **Where Used**: Permission checks in views
- **Logic**: Determines if user can edit/approve transfers for specific entities
- **Views**: 
  - `transaction/views.py` - check before allowing edit
  - Approval workflow managers
- **Query Pattern**:
  ```python
  # Check if user can edit Entity E001
  XX_UserSegmentAbility.objects.filter(
      user=request.user,
      segment_type_id=1,
      segment_value__code='E001',
      ability_type='edit',
      is_active=True
  ).exists()
  ```

**Business Rules**:
- Multiple abilities per user
- Entity-specific (historically)
- Can be expanded to Account/Project abilities in new system

**Data Volume**: ~100-500 user ability records

---

### ✅ **TASK 9: User Segment Access (XX_USER_SEGMENT_ACCESS_XX)**
**Priority**: HIGH - Access control

**Legacy Source**: **XX_USER_PROJECTS_XX** (UserProjects model)

**Field Mapping**:
```python
For each UserProjects record:

user_id = user_projects.user_id
segment_type_id = 3 (Project)
segment_value_id = lookup XX_Segment where segment_type_id=3, code=user_projects.project
access_level = 'full' (default - historically all project access was full)
is_active = True
```

**Backend Usage Analysis**:
- **Where Used**: Project filtering in dropdowns, transfer creation
- **Logic**: Limits which projects a user can see/use
- **Views**:
  - `transaction/views.py` - filter available projects
  - Dropdown population in serializers
- **Query Pattern**:
  ```python
  # Get all projects user can access
  user_projects = XX_UserSegmentAccess.objects.filter(
      user=request.user,
      segment_type_id=3,
      is_active=True
  ).select_related('segment_value')
  
  project_codes = [access.segment_value.code for access in user_projects]
  ```

**Business Rules**:
- User only sees assigned projects
- Access can be full, readonly, or restricted
- Hierarchical access (if user has access to parent, gets child access)

**Data Volume**: ~500-2000 user-project assignments

---

### ✅ **TASK 10: Create Migration Scripts**
**Priority**: CRITICAL - Orchestrates all tasks

**Components**:

1. **Data Validation Pre-Check**:
   - Count all legacy records
   - Check for orphaned references
   - Validate data integrity
   - Generate validation report

2. **Sequential Migration Execution**:
   - Task 1: Segment Types (manual/script)
   - Task 2: Segment Master Data (bulk create with batching)
   - Task 3: Segment Mappings (with FK lookups)
   - Task 4: Transaction Segments (high volume, use bulk_create)
   - Task 5: Transfer Limits (with JSON field population)
   - Task 6: Segment Envelopes (simple migration)
   - Task 7: Balance Reports (optional, phased approach)
   - Task 8: User Abilities (with permission mapping)
   - Task 9: User Access (project assignments)

3. **Post-Migration Validation**:
   - Count new records vs legacy
   - Spot check random samples
   - Run Phase 5 tests
   - Verify FK relationships
   - Test critical user workflows

4. **Rollback Capability**:
   - Backup database before migration
   - Create rollback script
   - Log all operations
   - Support partial rollback

---

## Migration Execution Order

```
PHASE 1: Foundation (Must complete in order)
├── TASK 1: XX_SEGMENT_TYPE_XX (manual config)
├── TASK 2: XX_SEGMENT_XX (all master data)
└── TASK 3: XX_SEGMENT_MAPPING_XX (dependencies: Task 2)

PHASE 2: Transaction Data (Can run in parallel after Phase 1)
├── TASK 4: XX_TRANSACTION_SEGMENT_XX (dependencies: Task 2)
├── TASK 5: XX_SEGMENT_TRANSFER_LIMIT_XX (dependencies: Task 2)
└── TASK 6: XX_SEGMENT_ENVELOPE_XX (dependencies: Task 2)

PHASE 3: User Access Control (Can run in parallel after Phase 1)
├── TASK 8: XX_USER_SEGMENT_ABILITY_XX (dependencies: Task 2)
└── TASK 9: XX_USER_SEGMENT_ACCESS_XX (dependencies: Task 2)

PHASE 4: Historical Data (Optional, can defer)
└── TASK 7: XX_BALANCE_REPORT_SEGMENT_XX (dependencies: Task 2)

PHASE 5: Validation & Testing
└── TASK 10: Run all Phase 5 tests, verify data integrity
```

---

## Risk Assessment

### High Risk Areas:
1. **Task 4 (Transaction Segments)**: Highest volume, most critical
2. **Task 7 (Balance Reports)**: Potential data loss if not careful
3. **Task 2 (Segment Master)**: Foundation for everything else

### Mitigation Strategies:
1. Database backup before starting
2. Dry-run mode for all scripts
3. Batch processing with progress logging
4. Validation checks after each task
5. Keep legacy tables intact during migration
6. Gradual cutover (not big bang)

---

## Testing Strategy

### Pre-Migration Tests:
- ✅ Phase 5 Oracle integration tests (24/24 passing)
- Validate all legacy data is readable
- Check for NULL/missing values

### Post-Migration Tests:
- Run Phase 5 tests again (should still pass)
- Manual testing of critical workflows:
  - Create new budget transfer
  - Approve transfer
  - Check balance reports
  - Verify user access controls
- Data integrity checks (counts, FK relationships)

### Rollback Tests:
- Verify backup restoration
- Test partial rollback scenarios

---

## Success Criteria

✅ All legacy data migrated without loss
✅ All Phase 5 tests passing (24/24)
✅ Critical workflows functional
✅ User access controls working
✅ Balance reports accurate
✅ No performance degradation
✅ Rollback capability verified

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Create backup** of production database
3. **Implement Task 1** (Segment Type configuration)
4. **Develop migration scripts** for Tasks 2-9
5. **Test in development environment**
6. **Execute in staging environment**
7. **Validate and get sign-off**
8. **Schedule production migration**

---

**Estimated Total Time**: 
- Script Development: 8-12 hours
- Testing: 4-6 hours
- Execution: 2-4 hours
- **Total: 14-22 hours**

**Recommended Approach**: Phased migration over 2-3 days with validation between each phase
