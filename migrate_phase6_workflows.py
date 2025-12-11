"""
Data migration script for Phase 6: Convert existing workflows to new structure

This script helps migrate existing ApprovalWorkflowInstance records to the new
ForeignKey structure and sets default execution_order.

IMPORTANT: Run this AFTER applying the schema migration!

Usage:
    python migrate_phase6_workflows.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_transfer.settings')
django.setup()

from approvals.models import ApprovalWorkflowInstance, XX_WorkflowTemplateAssignment, ApprovalWorkflowTemplate
from budget_management.models import xx_BudgetTransfer
from user_management.models import XX_SecurityGroup

def migrate_workflow_instances():
    """Set execution_order=1 for all existing workflow instances"""
    print("\n" + "="*80)
    print("PHASE 6 DATA MIGRATION: Workflow Instances")
    print("="*80)
    
    # Update all existing workflow instances to have execution_order=1
    updated = ApprovalWorkflowInstance.objects.filter(
        execution_order__isnull=True
    ).update(execution_order=1)
    
    print(f"\n✅ Set execution_order=1 for {updated} existing workflow instances")
    
    # Show summary
    total_workflows = ApprovalWorkflowInstance.objects.count()
    print(f"\nTotal workflow instances: {total_workflows}")
    
    # Check for transfers with multiple workflows (shouldn't exist yet)
    from django.db.models import Count
    transfers_with_multiple = xx_BudgetTransfer.objects.annotate(
        workflow_count=Count('workflow_instances')
    ).filter(workflow_count__gt=1)
    
    if transfers_with_multiple.exists():
        print(f"\n⚠️  WARNING: {transfers_with_multiple.count()} transfers have multiple workflows")
        for transfer in transfers_with_multiple[:5]:
            print(f"   - Transfer {transfer.code}: {transfer.workflow_instances.count()} workflows")
    else:
        print(f"\n✅ No transfers have multiple workflows (as expected for existing data)")


def create_sample_workflow_assignments():
    """
    Optional: Create sample workflow template assignments
    
    This creates XX_WorkflowTemplateAssignment records for each security group
    based on their existing workflow templates.
    
    NOTE: Only run this if you want to automatically assign existing workflows!
    """
    print("\n" + "="*80)
    print("OPTIONAL: Create Sample Workflow Assignments")
    print("="*80)
    
    try:
        response = input("\nDo you want to auto-create workflow assignments for all security groups? (y/N): ")
    except EOFError:
        print("Skipped auto-creation of workflow assignments (non-interactive mode).")
        return
    
    if response.lower() != 'y':
        print("Skipped auto-creation of workflow assignments.")
        return
    
    created_count = 0
    security_groups = XX_SecurityGroup.objects.filter(is_active=True)
    
    for group in security_groups:
        # Get transfers in this group
        transfers = xx_BudgetTransfer.objects.filter(security_group=group)
        
        if not transfers.exists():
            print(f"\n⏭️  Skipping '{group.group_name}' - no transfers")
            continue
        
        # Get unique workflow templates used by this group's transfers
        workflow_templates = set()
        for transfer in transfers:
            # Get active workflow instance
            workflow = transfer.workflow_instance  # Uses property
            if workflow and workflow.template:
                workflow_templates.add(workflow.template)
        
        if not workflow_templates:
            print(f"\n⏭️  Skipping '{group.group_name}' - no active workflows")
            continue
        
        print(f"\n📋 Security Group: {group.group_name}")
        print(f"   Found {len(workflow_templates)} unique workflow template(s)")
        
        # Create assignments (all with execution_order=1 since they're existing)
        for idx, template in enumerate(sorted(workflow_templates, key=lambda t: t.code), start=1):
            assignment, created = XX_WorkflowTemplateAssignment.objects.get_or_create(
                security_group=group,
                workflow_template=template,
                defaults={
                    'execution_order': idx,
                    'is_active': True,
                    'created_by': None  # System migration
                }
            )
            
            if created:
                print(f"   ✅ Created: {template.code} (Order: {idx})")
                created_count += 1
            else:
                print(f"   ℹ️  Already exists: {template.code}")
    
    print(f"\n✅ Created {created_count} new workflow assignment(s)")


def show_summary():
    """Display migration summary"""
    print("\n" + "="*80)
    print("MIGRATION SUMMARY")
    print("="*80)
    
    total_workflows = ApprovalWorkflowInstance.objects.count()
    total_assignments = XX_WorkflowTemplateAssignment.objects.count()
    total_groups = XX_SecurityGroup.objects.filter(is_active=True).count()
    
    print(f"\n📊 Statistics:")
    print(f"   - Total workflow instances: {total_workflows}")
    print(f"   - Total workflow assignments: {total_assignments}")
    print(f"   - Total active security groups: {total_groups}")
    
    # Show groups with assignments
    groups_with_workflows = XX_SecurityGroup.objects.filter(
        workflow_assignments__isnull=False
    ).distinct().count()
    
    print(f"   - Security groups with workflows assigned: {groups_with_workflows}")
    
    if total_assignments > 0:
        print(f"\n📋 Workflow Assignments by Group:")
        for group in XX_SecurityGroup.objects.filter(workflow_assignments__isnull=False).distinct():
            assignments = group.workflow_assignments.order_by('execution_order')
            print(f"\n   {group.group_name}:")
            for assignment in assignments:
                print(f"      {assignment.execution_order}. {assignment.workflow_template.code} ({assignment.workflow_template.name})")


if __name__ == '__main__':
    print("\n" + "="*80)
    print("PHASE 6: WORKFLOW DATA MIGRATION SCRIPT")
    print("="*80)
    print("\nThis script will:")
    print("1. Set execution_order=1 for existing workflow instances")
    print("2. Optionally create workflow assignments for security groups")
    print("\nMAKE SURE you have:")
    print("✅ Applied the schema migration: python manage.py migrate")
    print("✅ Backed up your database")
    print("\n" + "="*80)
    
    try:
        response = input("\nProceed with migration? (y/N): ")
    except EOFError:
        response = 'y'
        print("\nNon-interactive mode: Auto-proceeding with migration...")
    
    if response.lower() != 'y':
        print("\n❌ Migration cancelled.")
        exit(0)
    
    try:
        # Step 1: Migrate workflow instances
        migrate_workflow_instances()
        
        # Step 2: Optionally create assignments
        create_sample_workflow_assignments()
        
        # Step 3: Show summary
        show_summary()
        
        print("\n" + "="*80)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY")
        print("="*80)
        print("\nNext steps:")
        print("1. Test workflow creation with new transfers")
        print("2. Verify sequential workflow execution")
        print("3. Update frontend to use new workflow assignment UI")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ ERROR during migration: {str(e)}")
        import traceback
        traceback.print_exc()
        print("\n⚠️  Migration may be incomplete. Check database state!")
