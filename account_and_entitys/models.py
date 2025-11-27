from django.db import models

from approvals.models import ApprovalWorkflowInstance
from transaction.models import xx_TransactionTransfer

# Removed encrypted fields import - using standard Django fields now


class XX_Account(models.Model):
    """Model representing ADJD accounts"""

    account = models.CharField(max_length=50, unique=False)
    parent = models.CharField(
        max_length=50, null=True, blank=True
    )  # Changed from EncryptedCharField
    alias_default = models.CharField(
        max_length=255, null=True, blank=True
    )  # Changed from EncryptedCharField

    def __str__(self):
        return str(self.account)

    class Meta:
        db_table = "XX_ACCOUNT_XX"


class XX_Entity(models.Model):
    """Model representing ADJD entities"""

    entity = models.CharField(max_length=50, unique=False)
    parent = models.CharField(
        max_length=50, null=True, blank=True
    )  # Changed from EncryptedCharField
    alias_default = models.CharField(
        max_length=255, null=True, blank=True
    )  # Changed from EncryptedCharField

    def __str__(self):
        return str(self.entity)

    class Meta:
        db_table = "XX_ENTITY_XX"


class XX_Project(models.Model):
    """Model representing ADJD entities"""

    project = models.CharField(max_length=50, unique=False)
    parent = models.CharField(
        max_length=50, null=True, blank=True
    )  # Changed from EncryptedCharField
    alias_default = models.CharField(
        max_length=255, null=True, blank=True
    )  # Changed from EncryptedCharField

    def __str__(self):
        return str(self.project)

    class Meta:
        db_table = "XX_PROJECT_XX"


class Project_Envelope(models.Model):
    """Model representing ADJD entities"""

    project = models.CharField(max_length=50, unique=False)
    envelope = models.DecimalField(
        max_digits=30, decimal_places=2
    )  # Changed from EncryptedCharField

    def __str__(self):
        return str(self.project)

    class Meta:
        db_table = "XX_PROJECT_ENVELOPE_XX"


class Account_Mapping(models.Model):
    """Model representing ADJD account mappings"""

    source_account = models.CharField(max_length=50, unique=False)
    target_account = models.CharField(max_length=50, unique=False)

    def __str__(self):
        return f"{self.source_account} -> {self.target_account}"

    class Meta:
        db_table = "XX_ACCOUNT_MAPPING_LEGACY_XX"
        unique_together = ("source_account", "target_account")


class Budget_data(models.Model):
    project = models.CharField(max_length=50, unique=False)
    account = models.CharField(max_length=50, unique=False)
    FY24_budget = models.DecimalField(max_digits=30, decimal_places=2)
    FY25_budget = models.DecimalField(max_digits=30, decimal_places=2)

    class Meta:
        db_table = "BUDGET_DATA_XX"
        unique_together = ("project", "account")


class EnvelopeManager:
    @staticmethod
    def Has_Envelope(project_code):
        try:
            envelope_record = Project_Envelope.objects.get(project=project_code)
            return True
        except Project_Envelope.DoesNotExist:
            return False

    @staticmethod
    def Get_Envelope(project_code):
        try:
            envelope_record = Project_Envelope.objects.get(project=project_code)
            return envelope_record.envelope
        except Project_Envelope.DoesNotExist:
            return 0

    @staticmethod
    def __get_project_parent_code(project_code):
        try:
            parent_project = XX_Project.objects.get(project=project_code)
            return parent_project.parent
        except XX_Project.DoesNotExist:
            return None

    @staticmethod
    def get_all_children(all_projects, curr_code, visited=None):
        """Recursively get all descendants of a project code with cycle protection."""
        if visited is None:
            visited = set()
        if curr_code in visited:
            return []
        visited.add(curr_code)

        direct_children = list(
            all_projects.filter(parent=curr_code).values_list("project", flat=True)
        )

        descendants = []
        for child in direct_children:
            if child in visited:
                continue
            descendants.append(child)
            descendants.extend(
                EnvelopeManager.get_all_children(all_projects, child, visited)
            )
        return descendants

    @staticmethod
    def get_all_children_for_accounts(all_accounts, curr_code, visited=None):
        """Recursively get all descendants of an account code with cycle protection."""
        if visited is None:
            visited = set()
        if curr_code in visited:
            return []
        visited.add(curr_code)

        direct_children = list(
            all_accounts.filter(parent=curr_code).values_list("account", flat=True)
        )

        descendants = []
        for child in direct_children:
            if child in visited:
                continue
            descendants.append(child)
            descendants.extend(
                EnvelopeManager.get_all_children_for_accounts(
                    all_accounts, child, visited
                )
            )
        return descendants

    @staticmethod
    def __get_all_level_zero_children_code(project_code):
        """
        Get all leaf node project codes that are descendants of the given project_code.
        A leaf node is a project that has no children (no other projects have it as their parent).

        Args:
            project_code (str): The project code to find leaf descendants for

        Returns:
            list: List of project codes that are leaf nodes under the given project_code
        """
        try:
            # First verify the parent project exists
            XX_Project.objects.get(project=project_code)

            # Get all projects
            all_projects = XX_Project.objects.all()

            # Get all parent codes to identify which projects are not parents
            parent_codes = set(
                all_projects.exclude(parent__isnull=True)
                .values_list("parent", flat=True)
                .distinct()
            )

            # Get all descendants of the given project_code
            all_descendants = EnvelopeManager.get_all_children(
                all_projects, project_code
            )

            # Filter to only include descendants that are not parents themselves
            leaf_nodes = [code for code in all_descendants if code not in parent_codes]

            return leaf_nodes

        except XX_Project.DoesNotExist:
            return []

    @staticmethod
    def __get_all_children_codes(project_code):
        try:
            XX_Project.objects.only("project").get(project=project_code)

            pairs = XX_Project.objects.values_list("project", "parent")
            children_map = {}
            for proj, parent in pairs:
                children_map.setdefault(parent, []).append(proj)

            result = []
            stack = list(children_map.get(project_code, []))
            while stack:
                node = stack.pop()
                result.append(node)
                stack.extend(children_map.get(node, []))
            return result
        except XX_Project.DoesNotExist:
            return []

    @staticmethod
    def Get_First_Parent_Envelope(project_code):
        while project_code:
            try:
                if EnvelopeManager.Has_Envelope(project_code):
                    return project_code, EnvelopeManager.Get_Envelope(project_code)
                else:
                    project_code = EnvelopeManager.__get_project_parent_code(
                        project_code
                    )
            except XX_Project.DoesNotExist:
                project_code = None
        return None, None

    @staticmethod
    def Get_Envelope_Amount(project_code):
        envelope_amount = EnvelopeManager.Get_Envelope(project_code)
        if envelope_amount:
            return envelope_amount
        return 0

    @staticmethod
    def Get_All_Children_Accounts_with_Mapping(accounts):
        all_accounts = []
        for account in accounts:
            all_accounts.append(account)
            all_accounts.extend(
                EnvelopeManager.get_all_children_for_accounts(
                    XX_Account.objects.all(), account
                )
            )
        for account in all_accounts:
            if Account_Mapping.objects.filter(target_account=account).exists():
                mapped_accounts = Account_Mapping.objects.filter(
                    target_account=account
                ).values_list("source_account", flat=True)
                all_accounts.extend(list(mapped_accounts))
        return list(set(all_accounts))

    @staticmethod
    def Calculate_Transactions_total(base_transactions):
        from django.db.models import Sum, F, Value, Q
        from django.db.models.functions import Coalesce

        # Get approved transactions
        approved_transactions = base_transactions.filter(
            transaction__workflow_instance__status=ApprovalWorkflowInstance.STATUS_APPROVED
        )
        print(f"Approved transactions: {approved_transactions.count()}")
        # Get submitted (in progress) transactions
        submitted_transactions = base_transactions.filter(
            transaction__workflow_instance__status=ApprovalWorkflowInstance.STATUS_IN_PROGRESS
        )
        print(f"Submitted transactions: {submitted_transactions.count()}")
        # Calculate totals for approved transactions
        approved_result = approved_transactions.aggregate(
            total_from=Coalesce(
                Sum("from_center"), Value(0, output_field=models.DecimalField())
            ),
            total_to=Coalesce(
                Sum("to_center"), Value(0, output_field=models.DecimalField())
            ),
        )
        approved = {}
        approved["total_from"] = approved_result["total_from"] * -1
        approved["total_to"] = approved_result["total_to"]
        approved["total"] = approved["total_from"] + approved["total_to"]

        # Calculate totals for submitted transactions
        submitted_result = submitted_transactions.aggregate(
            total_from=Coalesce(
                Sum("from_center"), Value(0, output_field=models.DecimalField())
            ),
            total_to=Coalesce(
                Sum("to_center"), Value(0, output_field=models.DecimalField())
            ),
        )
        submitted = {}
        submitted["total_from"] = submitted_result["total_from"] * -1
        submitted["total_to"] = submitted_result["total_to"]
        submitted["total"] = submitted["total_from"] + submitted["total_to"]

        return approved, submitted

    @staticmethod
    def Get_Total_Amount_for_Project(
        project_code, year=None, month=None, FilterAccounts=True
    ):
        try:

            import calendar

            # Import here to avoid circular import at module import time
            from transaction.models import xx_TransactionTransfer

            if FilterAccounts:
                accounts = [
                    "TC11100T",  # Men Power
                    "TC11200T",  # Non Men Power
                    "TC13000T",  # Copex
                ]
                all_accounts = EnvelopeManager.Get_All_Children_Accounts_with_Mapping(
                    accounts
                )
                # Filter to keep only numeric accounts
                numeric_accounts = EnvelopeManager.__filter_numeric_accounts(
                    all_accounts
                )
                base_transactions = xx_TransactionTransfer.objects.filter(
                    project_code=project_code, account_code__in=numeric_accounts
                )
                # Start with base filter for project code
            else:
                base_transactions = xx_TransactionTransfer.objects.filter(
                    project_code=project_code
                )

            print(
                f"Base transactions count for project {project_code}: {base_transactions.count()}"
            )
            # Apply date filtering based on provided parameters
            if year is not None:
                base_transactions = base_transactions.filter(transaction__fy=year)

            if month is not None:
                month_abbr = calendar.month_abbr[
                    month
                ]  # Convert month number to abbreviation
                base_transactions = base_transactions.filter(
                    transaction__transaction_date=month_abbr
                )

            return EnvelopeManager.Calculate_Transactions_total(base_transactions)
        except Exception as e:
            print(f"Error calculating total amount for project {project_code}: {e}")
            return None, None

    @staticmethod
    def Get_Active_Projects(project_codes=None, year=None, month=None):
        """Return a list of distinct project codes used by transactions.

        Params:
            project_codes: optional list of project codes to filter by. If provided, only projects
                         from this list that have transactions will be returned.
            year: optional fiscal year (int or numeric string) — filters on transaction__fy
            month: optional month (int 1-12 or 3-letter abbreviation like 'Jan') — filters on transaction__transaction_date
            IsApproved: if True only include transactions whose parent budget transfer's workflow instance status is APPROVED,
                        otherwise include those in IN_PROGRESS.

        Returns:
            list of project_code strings (empty list on error)
        """
        try:
            import calendar

            # Import here to avoid circular import at module import time
            from transaction.models import xx_TransactionTransfer

            # desired_status = (
            #     ApprovalWorkflowInstance.STATUS_APPROVED
            #     if IsApproved
            #     else ApprovalWorkflowInstance.STATUS_IN_PROGRESS
            # )

            # transactions = xx_TransactionTransfer.objects.filter(
            #     transaction__workflow_instance__status=desired_status
            # )
            transactions = xx_TransactionTransfer.objects.all()
            # Filter by provided project codes if any
            if project_codes:
                transactions = transactions.filter(project_code__in=project_codes)

            # Apply year filter if provided
            if year is not None and year != "":
                try:
                    year_int = int(year)
                    transactions = transactions.filter(transaction__fy=year_int)
                except Exception:
                    # invalid year value; ignore filter but log
                    print(
                        f"Get_Active_Projects: invalid year value '{year}', skipping year filter"
                    )

            # Apply month filter if provided; accept month as int or 3-letter name
            if month is not None and month != "":
                month_abbr = None
                try:
                    if isinstance(month, str):
                        m = month.strip()
                        if len(m) == 3:
                            month_abbr = m[:3]
                        else:
                            month_int = int(m)
                            if 1 <= month_int <= 12:
                                month_abbr = calendar.month_abbr[month_int]
                    else:
                        month_int = int(month)
                        if 1 <= month_int <= 12:
                            month_abbr = calendar.month_abbr[month_int]
                except Exception:
                    print(
                        f"Get_Active_Projects: invalid month value '{month}', skipping month filter"
                    )

                if month_abbr:
                    transactions = transactions.filter(
                        transaction__transaction_date=month_abbr
                    )

            # Return plain list of distinct project codes
            project_qs = transactions.values_list("project_code", flat=True).distinct()
            return list(project_qs)

        except Exception as e:
            # Don't raise to avoid breaking import-time usage; log and return empty list
            print(f"Error in Get_Active_Projects: {e}")
            return []

    @staticmethod
    def Get_Current_Envelope_For_Project(project_code, year=None, month=None):
        try:
            parent_project, envelope = EnvelopeManager.Get_First_Parent_Envelope(
                project_code
            )
            if envelope is None:
                return None
            Children_projects = EnvelopeManager.__get_all_level_zero_children_code(
                parent_project
            )
            active_projects = EnvelopeManager.Get_Active_Projects(
                project_codes=Children_projects, year=year, month=month
            )

            # Initialize dictionary to store results for all projects
            projects_totals = {}

            # Get totals for each active project
            for proj in active_projects:
                approved, submitted = EnvelopeManager.Get_Total_Amount_for_Project(
                    proj, year=year, month=month
                )
                projects_totals[proj] = {
                    "approved": (
                        approved
                        if approved
                        else {"total": 0, "total_from": 0, "total_to": 0}
                    ),
                    "submitted": (
                        submitted
                        if submitted
                        else {"total": 0, "total_from": 0, "total_to": 0}
                    ),
                }

            current_envelope = envelope
            estimated_envelope = envelope
            for proj, totals in projects_totals.items():
                current_envelope += totals["approved"]["total"]
                estimated_envelope += totals["approved"]["total"]
                estimated_envelope += totals["submitted"]["total"]
            return {
                "initial_envelope": envelope,
                "current_envelope": current_envelope,
                "estimated_envelope": estimated_envelope,
                "project_totals": projects_totals,
            }
        except Project_Envelope.DoesNotExist:
            return None

    @staticmethod
    def Get_Budget_for_Project(project_code):
        from django.db.models import Sum

        budget_totals = Budget_data.objects.filter(project=project_code).aggregate(
            FY24_total=Sum("FY24_budget"), FY25_total=Sum("FY25_budget")
        )
        return {
            "FY24_budget": budget_totals["FY24_total"] or 0,
            "FY25_budget_initial": budget_totals["FY25_total"] or 0,
        }

    @staticmethod
    def Get_Total_Amount_for_Entity(entity_code):
        try:
            from django.db.models import Sum, F, Value, Q
            from django.db.models.functions import Coalesce
            import calendar

            # Import here to avoid circular import at module import time
            from transaction.models import xx_TransactionTransfer

            base_transactions = xx_TransactionTransfer.objects.filter(
                cost_center_code=entity_code,
            )
            project_codes = list(
                base_transactions.values_list("project_code", flat=True).distinct()
            )

            data = {}
            for proj in project_codes:
                # Get transaction totals
                approved, submitted = EnvelopeManager.Get_Total_Amount_for_Project(
                    proj, FilterAccounts=False
                )
                if approved is None or submitted is None:
                    continue

                # Get budget data
                budget_data = EnvelopeManager.Get_Budget_for_Project(proj)

                data[proj] = {
                    # FY24 data
                    "FY24_budget": budget_data.get("FY24_budget", 0),
                    # FY25 data
                    "FY25_budget_current": budget_data.get("FY25_budget_initial", 0)
                    + approved["total"],
                    "variances": budget_data.get("FY24_budget", 0)
                    - (budget_data.get("FY25_budget_initial", 0) + approved["total"]),
                }
            return data

        except Exception as e:
            print(f"Error calculating total amount for entity {entity_code}: {e}")
            return None, None

    @staticmethod
    def Get_Dashboard_Data_For_Entity(entity_code):
        result = EnvelopeManager.Get_Total_Amount_for_Entity(entity_code)
        if not result:
            return []

        dashboard_data = []
        for project_code, project_data in result.items():
            # Try to get project name, fallback to project code if not found
            try:
                project = XX_Project.objects.get(project=project_code)
                project_name = project.alias_default or project_code
            except XX_Project.DoesNotExist:
                project_name = project_code

            dashboard_data.append(
                {
                    "project_code": project_code,
                    "project_name": project_name,
                    "FY24_budget": project_data["FY24_budget"],
                    "FY25_budget_current": project_data["FY25_budget_current"],
                    "variances": project_data["variances"],
                }
            )

        return dashboard_data

    @staticmethod
    def Get_Dashboard_Data_For_Account(transfers_for_project, project_code, Accounts):
        result = []
        total_submitted = 0
        total_approved = 0
        total_fy25_budget = 0
        total_fy24_budget = 0
        print(
            f"Calculating dashboard data for project {project_code} and accounts: {Accounts}"
        )
        for acc in Accounts:
            approved, submitted = ({"total": 0}, {"total": 0})
            if acc.isdigit():
                Transfers_for_projects_and_accounts = transfers_for_project.filter(
                    account_code=acc
                )
                approved, submitted = EnvelopeManager.Calculate_Transactions_total(
                    Transfers_for_projects_and_accounts
                )
            mapped_acc = Account_Mapping.objects.filter(source_account=acc).first()
            if mapped_acc:
                acc = mapped_acc.target_account
            from django.db.models import Sum

            budget_data = Budget_data.objects.filter(
                project=project_code, account=acc
            ).aggregate(fy24_total=Sum("FY24_budget"), fy25_total=Sum("FY25_budget"))
            print(
                f"Budget data for project {project_code}, account {acc}: {budget_data}"
            )

            fy24_budget = budget_data["fy24_total"] or 0
            fy25_budget = budget_data["fy25_total"] or 0
            if approved["total"] == 0 and fy24_budget == 0 and fy25_budget == 0:
                continue
            result.append(
                {
                    "account": acc,
                    "account_name": (
                        XX_Account.objects.filter(account=acc).first().alias_default
                        if XX_Account.objects.filter(account=acc).first()
                        else acc
                    ),
                    "approved_total": approved["total"] if approved else 0,
                    "FY24_budget": fy24_budget,
                    "FY25_budget": fy25_budget + approved["total"] if approved else 0,
                }
            )
            total_submitted += submitted["total"] if submitted else 0
            total_approved += approved["total"] if approved else 0
            total_fy25_budget += fy25_budget + approved["total"] if approved else 0
            total_fy24_budget += fy24_budget
        return (
            total_approved,
            total_submitted,
            total_fy25_budget,
            total_fy24_budget,
            result,
        )

    @staticmethod
    def __filter_numeric_accounts(accounts):
        """Helper function to filter accounts that contain only numbers"""
        return [acc for acc in accounts if acc.isdigit()]

    @staticmethod
    def Get_Dashboard_Data_For_Project(project_code):
        MenPowerAccounts = EnvelopeManager.Get_All_Children_Accounts_with_Mapping(
            ["TC11100T"]
        )

        NonMenPowerAccounts = EnvelopeManager.Get_All_Children_Accounts_with_Mapping(
            ["TC11200T"]
        )

        CopexAccounts = EnvelopeManager.Get_All_Children_Accounts_with_Mapping(
            ["TC13000T"]
        )

        projects = EnvelopeManager.get_all_children(
            XX_Project.objects.all(), project_code
        )
        projects.append(project_code)
        transfers_for_project = xx_TransactionTransfer.objects.filter(
            project_code__in=projects
        )
        # MenPowerActiveAccounts = (
        #     transfers_for_project.filter(account_code__in=MenPowerAccounts)
        #     .values_list("account_code", flat=True)
        #     .distinct()
        # )
        # NonMenPowerActiveAccounts = (
        #     transfers_for_project.filter(account_code__in=NonMenPowerAccounts)
        #     .values_list("account_code", flat=True)
        #     .distinct()
        # )
        # CopexActiveAccounts = (
        #     transfers_for_project.filter(account_code__in=CopexAccounts)
        #     .values_list("account_code", flat=True)
        #     .distinct()
        # )
        MenPowerData = EnvelopeManager.Get_Dashboard_Data_For_Account(
            transfers_for_project, project_code, MenPowerAccounts
        )
        NonMenPowerData = EnvelopeManager.Get_Dashboard_Data_For_Account(
            transfers_for_project, project_code, NonMenPowerAccounts
        )
        CopexData = EnvelopeManager.Get_Dashboard_Data_For_Account(
            transfers_for_project, project_code, CopexAccounts
        )

        def format_category_data(data_tuple):
            (
                total_approved,
                total_submitted,
                total_fy25_budget,
                total_fy24_budget,
                accounts_list,
            ) = data_tuple
            return {
                "summary": {
                    "total_approved_transfers": total_approved,
                    "total_fy25_budget": total_fy25_budget,
                    "total_fy24_budget": total_fy24_budget,
                },
                "accounts": accounts_list,
            }

        return {
            "MenPower": format_category_data(MenPowerData),
            "NonMenPower": format_category_data(NonMenPowerData),
            "Copex": format_category_data(CopexData),
        }


class XX_PivotFund(models.Model):
    """Model representing ADJD pivot funds"""

    entity = models.CharField(max_length=50)
    account = models.CharField(max_length=50)
    project = models.CharField(max_length=50, null=True, blank=True)
    year = models.IntegerField()
    actual = models.DecimalField(
        max_digits=30, decimal_places=2, null=True, blank=True
    )  # Changed from EncryptedCharField to DecimalField
    fund = models.DecimalField(
        max_digits=30, decimal_places=2, null=True, blank=True
    )  # Changed from EncryptedCharField to DecimalField
    budget = models.DecimalField(
        max_digits=30, decimal_places=2, null=True, blank=True
    )  # Changed from EncryptedCharField to DecimalField
    encumbrance = models.DecimalField(
        max_digits=30, decimal_places=2, null=True, blank=True
    )  # Changed from EncryptedCharField to DecimalField

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["entity", "account", "project", "year"],
                name="unique_entity_account_year",
            )
        ]
        db_table = "XX_PIVOTFUND_XX"


class XX_TransactionAudit(models.Model):
    """Model representing ADJD transaction audit records"""

    id = models.AutoField(primary_key=True)
    type = models.CharField(max_length=50, null=True, blank=True)
    transfer_id = models.IntegerField(null=True, blank=True)
    transcation_code = models.CharField(max_length=50, null=True, blank=True)
    cost_center_code = models.CharField(max_length=50, null=True, blank=True)
    account_code = models.CharField(max_length=50, null=True, blank=True)
    project_code = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f"Audit {self.id}: {self.transcation_code}"

    class Meta:
        db_table = "XX_TRANSACTION_AUDIT_XX"


class XX_ACCOUNT_ENTITY_LIMIT(models.Model):
    """
    LEGACY Model - being replaced by XX_SegmentTransferLimit
    Model representing ADJD account entity limits
    """

    id = models.AutoField(primary_key=True)
    account_id = models.CharField(max_length=50)
    entity_id = models.CharField(max_length=50)
    project_id = models.CharField(max_length=50, null=True, blank=True)
    is_transer_allowed_for_source = models.CharField(
        max_length=255, null=True, blank=True
    )  # Changed from EncryptedBooleanField
    is_transer_allowed_for_target = models.CharField(
        max_length=255, null=True, blank=True
    )  # Changed from EncryptedBooleanField
    is_transer_allowed = models.CharField(
        max_length=255, null=True, blank=True
    )  # Changed from EncryptedBooleanField
    source_count = models.IntegerField(
        null=True, blank=True
    )  # Changed from EncryptedIntegerField
    target_count = models.IntegerField(
        null=True, blank=True
    )  # Changed from EncryptedIntegerField

    def __str__(self):
        return f"Account Entity Limit {self.id}"

    class Meta:
        db_table = "XX_ACCOUNT_ENTITY_LIMIT_XX"
        unique_together = ("account_id", "entity_id")


class XX_SegmentTransferLimit(models.Model):
    """
    Dynamic segment transfer limit model (Phase 3).
    Replaces XX_ACCOUNT_ENTITY_LIMIT with flexible segment combination support.
    
    Defines transfer rules/limits for segment combinations:
    - Which segment combinations can transfer to which others
    - Transfer limits and counts
    - Source/target restrictions
    """
    id = models.AutoField(primary_key=True)
    
    # Store segment combination as JSON: {"1": "E001", "2": "A100", "3": "P001"}
    segment_combination = models.JSONField(
        help_text="JSON mapping of segment_type_id -> segment_code for this limit rule"
    )
    
    # Transfer allowance flags
    is_transfer_allowed_as_source = models.BooleanField(
        default=True,
        help_text="Can this segment combination be used as a transfer source?"
    )
    
    is_transfer_allowed_as_target = models.BooleanField(
        default=True,
        help_text="Can this segment combination be used as a transfer target?"
    )
    
    is_transfer_allowed = models.BooleanField(
        default=True,
        help_text="Are transfers allowed for this segment combination at all?"
    )
    
    # Transfer counts/limits
    source_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Number of times used as source (for tracking)"
    )
    
    target_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Number of times used as target (for tracking)"
    )
    
    max_source_transfers = models.IntegerField(
        null=True,
        blank=True,
        help_text="Maximum allowed transfers as source (null = unlimited)"
    )
    
    max_target_transfers = models.IntegerField(
        null=True,
        blank=True,
        help_text="Maximum allowed transfers as target (null = unlimited)"
    )
    
    # Additional metadata
    fiscal_year = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text="Fiscal year this limit applies to"
    )
    
    notes = models.TextField(
        null=True,
        blank=True,
        help_text="Notes about this transfer limit"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this limit is currently active"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "XX_SEGMENT_TRANSFER_LIMIT_XX"
        verbose_name = "Segment Transfer Limit"
        verbose_name_plural = "Segment Transfer Limits"
        indexes = [
            models.Index(fields=["fiscal_year", "is_active"]),
            models.Index(fields=["is_active"]),
        ]
    
    def __str__(self):
        segments_str = ", ".join([f"S{k}:{v}" for k, v in self.segment_combination.items()])
        return f"Transfer Limit {self.id}: {segments_str}"
    
    def get_segment_code(self, segment_type_id):
        """Get segment code for a specific segment type in this limit"""
        return self.segment_combination.get(str(segment_type_id))
    
    def matches_segments(self, segment_dict):
        """
        Check if this limit matches the given segment combination.
        
        Args:
            segment_dict: Dict of {segment_type_id: segment_code}
        
        Returns:
            bool: True if limit combination exactly matches the given segments
        """
        # Convert both to string keys for comparison
        limit_segments = {str(k): str(v) for k, v in self.segment_combination.items()}
        query_segments = {str(k): str(v) for k, v in segment_dict.items()}
        
        # Must have same number of segments
        if len(limit_segments) != len(query_segments):
            return False
        
        # All segments must match exactly
        for seg_type_id, seg_code in limit_segments.items():
            if seg_type_id not in query_segments:
                return False
            if query_segments[seg_type_id] != seg_code:
                return False
        
        return True
    
    def can_be_source(self):
        """Check if this segment combination can be used as transfer source"""
        if not self.is_active or not self.is_transfer_allowed:
            return False
        if not self.is_transfer_allowed_as_source:
            return False
        if self.max_source_transfers and self.source_count and self.source_count >= self.max_source_transfers:
            return False
        return True
    
    def can_be_target(self):
        """Check if this segment combination can be used as transfer target"""
        if not self.is_active or not self.is_transfer_allowed:
            return False
        if not self.is_transfer_allowed_as_target:
            return False
        if self.max_target_transfers and self.target_count and self.target_count >= self.max_target_transfers:
            return False
        return True
    
    def increment_source_count(self):
        """Increment the source usage count"""
        self.source_count = (self.source_count or 0) + 1
        self.save(update_fields=['source_count', 'updated_at'])
    
    def increment_target_count(self):
        """Increment the target usage count"""
        self.target_count = (self.target_count or 0) + 1
        self.save(update_fields=['target_count', 'updated_at'])


class XX_BalanceReport(models.Model):
    """Model representing balance report data from report.xlsx"""

    id = models.AutoField(primary_key=True)
    control_budget_name = models.CharField(
        max_length=100, null=True, blank=True, help_text="Control Budget Name"
    )
    ledger_name = models.CharField(
        max_length=100, null=True, blank=True, help_text="Ledger Name"
    )
    as_of_period = models.CharField(
        max_length=20, null=True, blank=True, help_text="As of Period (e.g., Sep-25)"
    )
    segment1 = models.CharField(
        max_length=50, null=True, blank=True, help_text="Segment 1 (Cost Center)"
    )
    segment2 = models.CharField(
        max_length=50, null=True, blank=True, help_text="Segment 2 (Account)"
    )
    segment3 = models.CharField(
        max_length=50, null=True, blank=True, help_text="Segment 3 (Project)"
    )
    encumbrance_ytd = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Encumbrance Year to Date",
    )
    other_ytd = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Other Year to Date",
    )
    actual_ytd = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Actual Year to Date",
    )
    funds_available_asof = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Funds Available As Of",
    )
    budget_ytd = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Budget Year to Date",
    )

    # Additional metadata fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Balance Report: {self.control_budget_name} - {self.segment1}/{self.segment2}/{self.segment3}"

    class Meta:
        db_table = "XX_BALANCE_REPORT_XX"
        verbose_name = "Balance Report"
        verbose_name_plural = "Balance Reports"
        indexes = [
            models.Index(fields=["control_budget_name", "as_of_period"]),
            models.Index(fields=["segment1", "segment2", "segment3"]),
            models.Index(fields=["as_of_period"]),
        ]


class XX_BalanceReportSegment(models.Model):
    """
    Linking model for balance report segments (replaces hardcoded segment1/2/3).
    
    This model enables flexible segment storage for balance reports, supporting
    2-30 segments dynamically based on XX_SegmentType configuration.
    
    Example:
        For a balance report with Entity (E001), Account (A100), Project (P001):
        - Record 1: balance_report=BR1, segment_type=Entity, segment_value=E001
        - Record 2: balance_report=BR1, segment_type=Account, segment_value=A100
        - Record 3: balance_report=BR1, segment_type=Project, segment_value=P001
    """
    
    id = models.AutoField(primary_key=True)
    
    balance_report = models.ForeignKey(
        'XX_BalanceReport',
        on_delete=models.CASCADE,
        related_name='balance_segments',
        help_text="Parent balance report record"
    )
    
    segment_type = models.ForeignKey(
        'XX_SegmentType',
        on_delete=models.PROTECT,
        related_name='balance_report_segments',
        help_text="Type of segment (Entity, Account, Project, etc.)"
    )
    
    segment_value = models.ForeignKey(
        'XX_Segment',
        on_delete=models.PROTECT,
        related_name='balance_report_usages',
        null=True,
        blank=True,
        help_text="Specific segment value (e.g., E001, A100, P001)"
    )
    
    segment_code = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Segment code (denormalized for performance, synced from segment_value)"
    )
    
    # Oracle integration tracking
    oracle_field_name = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Oracle field name (SEGMENT1, SEGMENT2, etc.)"
    )
    
    oracle_field_number = models.IntegerField(
        null=True,
        blank=True,
        help_text="Oracle segment position (1-30)"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        """Override save to sync segment_code from segment_value"""
        if self.segment_value and not self.segment_code:
            self.segment_code = self.segment_value.code
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.balance_report.id} - {self.segment_type.segment_name}: {self.segment_code or 'N/A'}"
    
    class Meta:
        db_table = "XX_BALANCE_REPORT_SEGMENT_XX"
        verbose_name = "Balance Report Segment"
        verbose_name_plural = "Balance Report Segments"
        unique_together = [
            ('balance_report', 'segment_type'),  # One value per segment type per report
        ]
        indexes = [
            models.Index(fields=['balance_report', 'segment_type']),
            models.Index(fields=['segment_type', 'segment_code']),
            models.Index(fields=['oracle_field_number']),
        ]
        ordering = ['balance_report', 'oracle_field_number']


class XX_ACCOUNT_mapping(models.Model):
    """Model representing ADJD account mappings"""

    id = models.AutoField(primary_key=True)
    source_account = models.CharField(max_length=50)
    target_account = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return (
            f"Account Mapping {self.id}: {self.source_account} -> {self.target_account}"
        )

    class Meta:
        db_table = "XX_ACCOUNT_MAPPING__elies_XX"
        unique_together = ("source_account", "target_account")


class XX_Entity_mapping(models.Model):
    """Model representing ADJD entity mappings"""

    id = models.AutoField(primary_key=True)
    source_entity = models.CharField(max_length=50)
    target_entity = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Entity Mapping {self.id}: {self.source_entity} -> {self.target_entity}"

    class Meta:
        db_table = "XX_ENTITY_MAPPING__elies_XX"
        unique_together = ("source_entity", "target_entity")


# ============================================
# DYNAMIC SEGMENT SYSTEM (Multi-Client Support)
# ============================================

class XX_SegmentType(models.Model):
    """
    Defines segment types for this client installation.
    Examples: Entity (Cost Center), Account, Project, Line Item, etc.
    Configured during client setup.
    """
    segment_id = models.IntegerField(primary_key=True, help_text="Unique segment identifier")
    segment_name = models.CharField(
        max_length=50, 
        unique=True,
        help_text="Display name (e.g., 'Entity', 'Account', 'Project')"
    )
    segment_type = models.CharField(
        max_length=50,
        help_text="Technical type (e.g., 'cost_center', 'account', 'project')"
    )
    oracle_segment_number = models.IntegerField(
        help_text="Maps to Oracle SEGMENT1, SEGMENT2, etc."
    )
    is_required = models.BooleanField(
        default=True,
        help_text="Whether this segment is required in transactions"
    )
    has_hierarchy = models.BooleanField(
        default=False,
        help_text="Whether this segment supports parent-child relationships"
    )
    max_length = models.IntegerField(
        default=50,
        help_text="Maximum code length for this segment"
    )
    display_order = models.IntegerField(
        default=0,
        help_text="Order for displaying in UI (lower = first)"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Optional description of what this segment represents"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this segment is currently active"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "XX_SEGMENT_TYPE_XX"
        verbose_name = "Segment Type"
        verbose_name_plural = "Segment Types"
        ordering = ['display_order', 'segment_id']
    
    def __str__(self):
        return f"{self.segment_name} (Segment {self.oracle_segment_number})"


class XX_Segment(models.Model):
    """
    Generic segment value model that replaces XX_Entity, XX_Account, XX_Project.
    All segment values (regardless of type) are stored here.
    """
    id = models.AutoField(primary_key=True)
    segment_type = models.ForeignKey(
        XX_SegmentType,
        on_delete=models.CASCADE,
        related_name='values',
        help_text="Which segment type this value belongs to"
    )
    code = models.CharField(
        max_length=50,
        help_text="The actual segment code/value"
    )
    parent_code = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Parent segment code for hierarchical segments"
    )
    alias = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Display name / description"
    )
    level = models.IntegerField(
        default=0,
        help_text="Hierarchy level (0 = root)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this segment value is active"
    )
    
    # NOTE: Envelope amounts are now stored in XX_SegmentEnvelope model (Phase 3)
    # The envelope_amount field has been removed - use XX_SegmentEnvelope for budget tracking
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "XX_SEGMENT_XX"
        verbose_name = "Segment Value"
        verbose_name_plural = "Segment Values"
        unique_together = ("segment_type", "code")
        indexes = [
            models.Index(fields=["segment_type", "code"]),
            models.Index(fields=["segment_type", "parent_code"]),
            models.Index(fields=["code"]),
        ]
    
    def __str__(self):
        return f"{self.segment_type.segment_name}: {self.code} ({self.alias or 'No alias'})"
    
    def get_all_children(self):
        """Get all descendant codes recursively"""
        children = list(XX_Segment.objects.filter(
            segment_type=self.segment_type,
            parent_code=self.code
        ).values_list('code', flat=True))
        
        descendants = []
        for child_code in children:
            descendants.append(child_code)
            try:
                child = XX_Segment.objects.get(
                    segment_type=self.segment_type,
                    code=child_code
                )
                descendants.extend(child.get_all_children())
            except XX_Segment.DoesNotExist:
                continue
        
        return descendants


class XX_Segment_Funds(models.Model):
    """
    Oracle Segment Funds model with 30 segments and 7 additional columns.
    Stores financial data with flexible segment structure.
    """
    id = models.AutoField(primary_key=True)
    Segment1 = models.CharField(max_length=50, null=True, blank=True, help_text="Segment 1")
    Segment2 = models.CharField(max_length=50, null=True, blank=True, help_text="Segment 2")
    Segment3 = models.CharField(max_length=50, null=True, blank=True, help_text="Segment 3")
    Segment4 = models.CharField(max_length=50, null=True, blank=True, help_text="Segment 4")
    Segment5 = models.CharField(max_length=50, null=True, blank=True, help_text="Segment 5")
    Segment6 = models.CharField(max_length=50, null=True, blank=True, help_text="Segment 6")
    Segment7 = models.CharField(max_length=50, null=True, blank=True, help_text="Segment 7")
    Segment8 = models.CharField(max_length=50, null=True, blank=True, help_text="Segment 8")
    Segment9 = models.CharField(max_length=50, null=True, blank=True, help_text="Segment 9")
    Segment10 = models.CharField(max_length=50, null=True, blank=True, help_text="Segment 10")
    Segment11 = models.CharField(max_length=50, null=True, blank=True, help_text="Segment 11")
    Segment12 = models.CharField(max_length=50, null=True, blank=True, help_text="Segment 12")
    Segment13 = models.CharField(max_length=50, null=True, blank=True, help_text="Segment 13")
    Segment14 = models.CharField(max_length=50, null=True, blank=True, help_text="Segment 14")
    Segment15 = models.CharField(max_length=50, null=True, blank=True, help_text="Segment 15")
    Segment16 = models.CharField(max_length=50, null=True, blank=True, help_text="Segment 16")
    Segment17 = models.CharField(max_length=50, null=True, blank=True, help_text="Segment 17")
    Segment18 = models.CharField(max_length=50, null=True, blank=True, help_text="Segment 18")
    Segment19 = models.CharField(max_length=50, null=True, blank=True, help_text="Segment 19")
    Segment20 = models.CharField(max_length=50, null=True, blank=True, help_text="Segment 20")
    Segment21 = models.CharField(max_length=50, null=True, blank=True, help_text="Segment 21")
    Segment22 = models.CharField(max_length=50, null=True, blank=True, help_text="Segment 22")
    Segment23 = models.CharField(max_length=50, null=True, blank=True, help_text="Segment 23")
    Segment24 = models.CharField(max_length=50, null=True, blank=True, help_text="Segment 24")
    Segment25 = models.CharField(max_length=50, null=True, blank=True, help_text="Segment 25")
    Segment26 = models.CharField(max_length=50, null=True, blank=True, help_text="Segment 26")
    Segment27 = models.CharField(max_length=50, null=True, blank=True, help_text="Segment 27")
    Segment28 = models.CharField(max_length=50, null=True, blank=True, help_text="Segment 28")
    Segment29 = models.CharField(max_length=50, null=True, blank=True, help_text="Segment 29")
    Segment30 = models.CharField(max_length=50, null=True, blank=True, help_text="Segment 30")
    
    # 7 Additional columns (rename as needed)
    CONTROL_BUDGET_NAME = models.CharField(max_length=100, null=True, blank=True, help_text="CONTROL_BUDGET_NAME")
    ENCUMBRANCE_PTD = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, help_text="encumbrance_ptd")
    PERIOD_NAME = models.CharField(max_length=100, null=True, blank=True, help_text="PERIOD_NAME")
    FUNDS_AVAILABLE_PTD = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, help_text="FUNDS_AVAILABLE_PTD")
    COMMITMENT_PTD = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, help_text="COMMITMENT_PTD")
    OBLIGATION_PTD = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, help_text="OBLIGATION_PTD")
    OTHER_PTD = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, help_text="OTHER_PTD")
    ACTUAL_PTD = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, help_text="ACTUAL_PTD")
    BUDGET_PTD= models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, help_text="BUDGET_PTD")
    TOTAL_BUDGET = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, help_text="TOTAL_BUDGET")
    INITIAL_BUDGET = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, help_text="INITIAL_BUDGET")
    BUDGET_ADJUSTMENTS = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, help_text="BUDGET_ADJUSTMENTS")

    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "XX_SEGMENT_FUNDS_XX"
        verbose_name = "Segment Funds"
        verbose_name_plural = "Segment Funds"
        indexes = [
            models.Index(fields=["Segment1", "Segment2", "Segment3"]),
        ]
    
    def __str__(self):
        segments = [getattr(self, f"Segment{i}") for i in range(1, 31) if getattr(self, f"Segment{i}")]
        return f"Segment Funds {self.id}: {' / '.join(segments[:3])}"


class XX_TransactionSegment(models.Model):
    """
    Links transaction transfers to their segment values.
    Each transaction will have one record per segment type.
    """
    id = models.AutoField(primary_key=True)
    transaction_transfer = models.ForeignKey(
        'transaction.xx_TransactionTransfer',
        on_delete=models.CASCADE,
        related_name='transaction_segments',
        help_text="The transaction this segment belongs to"
    )
    segment_type = models.ForeignKey(
        XX_SegmentType,
        on_delete=models.CASCADE,
        help_text="Which segment type (Entity, Account, etc.)"
    )
    segment_value = models.ForeignKey(
        XX_Segment,
        on_delete=models.CASCADE,
        help_text="The specific segment value"
    )
    
    # For transfer transactions, store source and destination
    from_segment_value = models.ForeignKey(
        XX_Segment,
        on_delete=models.CASCADE,
        related_name='transfers_from',
        null=True,
        blank=True,
        help_text="Source segment for transfers"
    )
    to_segment_value = models.ForeignKey(
        XX_Segment,
        on_delete=models.CASCADE,
        related_name='transfers_to',
        null=True,
        blank=True,
        help_text="Destination segment for transfers"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "XX_TRANSACTION_SEGMENT_XX"
        verbose_name = "Transaction Segment"
        verbose_name_plural = "Transaction Segments"
        unique_together = ("transaction_transfer", "segment_type")
        indexes = [
            models.Index(fields=["transaction_transfer", "segment_type"]),
            models.Index(fields=["segment_value"]),
        ]
    
    def __str__(self):
        return f"Transaction {self.transaction_transfer_id} - {self.segment_type.segment_name}: {self.segment_value.code}"


class XX_DynamicBalanceReport(models.Model):
    """
    Dynamic balance report storage that supports any number of segments.
    Segment values stored as JSONField for flexibility.
    """
    id = models.AutoField(primary_key=True)
    control_budget_name = models.CharField(
        max_length=100, null=True, blank=True
    )
    ledger_name = models.CharField(
        max_length=100, null=True, blank=True
    )
    as_of_period = models.CharField(
        max_length=20, null=True, blank=True
    )
    
    # Store segment values as JSON: {"1": "12345", "2": "67890", "3": "98765"}
    # Keys are segment_type IDs, values are segment codes
    segment_values = models.JSONField(
        default=dict,
        help_text="JSON mapping of segment_type_id -> segment_code"
    )
    
    # Financial fields
    encumbrance_ytd = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True
    )
    other_ytd = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True
    )
    actual_ytd = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True
    )
    funds_available_asof = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True
    )
    budget_ytd = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "XX_DYNAMIC_BALANCE_REPORT_XX"
        verbose_name = "Dynamic Balance Report"
        verbose_name_plural = "Dynamic Balance Reports"
        indexes = [
            models.Index(fields=["control_budget_name", "as_of_period"]),
            models.Index(fields=["as_of_period"]),
        ]
    
    def __str__(self):
        segments_str = ", ".join([f"{k}:{v}" for k, v in self.segment_values.items()])
        return f"Balance Report: {self.control_budget_name} - {segments_str}"
    
    def get_segment_value(self, segment_type_id):
        """Get segment value for a specific segment type"""
        return self.segment_values.get(str(segment_type_id))


# ============================================
# PHASE 3: ENVELOPE AND MAPPING MODELS
# ============================================

class XX_SegmentEnvelope(models.Model):
    """
    Dynamic envelope model that replaces Project_Envelope.
    Stores envelope amounts for ANY segment combination (not just projects).
    
    Example:
    - For 3 segments (Entity, Account, Project): stores envelope per project
    - For 5 segments: stores envelope per 5-segment combination
    - Flexible JSON storage for any number of segments
    """
    id = models.AutoField(primary_key=True)
    
    # Store segment combination as JSON: {"1": "E001", "2": "A100", "3": "P001"}
    # Keys are segment_type IDs, values are segment codes
    segment_combination = models.JSONField(
        help_text="JSON mapping of segment_type_id -> segment_code representing the envelope scope"
    )
    
    envelope_amount = models.DecimalField(
        max_digits=30,
        decimal_places=2,
        help_text="Total envelope/budget amount for this segment combination"
    )
    
    fiscal_year = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text="Fiscal year for this envelope (e.g., 'FY2025')"
    )
    
    description = models.TextField(
        null=True,
        blank=True,
        help_text="Optional description of this envelope"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this envelope is currently active"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "XX_SEGMENT_ENVELOPE_XX"
        verbose_name = "Segment Envelope"
        verbose_name_plural = "Segment Envelopes"
        indexes = [
            models.Index(fields=["fiscal_year", "is_active"]),
        ]
    
    def __str__(self):
        segments_str = ", ".join([f"S{k}:{v}" for k, v in self.segment_combination.items()])
        return f"Envelope {self.id}: {segments_str} = {self.envelope_amount}"
    
    def get_segment_code(self, segment_type_id):
        """Get segment code for a specific segment type in this envelope"""
        return self.segment_combination.get(str(segment_type_id))
    
    def matches_segments(self, segment_dict):
        """
        Check if this envelope matches the given segment combination.
        
        Args:
            segment_dict: Dict of {segment_type_id: segment_code}
        
        Returns:
            bool: True if envelope combination exactly matches the given segments
        """
        # Convert both to string keys for comparison
        envelope_segments = {str(k): str(v) for k, v in self.segment_combination.items()}
        query_segments = {str(k): str(v) for k, v in segment_dict.items()}
        
        # Must have same number of segments
        if len(envelope_segments) != len(query_segments):
            return False
        
        # All segments must match exactly
        for seg_type_id, seg_code in envelope_segments.items():
            if seg_type_id not in query_segments:
                return False
            if query_segments[seg_type_id] != seg_code:
                return False
        
        return True


class XX_SegmentMapping(models.Model):
    """
    Generic segment-to-segment mapping model.
    Replaces hardcoded Account_Mapping and XX_Entity_mapping.
    
    Allows mapping any segment value to another segment value of the SAME type.
    Example: Entity E001 maps to Entity E002, Account A100 maps to Account A200
    """
    id = models.AutoField(primary_key=True)
    
    # Both source and target must be from the SAME segment type
    segment_type = models.ForeignKey(
        XX_SegmentType,
        on_delete=models.CASCADE,
        related_name='mappings',
        help_text="The segment type this mapping applies to"
    )
    
    source_segment = models.ForeignKey(
        XX_Segment,
        on_delete=models.CASCADE,
        related_name='mappings_as_source',
        help_text="The source segment value"
    )
    
    target_segment = models.ForeignKey(
        XX_Segment,
        on_delete=models.CASCADE,
        related_name='mappings_as_target',
        help_text="The target segment value that source maps to"
    )
    
    mapping_type = models.CharField(
        max_length=50,
        default='STANDARD',
        help_text="Type of mapping: STANDARD, ALIAS, CONSOLIDATION, etc."
    )
    
    description = models.TextField(
        null=True,
        blank=True,
        help_text="Optional description of this mapping rule"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this mapping is currently active"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "XX_SEGMENT_MAPPING_XX"
        verbose_name = "Segment Mapping"
        verbose_name_plural = "Segment Mappings"
        unique_together = ("segment_type", "source_segment", "target_segment")
        indexes = [
            models.Index(fields=["segment_type", "source_segment"]),
            models.Index(fields=["segment_type", "target_segment"]),
            models.Index(fields=["is_active"]),
        ]
    
    def __str__(self):
        return f"{self.segment_type.segment_name} Mapping: {self.source_segment.code} → {self.target_segment.code}"
    
    def clean(self):
        """Validate that source and target are from the same segment type"""
        from django.core.exceptions import ValidationError
        
        if self.source_segment.segment_type_id != self.segment_type_id:
            raise ValidationError("Source segment must be from the specified segment type")
        
        if self.target_segment.segment_type_id != self.segment_type_id:
            raise ValidationError("Target segment must be from the specified segment type")
        
        if self.source_segment_id == self.target_segment_id:
            raise ValidationError("Source and target segments cannot be the same")
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)





class XX_gfs_Mamping(models.Model):
    """Model representing GFS code mappings"""

    id = models.AutoField(primary_key=True)
    To_Value = models.CharField(max_length=50)
    From_value = models.CharField(max_length=50)
    Target_value = models.CharField(max_length=50)
    Target_alias=models.CharField(max_length=100,null=True,blank=True)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"GFS Mapping {self.id}: To={self.To_Value}, From={self.From_value}, Target={self.Target_value}"

    class Meta:
        db_table = "XX_GFS_MAPPING__XX"
        unique_together = ("To_Value", "Target_value")
