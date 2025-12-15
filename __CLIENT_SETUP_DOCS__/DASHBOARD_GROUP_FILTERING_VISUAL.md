# Dashboard Security Group Filtering - Visual Flow

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER MAKES REQUEST                           │
│           GET /api/budget/dashboard/?type=normal                │
│                  Authorization: Bearer token                     │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              STEP 1: IDENTIFY USER'S GROUPS                     │
│                                                                  │
│  Query: XX_UserGroupMembership                                  │
│  WHERE user_id = current_user.id AND is_active = True          │
│                                                                  │
│  Result: [Finance Team (ID: 3), Audit Committee (ID: 7)]       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│          STEP 2: GET ALL USERS IN THOSE GROUPS                  │
│                                                                  │
│  Query: xx_User                                                 │
│  JOIN XX_UserGroupMembership                                    │
│  WHERE security_group_id IN (3, 7) AND is_active = True        │
│                                                                  │
│  Result: [User A, User B, User C, User D, User E]              │
│                                                                  │
│  Group Details:                                                 │
│    Finance Team (3): User A, User B, User C                    │
│    Audit Committee (7): User C, User D, User E                 │
│    (User C is in both groups)                                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│        STEP 3: AGGREGATE ENTITY ACCESS FROM ALL USERS           │
│                                                                  │
│  For each user in group:                                        │
│    User A abilities: Entity 100, 101                           │
│    User B abilities: Entity 102                                │
│    User C abilities: Entity 103, 104                           │
│    User D abilities: Entity 105                                │
│    User E abilities: (none)                                    │
│                                                                  │
│  Combined Entity IDs: {100, 101, 102, 103, 104, 105}          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│          STEP 4: EXPAND TO INCLUDE CHILD ENTITIES               │
│                                                                  │
│  get_entities_with_children([100, 101, 102, 103, 104, 105])   │
│                                                                  │
│  Entity Hierarchy:                                              │
│    100 → 100, 1001, 1002                                       │
│    101 → 101, 1011                                             │
│    102 → 102                                                    │
│    ...                                                          │
│                                                                  │
│  Final Entity Codes: [100, 1001, 1002, 101, 1011, 102, ...]   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│          STEP 5: FILTER BUDGET TRANSFERS (RAW SQL)              │
│                                                                  │
│  SELECT bt.transaction_id                                       │
│  FROM XX_BUDGET_TRANSFER_XX bt                                  │
│  WHERE NOT EXISTS (                                             │
│    -- No transactions outside allowed entities                 │
│    SELECT 1                                                     │
│    FROM XX_TRANSACTION_TRANSFER_XX tt                          │
│    WHERE tt.transaction_id = bt.transaction_id                 │
│    AND tt.cost_center_code NOT IN (100, 101, 102, ...)        │
│  )                                                              │
│  AND EXISTS (                                                   │
│    -- Has at least one transaction                             │
│    SELECT 1                                                     │
│    FROM XX_TRANSACTION_TRANSFER_XX tt2                         │
│    WHERE tt2.transaction_id = bt.transaction_id                │
│  )                                                              │
│                                                                  │
│  Result: [Transfer_1, Transfer_5, Transfer_12, ...]           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              STEP 6: CALCULATE DASHBOARD METRICS                │
│                                                                  │
│  Aggregate filtered transfers:                                  │
│    - Total count                                                │
│    - Count by status (approved, rejected, pending)             │
│    - Count by level (1, 2, 3, 4)                               │
│    - Count by code (FAR, AFR, FAD)                             │
│                                                                  │
│  Result Dashboard Data:                                         │
│    total_transfers: 45                                          │
│    approved_transfers: 30                                       │
│    pending_transfers: 10                                        │
│    rejected_transfers: 5                                        │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  RETURN JSON RESPONSE                           │
│                                                                  │
│  {                                                              │
│    "normal": {                                                  │
│      "total_transfers": 45,                                     │
│      "approved_transfers": 30,                                  │
│      "pending_transfers": 10,                                   │
│      "rejected_transfers": 5,                                   │
│      ...                                                        │
│    }                                                            │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Group Membership Scenarios

### Scenario 1: Single Group Membership

```
┌──────────────────────────────────────────┐
│         Security Group: Finance Team      │
│                                           │
│  Members:                                 │
│    ┌─────────┐  ┌─────────┐  ┌─────────┐│
│    │ User A  │  │ User B  │  │ User C  ││
│    └────┬────┘  └────┬────┘  └────┬────┘│
│         │            │            │      │
└─────────┼────────────┼────────────┼──────┘
          │            │            │
     Entity 100    Entity 101   Entity 102
          │            │            │
          └────────────┴────────────┘
                       │
                  Combined Access
                       │
                   ┌───▼────┐
                   │Dashboard│
                   │ Shows:  │
                   │ 100, 101│
                   │ 102     │
                   └─────────┘
```

### Scenario 2: Multiple Group Membership

```
┌──────────────────────────────────────────┐
│      Security Group: Finance Team         │
│  Members: User A, User B, User C         │
└──────────────────────────────────────────┘
                    ▲
                    │ (User C is in both)
                    │
                    ▼
┌──────────────────────────────────────────┐
│    Security Group: Audit Committee        │
│  Members: User C, User D, User E         │
└──────────────────────────────────────────┘

User C's Dashboard View:
  ┌─────────────────────────────────┐
  │  Finance Team entities:         │
  │    User A → Entity 100          │
  │    User B → Entity 101          │
  │    User C → Entity 102          │
  ├─────────────────────────────────┤
  │  Audit Committee entities:      │
  │    User C → Entity 102          │
  │    User D → Entity 103          │
  │    User E → Entity 104          │
  ├─────────────────────────────────┤
  │  Combined (deduplicated):       │
  │    100, 101, 102, 103, 104      │
  └─────────────────────────────────┘
```

### Scenario 3: No Group Membership

```
┌──────────────────────────────────────────┐
│          User F (No Groups)              │
│                                           │
│  Entity Access: 200, 201                 │
│                                           │
│  Dashboard Shows:                         │
│    Only transfers from Entity 200, 201   │
│    (Same as before - backward compat)    │
└──────────────────────────────────────────┘
```

---

## Entity Hierarchy Expansion

```
User has access to Entity 100
                │
                ▼
        ┌───────────────┐
        │  Entity 100   │
        └───┬───────┬───┘
            │       │
    ┌───────▼──┐  ┌▼────────┐
    │Entity 1001│ │Entity 1002│
    └───────────┘ └──┬────────┘
                     │
              ┌──────▼──────┐
              │Entity 10021  │
              └─────────────┘

Dashboard filters include:
  100, 1001, 1002, 10021 (all in hierarchy)
```

---

## Performance Flow

```
Request Start
    │
    ├─ Get User's Groups (Query 1)         ~10ms
    │
    ├─ Get Group Members (Query 2)         ~20ms
    │
    ├─ Get All Abilities (Query 3-N)       ~50ms
    │
    ├─ Expand Hierarchy                    ~30ms
    │
    ├─ Filter Transfers (Raw SQL)          ~100ms
    │
    └─ Aggregate & Return                  ~40ms
                                           ─────
                                 Total:    ~250ms

Optimization Opportunities:
  ✅ Cache group memberships
  ✅ Cache entity hierarchies
  ✅ Index on security_group_id
  ✅ Database query optimization
```

---

## Database Query Sequence

```sql
-- Query 1: Get user's security groups
SELECT security_group_id 
FROM XX_USER_GROUP_MEMBERSHIP_XX 
WHERE user_id = 5 AND is_active = 1;

-- Query 2: Get all users in those groups
SELECT DISTINCT u.id, u.username
FROM XX_USER_XX u
INNER JOIN XX_USER_GROUP_MEMBERSHIP_XX m ON u.id = m.user_id
WHERE m.security_group_id IN (3, 7)
  AND m.is_active = 1
  AND u.is_active = 1;

-- Query 3: Get abilities for each user (looped)
SELECT entity_id 
FROM XX_USER_ABILITY_XX 
WHERE user_id = ? AND Type = 'edit';

-- Query 4: Get entity hierarchy
SELECT * 
FROM XX_ENTITY_XX 
WHERE id IN (...) OR parent_id IN (...);

-- Query 5: Filter budget transfers
SELECT bt.transaction_id
FROM XX_BUDGET_TRANSFER_XX bt
WHERE NOT EXISTS (
  SELECT 1 
  FROM XX_TRANSACTION_TRANSFER_XX tt 
  WHERE tt.transaction_id = bt.transaction_id 
    AND tt.cost_center_code NOT IN (...)
);

-- Query 6: Aggregate for dashboard
SELECT 
  COUNT(*) as total,
  SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved,
  SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected,
  SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending
FROM XX_BUDGET_TRANSFER_XX
WHERE transaction_id IN (...);
```

---

## Comparison: Before vs After

### Before (User-Based Filtering)
```
User A Request
    │
    ├─ Get User A's abilities        → Entity 100, 101
    │
    ├─ Filter by Entity 100, 101     → 10 transfers
    │
    └─ Return dashboard              → total: 10

User B Request (same group as A)
    │
    ├─ Get User B's abilities        → Entity 102, 103
    │
    ├─ Filter by Entity 102, 103     → 8 transfers
    │
    └─ Return dashboard              → total: 8

❌ Different data for same group members
```

### After (Group-Based Filtering)
```
User A Request
    │
    ├─ Get group members             → User A, User B, User C
    │
    ├─ Aggregate abilities           → Entity 100, 101, 102, 103
    │
    ├─ Filter by combined entities   → 25 transfers
    │
    └─ Return dashboard              → total: 25

User B Request (same group as A)
    │
    ├─ Get group members             → User A, User B, User C
    │
    ├─ Aggregate abilities           → Entity 100, 101, 102, 103
    │
    ├─ Filter by combined entities   → 25 transfers
    │
    └─ Return dashboard              → total: 25

✅ Same data for all group members
```

---

**Visualization created for:** Dashboard Security Group Filtering  
**Date:** December 13, 2025
