from django.core.management.base import BaseCommand
from user_management.models import xx_User
from approvals.managers import ApprovalManager


class Command(BaseCommand):
    help = 'Test pending approvals for a user'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username to test')

    def handle(self, *args, **options):
        username = options['username']
        
        try:
            user = xx_User.objects.get(username=username)
        except xx_User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User "{username}" not found'))
            return

        self.stdout.write("=" * 80)
        self.stdout.write(f"PENDING APPROVALS FOR USER: {user.username}")
        self.stdout.write("=" * 80)

        # Get pending approvals using the same method as the API
        pending_transfers = ApprovalManager.get_user_pending_approvals(user)
        
        self.stdout.write(f"\n📋 Total Pending Approvals: {pending_transfers.count()}")
        
        if pending_transfers.count() == 0:
            self.stdout.write(self.style.WARNING("⚠️  No pending approvals found!"))
        else:
            for transfer in pending_transfers:
                self.stdout.write(f"\n  ✅ {transfer.code}")
                self.stdout.write(f"     ID: {transfer.transaction_id}")
                self.stdout.write(f"     Security Group: {transfer.security_group.group_name}")
                self.stdout.write(f"     Creator: {transfer.requested_by}")
                self.stdout.write(f"     Status: {transfer.status}")

        self.stdout.write("\n" + "=" * 80)
