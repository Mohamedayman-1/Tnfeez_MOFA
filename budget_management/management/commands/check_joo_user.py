from django.core.management.base import BaseCommand
from user_management.models import xx_User, XX_UserGroupMembership, XX_SecurityGroup, XX_SecurityGroupRole


class Command(BaseCommand):
    help = 'Check user joo and Fusion Team configuration'

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write("CHECKING USER JOO AND FUSION TEAM")
        self.stdout.write("=" * 80)

        # Check if joo exists
        try:
            joo = xx_User.objects.get(username='joo')
            self.stdout.write(self.style.SUCCESS(f'\n✅ User "joo" exists (ID: {joo.id})'))
        except xx_User.DoesNotExist:
            self.stdout.write(self.style.ERROR('\n❌ User "joo" does not exist!'))
            joo = None

        # Check joo's group memberships
        if joo:
            memberships = XX_UserGroupMembership.objects.filter(user=joo, is_active=True)
            self.stdout.write(f'\n📋 Group Memberships: {memberships.count()}')
            for m in memberships:
                self.stdout.write(f'  - {m.security_group.group_name}')
                roles = m.assigned_roles.all()
                for role in roles:
                    self.stdout.write(f'    Role: {role}')

        # Check Fusion Team groups
        self.stdout.write('\n📋 Fusion Team Security Groups:')
        fusion_groups = XX_SecurityGroup.objects.filter(group_name__icontains='fusion')
        if fusion_groups.count() == 0:
            self.stdout.write(self.style.WARNING('  ⚠️  No Fusion Team groups found!'))
        else:
            for group in fusion_groups:
                self.stdout.write(f'\n  🔹 {group.group_name} (ID: {group.id})')
                
                # Check roles in this group
                group_roles = XX_SecurityGroupRole.objects.filter(security_group=group)
                self.stdout.write(f'     Available Roles: {group_roles.count()}')
                for gr in group_roles:
                    self.stdout.write(f'       - {gr}')
                
                # Check members
                members = XX_UserGroupMembership.objects.filter(security_group=group, is_active=True)
                self.stdout.write(f'     Members: {members.count()}')
                for member in members:
                    self.stdout.write(f'       - {member.user.username}')

        self.stdout.write("\n" + "=" * 80)
