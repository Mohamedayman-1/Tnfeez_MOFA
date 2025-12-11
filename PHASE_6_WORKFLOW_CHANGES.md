# Phase 6: Security Group-Based Workflow Assignment - Implementation Progress

## Overview
Major architectural change to assign workflows to security groups instead of individual stage-based assignments.

## Requirements Summary
1. Security groups can be assigned to one or multiple workflow templates
2. When user creates transfer → workflows auto-assigned based on their security group
3. All stages of a workflow use the SAME security group (from transfer)
4. Stage filtering by role ONLY (not security group check anymore)
5. Multiple workflows execute SEQUENTIALLY (Workflow 2 starts after Workflow 1 completes)
6. User sees transfer ONLY when their role matches the active stage's required_role

---

## ✅ COMPLETED CHANGES

### 1. Models Updated (`approvals/models.py`)

#### **NEW MODEL: XX_WorkflowTemplateAssignment**
```python
class XX_WorkflowTemplateAssignment(models.Model):
    """Links workflow templates to security groups with execution order"""
    security_group = FK to XX_SecurityGroup
    workflow_template = FK to ApprovalWorkflowTemplate
    execution_order = PositiveIntegerField (1 = first, 2 = second, etc.)
    is_active = BooleanField
    created_at, created_by
```

#### **MODIFIED: ApprovalWorkflowStageTemplate**
- `required_role`: Changed from CharField to **FK to XX_SecurityGroupRole**
- `security_group`: Marked as DEPRECATED (kept for backward compatibility)
- Comment added: Security group now determined by XX_WorkflowTemplateAssignment

#### **MODIFIED: ApprovalWorkflowInstance**
- `budget_transfer`: Changed from **OneToOneField** to **ForeignKey** (`workflow_instances`)
- Added `workflow_assignment`: FK to XX_WorkflowTemplateAssignment
- Added `execution_order`: Tracks which workflow in the sequence (1, 2, 3...)
- Added class methods:
  - `get_active_workflow(budget_transfer)`: Returns currently active workflow
  - `get_next_workflow(budget_transfer, current_workflow)`: Returns next workflow to start

---

### 2. Budget Transfer Model Updated (`budget_management/models.py`)

#### **ADDED: workflow_instance Property**
```python
@property
def workflow_instance(self):
    """Backward compatibility - returns active workflow instance"""
    return ApprovalWorkflowInstance.get_active_workflow(self)
```
This maintains backward compatibility with existing code that uses `transfer.workflow_instance`.

---

### 3. Approval Manager Updated (`approvals/managers.py`)

#### **MODIFIED: create_instance()**
```python
# OLD: Created single workflow instance based on transfer_type
# NEW: Creates ALL workflows assigned to transfer's security group
#      Returns list of workflow instances ordered by execution_order
```

Key changes:
- Gets XX_WorkflowTemplateAssignment records for transfer's security group
- Creates one workflow instance per assignment
- Each instance gets execution_order from assignment
- Returns empty list if no workflows assigned

#### **MODIFIED: start_workflow()**
```python
# OLD: Started single workflow
# NEW: Creates all workflows, activates ONLY the first one (execution_order=1)
```

#### **MODIFIED: _activate_next_stage_internal()**
Added sequential workflow activation at 2 locations (where workflow completes):
```python
# When no more stages in current workflow:
next_workflow = ApprovalWorkflowInstance.get_next_workflow(budget_transfer, instance)
if next_workflow:
    cls._activate_next_stage_internal(budget_transfer, instance=next_workflow)
```

#### **MODIFIED: _create_assignments()**
```python
# OLD: Filtered by stage_template.security_group + required_role (string)
# NEW: Uses transfer.security_group + required_role (FK to XX_SecurityGroupRole)
```

Key changes:
- Gets security group from `budget_transfer.security_group` (not stage template)
- Filters users by XX_UserGroupMembership in that group
- Further filters by users who have `stage_template.required_role` assigned
- No more stage-level security group check

#### **MODIFIED: get_user_pending_approvals()**
```python
# Changed all queries from workflow_instance to workflow_instances
# Example: workflow_instance__status → workflow_instances__status
```

---

## 🔄 PENDING CHANGES

### 4. Backend API Endpoints (NOT YET CREATED)
Need to create:
- `POST /api/workflows/assignments/` - Assign workflow to security group
- `DELETE /api/workflows/assignments/<id>/` - Remove assignment
- `PUT /api/workflows/assignments/<id>/reorder/` - Change execution_order
- `GET /api/workflows/assignments/?security_group=<id>` - List assignments

### 5. Frontend Updates (NOT YET DONE)
- **AddWorkFlow.tsx**: Remove security_group selection from stage creation
- **AddWorkFlow.tsx**: Add workflow-to-group assignment UI
- **Transfer creation**: Remove manual workflow selection (auto-assign)

### 6. Database Migration (NOT YET CREATED)
Need to generate migration for:
- New XX_WorkflowTemplateAssignment table
- ApprovalWorkflowInstance: OneToOneField → ForeignKey
- ApprovalWorkflowStageTemplate: required_role CharField → FK
- Add execution_order, workflow_assignment fields

### 7. Data Migration (NOT YET DONE)
Need script to:
- Convert existing workflow_instance relationships
- Set execution_order=1 for all existing workflows
- Optionally create XX_WorkflowTemplateAssignment records from existing data

---

## 🔧 BREAKING CHANGES

### Code that needs updating:

1. **Any code using `transfer.workflow_instance`:**
   - STILL WORKS via property (returns active workflow)
   - But to access ALL workflows: use `transfer.workflow_instances.all()`

2. **Any code filtering by workflow_instance (singular):**
   ```python
   # OLD
   xx_BudgetTransfer.objects.filter(workflow_instance__status=...)
   
   # NEW
   xx_BudgetTransfer.objects.filter(workflow_instances__status=...)
   ```

3. **ApprovalWorkflowStageTemplate.required_role:**
   - OLD: String field (e.g., "Finance Manager")
   - NEW: FK to XX_SecurityGroupRole model
   - Need to update any code that reads/writes this field

4. **Stage security_group field:**
   - Now IGNORED in assignment creation
   - Security group comes from transfer, not stage
   - Can be left NULL for new workflows

---

## 📊 Testing Scenarios

### Scenario 1: Single Workflow
1. Assign "Finance Team" → "Workflow Template 1"
2. User from Finance Team creates transfer
3. Workflow 1 should start automatically

### Scenario 2: Sequential Workflows
1. Assign "Finance Team" → "Workflow 1" (order=1), "Workflow 2" (order=2)
2. User creates transfer
3. Workflow 1 starts, Workflow 2 stays pending
4. When Workflow 1 completes → Workflow 2 should auto-start

### Scenario 3: Role-Based Visibility
1. Transfer in Finance Team with active "Finance Manager" stage
2. User A (Finance Manager role) → sees transfer
3. User B (Unit Head role) → does NOT see transfer (different role)
4. When "Unit Head" stage activates → User B sees it, User A doesn't

---

## 🎯 Next Steps

1. Generate Django migration
2. Create API endpoints for workflow assignments
3. Update frontend to remove stage security_group selection
4. Add workflow-to-group assignment UI
5. Test sequential workflow execution
6. Data migration for existing workflows

---

**Status**: Backend core logic complete, pending migration + frontend + API endpoints
**Date**: December 11, 2025
