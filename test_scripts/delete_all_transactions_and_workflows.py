"""
Script to delete all transactions and workflow templates/stages from the database.
WARNING: This will permanently delete all data. Use with caution!
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_transfer.settings')
django.setup()

from budget_management.models import xx_BudgetTransfer, xx_BudgetTransferAttachment, xx_BudgetTransferRejectReason
from transaction.models import xx_TransactionTransfer
from approvals.models import (
    ApprovalWorkflowTemplate,
    ApprovalWorkflowStageTemplate,
    ApprovalWorkflowInstance,
    ApprovalWorkflowStageInstance,
    ApprovalAssignment,
    ApprovalAction,
    ApprovalDelegation
)
from account_and_entitys.models import XX_TransactionSegment

print("\n" + "="*80)
print("⚠️  WARNING: DATABASE CLEANUP SCRIPT")
print("="*80)
print("\nThis script will DELETE ALL:")
print("  - Budget Transfers (xx_BudgetTransfer)")
print("  - Transaction Transfers (xx_TransactionTransfer)")
print("  - Transaction Segments (XX_TransactionSegment)")
print("  - Workflow Templates (ApprovalWorkflowTemplate)")
print("  - Workflow Stage Templates (ApprovalWorkflowStageTemplate)")
print("  - Workflow Instances (ApprovalWorkflowInstance)")
print("  - Workflow Stage Instances (ApprovalWorkflowStageInstance)")
print("  - Approval Assignments (ApprovalAssignment)")
print("  - Approval Actions (ApprovalAction)")
print("  - Approval Delegations (ApprovalDelegation)")
print("  - Budget Transfer Attachments (xx_BudgetTransferAttachment)")
print("  - Budget Transfer Reject Reasons (xx_BudgetTransferRejectReason)")
print("\n" + "="*80)

# Get counts before deletion
counts = {
    'budget_transfers': xx_BudgetTransfer.objects.count(),
    'transaction_transfers': xx_TransactionTransfer.objects.count(),
    'transaction_segments': XX_TransactionSegment.objects.count(),
    'workflow_templates': ApprovalWorkflowTemplate.objects.count(),
    'workflow_stage_templates': ApprovalWorkflowStageTemplate.objects.count(),
    'workflow_instances': ApprovalWorkflowInstance.objects.count(),
    'workflow_stage_instances': ApprovalWorkflowStageInstance.objects.count(),
    'approval_assignments': ApprovalAssignment.objects.count(),
    'approval_actions': ApprovalAction.objects.count(),
    'approval_delegations': ApprovalDelegation.objects.count(),
    'budget_transfer_attachments': xx_BudgetTransferAttachment.objects.count(),
    'budget_transfer_reject_reasons': xx_BudgetTransferRejectReason.objects.count(),
}

print("\n📊 CURRENT DATABASE COUNTS:")
for name, count in counts.items():
    print(f"  {name.replace('_', ' ').title()}: {count}")

if sum(counts.values()) == 0:
    print("\n✅ Database is already empty. Nothing to delete.")
    exit(0)

print("\n" + "="*80)
response = input("\n❓ Are you sure you want to DELETE ALL this data? Type 'DELETE ALL' to confirm: ")

if response != 'DELETE ALL':
    print("\n❌ Deletion cancelled. No data was removed.")
    exit(0)

print("\n🗑️  Starting deletion process...\n")

try:
    # Delete in reverse order of dependencies
    
    print("1️⃣  Deleting Approval Delegations...")
    deleted = ApprovalDelegation.objects.all().delete()
    print(f"   ✅ Deleted {deleted[0]} approval delegations")
    
    print("\n2️⃣  Deleting Approval Actions...")
    deleted = ApprovalAction.objects.all().delete()
    print(f"   ✅ Deleted {deleted[0]} approval actions")
    
    print("\n3️⃣  Deleting Approval Assignments...")
    deleted = ApprovalAssignment.objects.all().delete()
    print(f"   ✅ Deleted {deleted[0]} approval assignments")
    
    print("\n4️⃣  Deleting Workflow Stage Instances...")
    deleted = ApprovalWorkflowStageInstance.objects.all().delete()
    print(f"   ✅ Deleted {deleted[0]} workflow stage instances")
    
    print("\n5️⃣  Deleting Workflow Instances...")
    deleted = ApprovalWorkflowInstance.objects.all().delete()
    print(f"   ✅ Deleted {deleted[0]} workflow instances")
    
    print("\n6️⃣  Deleting Workflow Stage Templates...")
    deleted = ApprovalWorkflowStageTemplate.objects.all().delete()
    print(f"   ✅ Deleted {deleted[0]} workflow stage templates")
    
    print("\n7️⃣  Deleting Workflow Templates...")
    deleted = ApprovalWorkflowTemplate.objects.all().delete()
    print(f"   ✅ Deleted {deleted[0]} workflow templates")
    
    print("\n8️⃣  Deleting Transaction Segments...")
    deleted = XX_TransactionSegment.objects.all().delete()
    print(f"   ✅ Deleted {deleted[0]} transaction segments")
    
    print("\n9️⃣  Deleting Transaction Transfers...")
    deleted = xx_TransactionTransfer.objects.all().delete()
    print(f"   ✅ Deleted {deleted[0]} transaction transfers")
    
    print("\n🔟 Deleting Budget Transfer Attachments...")
    deleted = xx_BudgetTransferAttachment.objects.all().delete()
    print(f"   ✅ Deleted {deleted[0]} budget transfer attachments")
    
    print("\n1️⃣1️⃣  Deleting Budget Transfer Reject Reasons...")
    deleted = xx_BudgetTransferRejectReason.objects.all().delete()
    print(f"   ✅ Deleted {deleted[0]} budget transfer reject reasons")
    
    print("\n1️⃣2️⃣  Deleting Budget Transfers...")
    deleted = xx_BudgetTransfer.objects.all().delete()
    print(f"   ✅ Deleted {deleted[0]} budget transfers")
    
    print("\n" + "="*80)
    print("✅ SUCCESS: All transactions and workflows have been deleted!")
    print("="*80)
    
    # Verify deletion
    print("\n📊 FINAL DATABASE COUNTS:")
    final_counts = {
        'budget_transfers': xx_BudgetTransfer.objects.count(),
        'transaction_transfers': xx_TransactionTransfer.objects.count(),
        'transaction_segments': XX_TransactionSegment.objects.count(),
        'workflow_templates': ApprovalWorkflowTemplate.objects.count(),
        'workflow_stage_templates': ApprovalWorkflowStageTemplate.objects.count(),
        'workflow_instances': ApprovalWorkflowInstance.objects.count(),
        'workflow_stage_instances': ApprovalWorkflowStageInstance.objects.count(),
        'approval_assignments': ApprovalAssignment.objects.count(),
        'approval_actions': ApprovalAction.objects.count(),
        'approval_delegations': ApprovalDelegation.objects.count(),
    }
    
    for name, count in final_counts.items():
        status = "✅" if count == 0 else "⚠️"
        print(f"  {status} {name.replace('_', ' ').title()}: {count}")
    
    if sum(final_counts.values()) == 0:
        print("\n✅ Database cleanup complete! All data successfully removed.")
    else:
        print("\n⚠️  Warning: Some data may still remain. Check the counts above.")

except Exception as e:
    print(f"\n❌ ERROR during deletion: {e}")
    print("\n⚠️  Some data may have been deleted before the error occurred.")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "="*80)
print("🎉 Script completed successfully!")
print("="*80 + "\n")
