"""
Script to check FAR-0244 details and assignments
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_transfer.settings')
django.setup()

from budget_management.models import xx_BudgetTransfer
from approvals.models import ApprovalWorkflowInstance, ApprovalWorkflowStageInstance, ApprovalAssignment
from user_management.models import xx_User, XX_UserGroupMembership

print("\n=== CHECKING FAR-0244 DETAILS ===\n")

# Find FAR-0244
transfer = xx_BudgetTransfer.objects.filter(code='FAR-0244').first()

if not transfer:
    print("❌ FAR-0244 not found!")
else:
    print(f"✅ Transfer found: {transfer.code} (ID: {transfer.transaction_id})")
    print(f"   Security Group ID: {transfer.security_group_id}")
    print(f"   Security Group Name: {transfer.security_group.group_name if transfer.security_group else 'None'}")
    print(f"   Status: {transfer.status}")
    print(f"   Requested by: {transfer.requested_by}")
    
    # Check workflow instance
    workflow = transfer.workflow_instance
    if not workflow:
        print("\n❌ No workflow instance found for this transfer")
    else:
        template_name = getattr(workflow.template, 'name', 'Unknown') if hasattr(workflow, 'template') else 'Unknown'
        print(f"\n✅ Workflow Instance (ID: {workflow.id})")
        print(f"   Template: {template_name}")
        print(f"   Status: {workflow.status}")
        
        # Get all stages
        stages = workflow.stage_instances.all()
        print(f"\n📋 Workflow Stages ({stages.count()}):")
        
        for stage in stages:
            stage_template = stage.stage_template
            print(f"\n   Stage: {stage_template.name}")
            print(f"   Required user level: {stage_template.required_user_level.name if stage_template.required_user_level else 'None'}")
            print(f"   Required user level ID: {stage_template.required_user_level_id}")
            print(f"   Stage Status: {stage.status}")
            
            # Get assignments for this stage
            assignments = stage.assignments.all()
            print(f"   Assignments ({assignments.count()}):")
            for assignment in assignments:
                print(f"      - User: {assignment.user.username}")
                print(f"        Status: {assignment.status}")
                print(f"        Assigned at: {assignment.assigned_at}")
                
                # Check user's roles in the transfer's security group
                if transfer.security_group_id:
                    memberships = XX_UserGroupMembership.objects.filter(
                        user=assignment.user,
                        security_group_id=transfer.security_group_id,
                        is_active=True
                    )
                    
                    if memberships.exists():
                        membership = memberships.first()
                        user_role_ids = list(membership.assigned_roles.values_list('role_id', flat=True))
                        user_role_names = [r.role.name for r in membership.assigned_roles.all()]
                        print(f"        User's roles in {transfer.security_group.group_name}: {user_role_names} (IDs: {user_role_ids})")
                        
                        required_level_id = stage_template.required_user_level_id if stage_template else None
                        if required_level_id:
                            if required_level_id in user_role_ids:
                                print(f"        ✅ MATCH: User has required role {required_level_id}")
                            else:
                                print(f"        ❌ MISMATCH: User needs role {required_level_id} but has {user_role_ids}")
                    else:
                        print(f"        ⚠️  User is NOT a member of {transfer.security_group.group_name}")

print("\n=== CHECKING 'finance manager' USER ===\n")

fm_user = xx_User.objects.filter(username='finance manager').first()
if fm_user:
    print(f"User: {fm_user.username} (ID: {fm_user.id})")
    print(f"User level: {fm_user.user_level.name if fm_user.user_level else 'None'} (ID: {fm_user.user_level_id})")
    
    memberships = XX_UserGroupMembership.objects.filter(user=fm_user, is_active=True)
    print(f"\nSecurity Groups ({memberships.count()}):")
    for membership in memberships:
        print(f"\n  Group: {membership.security_group.group_name} (ID: {membership.security_group_id})")
        roles = membership.assigned_roles.all()
        for role in roles:
            print(f"    - Role: {role.role.name} (ID: {role.role_id})")
