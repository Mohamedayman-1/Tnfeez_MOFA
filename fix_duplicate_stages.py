"""
Fix duplicate workflow stages in FAR workflow template.

This script removes duplicate stages with order_index 10000 and 10001
that are causing duplicate stage display in the frontend.
"""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from approvals.models import ApprovalWorkflowTemplate, ApprovalWorkflowStageTemplate

def fix_duplicate_stages():
    """Remove duplicate FAR workflow stages with high order_index values."""
    
    print("=" * 60)
    print("FIXING DUPLICATE WORKFLOW STAGES")
    print("=" * 60)
    
    # Get FAR workflow
    try:
        far_workflow = ApprovalWorkflowTemplate.objects.get(code='FAR')
    except ApprovalWorkflowTemplate.DoesNotExist:
        print("❌ FAR workflow not found!")
        return
    
    # Show current stages
    print(f"\n📋 Current stages in FAR workflow:")
    stages = far_workflow.stages.all().order_by('order_index')
    for stage in stages:
        print(f"  • Order {stage.order_index}: {stage.name} (ID: {stage.id})")
    
    # Identify duplicate stages (order_index >= 10000)
    duplicate_stages = far_workflow.stages.filter(order_index__gte=10000).order_by('order_index')
    
    if not duplicate_stages.exists():
        print("\n✅ No duplicate stages found!")
        return
    
    print(f"\n⚠️  Found {duplicate_stages.count()} duplicate stages:")
    for stage in duplicate_stages:
        print(f"  • Order {stage.order_index}: {stage.name} (ID: {stage.id})")
    
    # Confirm deletion
    print("\n🗑️  These stages will be DELETED.")
    confirm = input("Continue? (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("❌ Operation cancelled.")
        return
    
    # Delete duplicate stages
    deleted_count = 0
    for stage in duplicate_stages:
        print(f"  Deleting: Order {stage.order_index} - {stage.name}")
        stage.delete()
        deleted_count += 1
    
    print(f"\n✅ Successfully deleted {deleted_count} duplicate stages!")
    
    # Show final stages
    print(f"\n📋 Final stages in FAR workflow:")
    final_stages = far_workflow.stages.all().order_by('order_index')
    for stage in final_stages:
        print(f"  • Order {stage.order_index}: {stage.name} (ID: {stage.id})")
    
    print("\n" + "=" * 60)
    print("✅ FIX COMPLETE!")
    print("=" * 60)
    print("\nThe frontend status modals will now show correct stages without duplicates.")

if __name__ == "__main__":
    fix_duplicate_stages()
