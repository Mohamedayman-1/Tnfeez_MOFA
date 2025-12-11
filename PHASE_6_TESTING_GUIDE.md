# Phase 6: Quick Testing Guide

## Prerequisites
1. ✅ Applied migration: `python manage.py migrate`
2. ✅ Created at least 2 workflow templates
3. ✅ Created at least 1 security group with members
4. ✅ Members have roles assigned (e.g., Finance Manager, Unit Head)

---

## Test Scenario 1: Single Workflow Assignment

### Step 1: Assign Workflow to Group
```bash
# Using httpie or curl
http POST http://localhost:8000/api/approvals/workflow-assignments/ \
  security_group=1 \
  workflow_template=1 \
  execution_order=1 \
  is_active=true \
  Authorization:"Bearer YOUR_TOKEN"
```

### Step 2: Create Transfer
- Login as user from Security Group 1
- Create a budget transfer (FAR)
- Submit for approval

### Expected Result:
- ✅ Workflow 1 starts automatically
- ✅ First stage activates
- ✅ Users with matching role see transfer in pending

---

## Test Scenario 2: Sequential Workflows

### Step 1: Assign Multiple Workflows
```bash
http POST http://localhost:8000/api/approvals/workflow-assignments/bulk-assign/ \
  security_group_id=1 \
  workflow_assignments:='[
    {"workflow_template_id": 1, "execution_order": 1},
    {"workflow_template_id": 2, "execution_order": 2}
  ]' \
  Authorization:"Bearer YOUR_TOKEN"
```

### Step 2: Create and Approve Transfer
1. User from Group 1 creates transfer
2. Approve all stages in Workflow 1
3. **Watch for Workflow 2 to auto-start**

### Expected Result:
- ✅ Workflow 1 starts (execution_order=1)
- ✅ After Workflow 1 completes → Workflow 2 starts automatically
- ✅ Console shows: "[INFO] Workflow completed. Starting next workflow..."

---

## Test Scenario 3: Role-Based Visibility

### Setup:
- Security Group: Finance Team
- Workflow Stage 1: Finance Manager role required
- Workflow Stage 2: Unit Head role required
- Users:
  - User A: Finance Manager role
  - User B: Unit Head role

### Test Steps:
1. Create transfer (Stage 1 active: Finance Manager)
   - **User A should see it** ✅
   - **User B should NOT see it** ✅

2. User A approves → Stage 2 activates (Unit Head)
   - **User A should NOT see it anymore** ✅
   - **User B should now see it** ✅

---

## Debugging Commands

### Check Workflow Assignments
```python
python manage.py shell

from approvals.models import XX_WorkflowTemplateAssignment
from user_management.models import XX_SecurityGroup

# List all assignments
for assignment in XX_WorkflowTemplateAssignment.objects.all():
    print(f"{assignment.security_group.group_name} → {assignment.workflow_template.code} (Order: {assignment.execution_order})")
```

### Check Transfer's Workflows
```python
from budget_management.models import xx_BudgetTransfer

transfer = xx_BudgetTransfer.objects.get(code='FAR-0001')

# Get active workflow
active_workflow = transfer.workflow_instance
print(f"Active: {active_workflow.template.code if active_workflow else 'None'}")

# Get all workflows
for workflow in transfer.workflow_instances.all():
    print(f"{workflow.execution_order}. {workflow.template.code} - {workflow.status}")
```

### Manually Trigger Next Workflow
```python
from approvals.managers import ApprovalManager
from budget_management.models import xx_BudgetTransfer

transfer = xx_BudgetTransfer.objects.get(code='FAR-0001')
active = transfer.workflow_instance

if active:
    # Complete current workflow
    active.status = 'approved'
    active.save()
    
    # Manually trigger next
    ApprovalManager._activate_next_stage_internal(transfer, instance=active)
```

---

## Common Issues

### Issue: "No workflows created"
**Cause**: Transfer has no security_group
**Fix**: Assign security group to transfer before submission

### Issue: "No users found for stage"
**Cause**: No users have the required role in the group
**Fix**: 
1. Check stage's required_role
2. Verify users have that role assigned in XX_UserGroupMembership

### Issue: Workflow 2 doesn't start
**Cause**: Workflow 1 not fully completed
**Debug**:
```python
workflow1 = transfer.workflow_instances.get(execution_order=1)
print(workflow1.status)  # Should be 'approved'
print(workflow1.finished_at)  # Should have timestamp
```

---

## API Test Collection (Postman/Thunder Client)

### 1. List Assignments
```
GET /api/approvals/workflow-assignments/
```

### 2. Assign Workflow
```
POST /api/approvals/workflow-assignments/
{
  "security_group": 1,
  "workflow_template": 1,
  "execution_order": 1,
  "is_active": true
}
```

### 3. Bulk Assign
```
POST /api/approvals/workflow-assignments/bulk-assign/
{
  "security_group_id": 1,
  "workflow_assignments": [
    {"workflow_template_id": 1, "execution_order": 1},
    {"workflow_template_id": 2, "execution_order": 2}
  ]
}
```

### 4. Reorder
```
PUT /api/approvals/workflow-assignments/reorder/
{
  "security_group_id": 1,
  "assignment_orders": [
    {"assignment_id": 1, "execution_order": 2},
    {"assignment_id": 2, "execution_order": 1}
  ]
}
```

---

## Success Criteria

- [ ] User creates transfer → correct workflow starts automatically
- [ ] User only sees transfers when their role matches active stage
- [ ] Workflow 1 completes → Workflow 2 starts (no manual intervention)
- [ ] Console logs show sequential workflow activation
- [ ] API endpoints return correct assignment data
- [ ] Bulk assign replaces existing assignments correctly
- [ ] Reorder changes execution order successfully

---

**Ready to Test!** 🚀
