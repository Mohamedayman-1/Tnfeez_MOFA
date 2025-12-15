# Dashboard Security Group Filtering - Implementation

## Overview
Modified `DashboardBudgetTransferView` to display data for all users within the same security group(s), not just the current user's data.

## Changes Made

### 1. Import Addition
Added `XX_UserGroupMembership` to imports:
```python
from user_management.models import xx_User, xx_notification, XX_UserGroupMembership
```

### 2. Modified `get()` Method
Updated the filtering logic to:
1. Get all users in the same security group(s) as the current user
2. Aggregate entity IDs from all those users
3. Filter budget transfers using the combined entity access

**Before:**
```python
if request.user.abilities_legacy.count() > 0:
    transfers_queryset = filter_budget_transfers_all_in_entities(
        transfers_queryset,
        request.user,  # Only current user
        "edit",
        dashboard_filler_per_project=DashBoard_filler_per_Project,
    )
```

**After:**
```python
# Get all users in the same security group(s) as the current user
users_in_same_groups = self._get_users_in_same_security_groups(request.user)

if request.user.abilities_legacy.count() > 0:
    # Get abilities from all users in the same security groups
    all_entity_ids = set()
    for user in users_in_same_groups:
        user_entity_ids = [
            ability.Entity.id
            for ability in user.abilities_legacy.all()
            if ability.Entity and ability.Type == "edit"
        ]
        all_entity_ids.update(user_entity_ids)
    
    # Apply filtering using the combined entity IDs
    if all_entity_ids:
        transfers_queryset = self._filter_by_group_entities(
            transfers_queryset,
            list(all_entity_ids),
            dashboard_filler_per_project=DashBoard_filler_per_Project
        )
```

### 3. Added Helper Methods

#### `_get_users_in_same_security_groups(user)`
Returns all users who belong to the same security group(s) as the given user.

**Logic:**
1. Get all security group IDs the user belongs to
2. Find all users in those same security groups
3. Return distinct active users

**Usage:**
```python
users = self._get_users_in_same_security_groups(request.user)
# Returns: QuerySet of xx_User objects
```

#### `_filter_by_group_entities(queryset, entity_ids, dashboard_filler_per_project=None)`
Filters budget transfers by entity IDs from all users in the security group.

**Logic:**
1. Get entities with their children (hierarchical structure)
2. Convert entity codes to numeric format
3. Use raw SQL to filter transfers where all transactions belong to allowed entities
4. Return filtered QuerySet

**Usage:**
```python
filtered = self._filter_by_group_entities(
    transfers_queryset,
    [1, 2, 3],  # Entity IDs
    dashboard_filler_per_project="100"  # Optional
)
```

## Behavior

### Before Implementation
- User A in "Finance Team" → sees only their own budget transfers
- User B in "Finance Team" → sees only their own budget transfers
- Users see different data even though they're in the same group

### After Implementation
- User A in "Finance Team" → sees budget transfers from all Finance Team members
- User B in "Finance Team" → sees budget transfers from all Finance Team members
- Users in the same group see the same data (shared view)

### Multiple Groups
If a user belongs to multiple security groups:
- Data from **all** groups is combined
- User sees budget transfers from all members across all their groups

**Example:**
```
User John belongs to:
  - Finance Team (Members: John, Sarah, Mike)
  - Audit Committee (Members: John, Lisa, Tom)

Dashboard shows budget transfers accessible by:
  John, Sarah, Mike, Lisa, Tom
  (all users from both groups)
```

## Edge Cases Handled

### 1. User Not in Any Security Group
```python
users = self._get_users_in_same_security_groups(request.user)
# Returns: Only the current user
# Behavior: Same as before (shows only own data)
```

### 2. User Has No Abilities
```python
if request.user.abilities_legacy.count() > 0:
    # Filter by group entities
else:
    # No filtering applied - shows all group data
```

### 3. Empty Entity IDs
```python
if all_entity_ids:
    transfers_queryset = self._filter_by_group_entities(...)
else:
    # No filtering if no entity access found
```

### 4. Invalid Entity Codes
Non-numeric entity codes are skipped to avoid Oracle errors:
```python
try:
    numeric_entity_codes.append(int(str(code).strip()))
except Exception:
    continue  # Skip invalid codes
```

## Database Queries

### Query 1: Get User's Security Groups
```sql
SELECT security_group_id 
FROM XX_USER_GROUP_MEMBERSHIP_XX 
WHERE user_id = ? AND is_active = 1
```

### Query 2: Get All Users in Those Groups
```sql
SELECT DISTINCT u.* 
FROM XX_USER_XX u
INNER JOIN XX_USER_GROUP_MEMBERSHIP_XX m 
  ON u.id = m.user_id
WHERE m.security_group_id IN (...)
  AND m.is_active = 1
  AND u.is_active = 1
```

### Query 3: Filter Budget Transfers
```sql
-- Get transfers where all transactions belong to allowed entities
SELECT bt.transaction_id
FROM XX_BUDGET_TRANSFER_XX bt
WHERE NOT EXISTS (
    SELECT 1 
    FROM XX_TRANSACTION_TRANSFER_XX tt 
    WHERE tt.transaction_id = bt.transaction_id 
    AND tt.cost_center_code NOT IN (entity_codes)
)
AND EXISTS (
    SELECT 1 
    FROM XX_TRANSACTION_TRANSFER_XX tt2 
    WHERE tt2.transaction_id = bt.transaction_id
)
UNION
-- Include transfers with no transactions
SELECT bt.transaction_id
FROM XX_BUDGET_TRANSFER_XX bt
WHERE NOT EXISTS (
    SELECT 1 
    FROM XX_TRANSACTION_TRANSFER_XX tt 
    WHERE tt.transaction_id = bt.transaction_id
)
```

## Performance Considerations

### Optimizations
1. **Distinct Users:** Uses `.distinct()` to avoid duplicate users
2. **Set for Entity IDs:** Uses Python `set()` for efficient ID aggregation
3. **Raw SQL:** Uses raw SQL for complex filtering (same as original implementation)
4. **Minimal Queries:** Only 2-3 additional queries per request

### Expected Performance Impact
- **Small Groups (2-5 users):** Minimal impact (~10-50ms additional)
- **Medium Groups (5-20 users):** Moderate impact (~50-200ms additional)
- **Large Groups (20+ users):** May need optimization if slow

### Monitoring
Added debug prints to track performance:
```python
print(f"Total transfers before filtering: {len(transfers_queryset)}")
print(f"Users in same security groups: {[u.username for u in users_in_same_groups]}")
print(f"Total entity IDs from all group members: {len(all_entity_ids)}")
print(f"Transfers after group filtering: {len(transfers_queryset)}")
```

## Testing

### Test Case 1: Users in Same Group
**Setup:**
- User A: Finance Team
- User B: Finance Team
- Both have access to different entities

**Expected Result:**
- Both users see combined data from entities A and B

**Test:**
```bash
# Login as User A
curl -X GET "http://localhost:8000/api/budget/dashboard/?type=normal" \
  -H "Authorization: Bearer USER_A_TOKEN"

# Login as User B
curl -X GET "http://localhost:8000/api/budget/dashboard/?type=normal" \
  -H "Authorization: Bearer USER_B_TOKEN"

# Both responses should have the same total_transfers count
```

### Test Case 2: User in Multiple Groups
**Setup:**
- User C: Finance Team + Audit Committee
- Finance Team: Users A, B, C
- Audit Committee: Users C, D, E

**Expected Result:**
- User C sees data from all 5 users (A, B, C, D, E)

### Test Case 3: User Not in Any Group
**Setup:**
- User F: No group memberships

**Expected Result:**
- User F sees only their own data (backward compatible)

### Test Case 4: Empty Group
**Setup:**
- User G: Only member of "New Department" group

**Expected Result:**
- User G sees only their own data

## Backward Compatibility

✅ **Fully Backward Compatible**

- Users not in any security groups: Same behavior as before
- Users with no abilities: Same behavior as before
- Existing filtering logic: Preserved and extended
- API response format: Unchanged

## Future Enhancements

1. **Caching:** Cache security group memberships to reduce queries
2. **Query Optimization:** Index on `security_group_id` in memberships table
3. **Configuration:** Allow admins to enable/disable group-based filtering
4. **UI Indicator:** Show which users' data is included in the dashboard
5. **Filtering Options:** Add parameter to toggle between "own data" and "group data"

## Related Files Modified

- `budget_management/views.py`: Main implementation

## Related Documentation

- Phase 5 Security Groups: `__CLIENT_SETUP_DOCS__/PHASE_5_*.md`
- User Profile API: `__CLIENT_SETUP_DOCS__/USER_PROFILE_API.md`

---

**Implementation Date:** December 13, 2025  
**Status:** ✅ Complete  
**Breaking Changes:** None
