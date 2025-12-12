"""
Clear required_user_level from all workflow stage templates
so they only use security_group for access control
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_transfer.settings')
django.setup()

from approvals.models import ApprovalWorkflowStageTemplate

print("\n" + "="*80)
print("🔧 CLEARING required_user_level FROM ALL WORKFLOW STAGES")
print("="*80)

stages = ApprovalWorkflowStageTemplate.objects.all()

print(f"\nTotal workflow stages: {stages.count()}")

updated_count = 0
for stage in stages:
    if stage.required_user_level:
        print(f"\n📝 Stage: {stage.name}")
        print(f"   Template: {stage.workflow_template.name}")
        print(f"   Current required_user_level: {stage.required_user_level.name}")
        print(f"   Security Group: {stage.security_group.group_name if stage.security_group else 'None'}")
        
        # Clear the required_user_level
        stage.required_user_level = None
        stage.save()
        
        print(f"   ✅ Cleared required_user_level")
        updated_count += 1

print(f"\n" + "="*80)
print(f"✅ Updated {updated_count} stage(s)")
print(f"Now access control is based ONLY on security_group membership")
print("="*80 + "\n")
