# Phase 6: Workflow Assignment API Documentation

## Overview
New API endpoints for assigning workflow templates to security groups with execution order management.

---

## Base URL
```
/api/approvals/workflow-assignments/
```

---

## Endpoints

### 1. List Workflow Assignments
**GET** `/api/approvals/workflow-assignments/`

Get all workflow assignments, optionally filtered by security group.

#### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| security_group | integer | No | Filter by security group ID |

#### Response
```json
{
  "success": true,
  "count": 2,
  "assignments": [
    {
      "id": 1,
      "security_group": 1,
      "security_group_name": "Finance Team",
      "workflow_template": 5,
      "workflow_template_name": "FAR Approval Workflow",
      "workflow_template_code": "FAR_WF_V1",
      "transfer_type": "FAR",
      "execution_order": 1,
      "is_active": true,
      "created_at": "2025-12-11T10:00:00Z",
      "created_by": 1
    },
    {
      "id": 2,
      "security_group": 1,
      "security_group_name": "Finance Team",
      "workflow_template": 6,
      "workflow_template_name": "Secondary Review Workflow",
      "workflow_template_code": "FAR_WF_REVIEW",
      "transfer_type": "FAR",
      "execution_order": 2,
      "is_active": true,
      "created_at": "2025-12-11T10:05:00Z",
      "created_by": 1
    }
  ]
}
```

---

### 2. Create Workflow Assignment
**POST** `/api/approvals/workflow-assignments/`

Assign a workflow template to a security group.

#### Request Body
```json
{
  "security_group": 1,
  "workflow_template": 5,
  "execution_order": 1,
  "is_active": true
}
```

#### Response (201 Created)
```json
{
  "success": true,
  "message": "Workflow assignment created successfully",
  "assignment": {
    "id": 3,
    "security_group": 1,
    "security_group_name": "Finance Team",
    "workflow_template": 5,
    "workflow_template_name": "FAR Approval Workflow",
    "workflow_template_code": "FAR_WF_V1",
    "transfer_type": "FAR",
    "execution_order": 1,
    "is_active": true,
    "created_at": "2025-12-11T12:00:00Z",
    "created_by": 2
  }
}
```

#### Error Response (400 Bad Request)
```json
{
  "success": false,
  "errors": {
    "non_field_errors": [
      "Workflow template 'FAR_WF_V1' is already assigned to security group 'Finance Team'"
    ]
  }
}
```

---

### 3. Get Workflow Assignment Details
**GET** `/api/approvals/workflow-assignments/{id}/`

Retrieve details of a specific workflow assignment.

#### Response
```json
{
  "success": true,
  "assignment": {
    "id": 1,
    "security_group": 1,
    "security_group_name": "Finance Team",
    "workflow_template": 5,
    "workflow_template_name": "FAR Approval Workflow",
    "workflow_template_code": "FAR_WF_V1",
    "transfer_type": "FAR",
    "execution_order": 1,
    "is_active": true,
    "created_at": "2025-12-11T10:00:00Z",
    "created_by": 1
  }
}
```

---

### 4. Update Workflow Assignment
**PUT** `/api/approvals/workflow-assignments/{id}/`

Update an existing workflow assignment.

#### Request Body
```json
{
  "security_group": 1,
  "workflow_template": 5,
  "execution_order": 2,
  "is_active": true
}
```

#### Response
```json
{
  "success": true,
  "message": "Assignment updated successfully",
  "assignment": { /* updated assignment object */ }
}
```

---

### 5. Delete Workflow Assignment
**DELETE** `/api/approvals/workflow-assignments/{id}/`

Remove a workflow assignment from a security group.

#### Response
```json
{
  "success": true,
  "message": "Removed workflow \"FAR_WF_V1\" from security group \"Finance Team\""
}
```

---

### 6. Bulk Assign Workflows
**POST** `/api/approvals/workflow-assignments/bulk-assign/`

Assign multiple workflows to a security group at once. **This replaces all existing assignments for the group.**

#### Request Body
```json
{
  "security_group_id": 1,
  "workflow_assignments": [
    {
      "workflow_template_id": 5,
      "execution_order": 1
    },
    {
      "workflow_template_id": 6,
      "execution_order": 2
    },
    {
      "workflow_template_id": 7,
      "execution_order": 3
    }
  ]
}
```

#### Response (201 Created)
```json
{
  "success": true,
  "message": "Assigned 3 workflow(s) to \"Finance Team\"",
  "deleted_count": 2,
  "created_count": 3,
  "assignments": [
    {
      "id": 10,
      "security_group": 1,
      "security_group_name": "Finance Team",
      "workflow_template": 5,
      "workflow_template_name": "FAR Approval Workflow",
      "workflow_template_code": "FAR_WF_V1",
      "transfer_type": "FAR",
      "execution_order": 1,
      "is_active": true,
      "created_at": "2025-12-11T12:30:00Z",
      "created_by": 2
    },
    /* ... 2 more assignments ... */
  ]
}
```

#### Error Response (400 Bad Request)
```json
{
  "success": false,
  "errors": {
    "workflow_assignments": [
      "Duplicate execution orders in assignment list"
    ]
  }
}
```

---

### 7. Reorder Workflow Assignments
**PUT** `/api/approvals/workflow-assignments/reorder/`

Change the execution order of existing workflow assignments.

#### Request Body
```json
{
  "security_group_id": 1,
  "assignment_orders": [
    {
      "assignment_id": 10,
      "execution_order": 2
    },
    {
      "assignment_id": 11,
      "execution_order": 1
    },
    {
      "assignment_id": 12,
      "execution_order": 3
    }
  ]
}
```

#### Response
```json
{
  "success": true,
  "message": "Reordered 3 workflow assignment(s)",
  "assignments": [
    {
      "id": 11,
      "execution_order": 1,
      /* ... */
    },
    {
      "id": 10,
      "execution_order": 2,
      /* ... */
    },
    {
      "id": 12,
      "execution_order": 3,
      /* ... */
    }
  ]
}
```

---

## Usage Examples

### Example 1: Assign Single Workflow to Group
```javascript
// Assign "FAR Approval Workflow" to "Finance Team"
const response = await fetch('/api/approvals/workflow-assignments/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer YOUR_TOKEN'
  },
  body: JSON.stringify({
    security_group: 1,  // Finance Team
    workflow_template: 5,  // FAR Approval Workflow
    execution_order: 1,
    is_active: true
  })
});

const data = await response.json();
console.log(data.message);  // "Workflow assignment created successfully"
```

### Example 2: Setup Sequential Workflows
```javascript
// Assign 3 workflows to execute sequentially
const response = await fetch('/api/approvals/workflow-assignments/bulk-assign/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer YOUR_TOKEN'
  },
  body: JSON.stringify({
    security_group_id: 1,
    workflow_assignments: [
      { workflow_template_id: 5, execution_order: 1 },  // Primary approval
      { workflow_template_id: 6, execution_order: 2 },  // Secondary review
      { workflow_template_id: 7, execution_order: 3 }   // Final sign-off
    ]
  })
});

// Now when Finance Team creates a transfer:
// 1. Workflow 5 starts immediately
// 2. When Workflow 5 completes → Workflow 6 starts automatically
// 3. When Workflow 6 completes → Workflow 7 starts automatically
```

### Example 3: Get Group's Workflows
```javascript
// Get all workflows assigned to Finance Team (group_id=1)
const response = await fetch('/api/approvals/workflow-assignments/?security_group=1', {
  headers: {
    'Authorization': 'Bearer YOUR_TOKEN'
  }
});

const data = await response.json();
console.log(`Group has ${data.count} workflow(s)`);
data.assignments.forEach(assignment => {
  console.log(`${assignment.execution_order}. ${assignment.workflow_template_name}`);
});
```

### Example 4: Reorder Workflows
```javascript
// Swap execution order of two workflows
const response = await fetch('/api/approvals/workflow-assignments/reorder/', {
  method: 'PUT',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer YOUR_TOKEN'
  },
  body: JSON.stringify({
    security_group_id: 1,
    assignment_orders: [
      { assignment_id: 10, execution_order: 2 },  // Move to position 2
      { assignment_id: 11, execution_order: 1 }   // Move to position 1
    ]
  })
});
```

---

## Important Notes

### Sequential Execution
- Workflows execute in order based on `execution_order` (1, 2, 3...)
- Next workflow **auto-starts** when previous completes
- If Workflow 2 is rejected, Workflow 3 will NOT start

### Bulk Assignment Behavior
- **REPLACES** all existing assignments for the group
- Use with caution - deletes old assignments first
- Atomic operation (all-or-nothing)

### Validation Rules
- Each group can have max ONE assignment per workflow template
- Execution orders must be unique within a group
- Workflow template must be active
- Security group must be active

---

## Frontend Integration

### React Example: Workflow Assignment Manager
```typescript
import { useState, useEffect } from 'react';

interface WorkflowAssignment {
  id: number;
  workflow_template_name: string;
  execution_order: number;
}

function WorkflowAssignmentManager({ securityGroupId }: { securityGroupId: number }) {
  const [assignments, setAssignments] = useState<WorkflowAssignment[]>([]);

  useEffect(() => {
    fetch(`/api/approvals/workflow-assignments/?security_group=${securityGroupId}`)
      .then(res => res.json())
      .then(data => setAssignments(data.assignments));
  }, [securityGroupId]);

  return (
    <div>
      <h3>Assigned Workflows (Sequential Execution)</h3>
      <ol>
        {assignments.map(assignment => (
          <li key={assignment.id}>
            {assignment.workflow_template_name}
          </li>
        ))}
      </ol>
    </div>
  );
}
```

---

## Testing Checklist

- [ ] Create single workflow assignment
- [ ] Create multiple assignments with bulk-assign
- [ ] Update assignment execution_order
- [ ] Reorder assignments
- [ ] Delete assignment
- [ ] Verify duplicate prevention
- [ ] Test sequential workflow execution (create transfer → verify workflows start in order)
- [ ] Test API with invalid security_group_id
- [ ] Test API with invalid workflow_template_id
- [ ] Test permission checks (non-authenticated users)

---

**Created**: December 11, 2025  
**Version**: Phase 6.0  
**Status**: Ready for Testing
