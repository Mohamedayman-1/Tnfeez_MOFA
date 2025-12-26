from django.db import models
from django.core.exceptions import ValidationError
# Refer to budget model by string to avoid circular import

# Removed encrypted fields import - using standard Django fields now


class xx_TransactionTransfer(models.Model):
    """Model for ADJD transaction transfers"""

    transfer_id = models.AutoField(primary_key=True)
    transaction = models.ForeignKey('budget_management.xx_BudgetTransfer', on_delete=models.CASCADE, db_column="transaction_id", null=True, blank=True, related_name="transfers")
    reason = models.TextField(null=True, blank=True)  # Keep as TextField but avoid in complex queries
    account_code = models.IntegerField(null=True, blank=True)
    account_name = models.TextField(null=True, blank=True)  # Keep as TextField but avoid in complex queries
    project_code = models.TextField(null=True, blank=True)
    project_name = models.TextField(null=True, blank=True)  # Keep as TextField but avoid in complex queries
    cost_center_code = models.IntegerField(null=True, blank=True)
    cost_center_name = models.TextField(null=True, blank=True)  # Keep as TextField but avoid in complex queries
    done = models.IntegerField(default=1)
    encumbrance = models.DecimalField(max_digits=500, decimal_places=2, null=True, blank=True)  # Changed from EncryptedTextField to DecimalField
    actual = models.DecimalField(max_digits=500, decimal_places=2, null=True, blank=True)
    approved_budget = models.DecimalField(max_digits=500, decimal_places=2, null=True, blank=True)  # Changed from EncryptedTextField to DecimalField
    available_budget = models.DecimalField(max_digits=500, decimal_places=2, null=True, blank=True)  # Changed from EncryptedTextField to DecimalField
    from_center = models.DecimalField(max_digits=500, decimal_places=2, null=True, blank=True)  # Changed from TextField to DecimalField
    to_center = models.DecimalField(max_digits=500, decimal_places=2, null=True, blank=True)  # Changed from TextField to DecimalField
    budget_adjustments = models.DecimalField(max_digits=500, decimal_places=2, null=True, blank=True, default=0)
    commitments = models.DecimalField(max_digits=500, decimal_places=2, null=True, blank=True, default=0)
    expenditures = models.DecimalField(max_digits=500, decimal_places=2, null=True, blank=True, default=0)
    initial_budget = models.DecimalField(max_digits=500, decimal_places=2, null=True, blank=True)
    obligations = models.DecimalField(max_digits=500, decimal_places=2, null=True, blank=True)
    other_consumption = models.DecimalField(max_digits=500, decimal_places=2, null=True, blank=True, default=0)
    total_budget = models.DecimalField(max_digits=500, decimal_places=2, null=True, blank=True)


    file = models.FileField(upload_to="transfers/", null=True, blank=True)





    class Meta:
        db_table = "XX_TRANSACTION_TRANSFER_XX"

    def __str__(self):
        return f"ADJD Transfer {self.transfer_id}"
    
    # ========================================================================
    # DYNAMIC SEGMENT HELPER METHODS
    # ========================================================================
    
    def get_segments_dict(self):
        """
        Get all segment assignments for this transaction as a dictionary.
        Returns: {
            segment_id: {
                'segment_name': 'Entity',
                'from_code': 'E001',
                'from_alias': 'HR Department',
                'to_code': 'E002',
                'to_alias': 'IT Department'
            }
        }
        """
        from account_and_entitys.models import XX_TransactionSegment
        
        segments_dict = {}
        transaction_segments = XX_TransactionSegment.objects.filter(
            transaction_transfer=self
        ).select_related('segment_type', 'from_segment_value', 'to_segment_value')
        
        for ts in transaction_segments:
            segments_dict[ts.segment_type.segment_id] = {
                'segment_name': ts.segment_type.segment_name,
                'segment_type': ts.segment_type.segment_type,
                'from_code': ts.from_segment_value.code if ts.from_segment_value else None,
                'from_alias': ts.from_segment_value.alias if ts.from_segment_value else None,
                'to_code': ts.to_segment_value.code if ts.to_segment_value else None,
                'to_alias': ts.to_segment_value.alias if ts.to_segment_value else None,
            }
        
        return segments_dict
    
    def set_segments(self, segments_data):
        """
        Set segment assignments for this transaction.
        
        Args:
            segments_data (dict): {
                segment_id: {
                    'from_code': 'E001',
                    'to_code': 'E002'
                }
            }
        
        Example:
            transaction.set_segments({
                1: {'from_code': 'E001', 'to_code': 'E002'},  # Entity
                2: {'from_code': 'A100', 'to_code': 'A200'},  # Account
                3: {'from_code': 'P001', 'to_code': 'P001'},  # Project (same)
            })
        """
        from account_and_entitys.managers.segment_manager import SegmentManager
        
        # Validate segments before creating
        validation_result = SegmentManager.validate_transaction_segments(segments_data)
        if not validation_result['valid']:
            raise ValidationError(validation_result['errors'])
        
        # Create/update transaction segments
        result = SegmentManager.create_transaction_segments(
            transaction_transfer=self,
            segments_data=segments_data
        )
        
        if not result['success']:
            raise ValidationError(result['errors'])
        
        # Sync to legacy fields for backward compatibility
        self.sync_dynamic_to_legacy()
        
        return result
    
    def sync_dynamic_to_legacy(self):
        """
        Sync dynamic segment values to legacy fields for backward compatibility.
        Maps:
            - Segment type 'Entity' or 'cost_center' → cost_center_code, cost_center_name
            - Segment type 'Account' or 'account' → account_code, account_name
            - Segment type 'Project' or 'project' → project_code, project_name
        """
        from account_and_entitys.models import XX_TransactionSegment, XX_Segment
        
        try:
            # Get Entity/Cost Center segment
            entity_segment = XX_TransactionSegment.objects.filter(
                transaction_transfer=self,
                segment_type__segment_type__in=['cost_center', 'entity']
            ).select_related('from_segment_value', 'to_segment_value').first()
            
            if entity_segment and entity_segment.from_segment_value:
                try:
                    # Try to convert to int for legacy integer field
                    self.cost_center_code = int(entity_segment.from_segment_value.code)
                except (ValueError, TypeError):
                    # If code is not numeric, skip (can't store in IntegerField)
                    pass
                self.cost_center_name = entity_segment.from_segment_value.alias or ''
            
            # Get Account segment
            account_segment = XX_TransactionSegment.objects.filter(
                transaction_transfer=self,
                segment_type__segment_type='account'
            ).select_related('from_segment_value', 'to_segment_value').first()
            
            if account_segment and account_segment.from_segment_value:
                try:
                    self.account_code = int(account_segment.from_segment_value.code)
                except (ValueError, TypeError):
                    pass
                self.account_name = account_segment.from_segment_value.alias or ''
            
            # Get Project segment
            project_segment = XX_TransactionSegment.objects.filter(
                transaction_transfer=self,
                segment_type__segment_type='project'
            ).select_related('from_segment_value', 'to_segment_value').first()
            
            if project_segment and project_segment.from_segment_value:
                self.project_code = project_segment.from_segment_value.code
                self.project_name = project_segment.from_segment_value.alias or ''
            
            self.save(update_fields=['cost_center_code', 'cost_center_name', 
                                    'account_code', 'account_name',
                                    'project_code', 'project_name'])
        
        except Exception as e:
            # Don't fail transaction if legacy sync fails
            print(f"Warning: Failed to sync dynamic segments to legacy fields: {e}")
    
    def sync_legacy_to_dynamic(self):
        """
        Sync legacy segment fields to dynamic segment structure.
        Used during migration or when legacy fields are updated directly.
        """
        from account_and_entitys.managers.segment_manager import SegmentManager
        
        segments_data = {}
        
        # Map Entity/Cost Center
        if self.cost_center_code:
            entity_type = SegmentManager.get_segment_by_type('Entity')
            if entity_type:
                segments_data[entity_type.segment_id] = {
                    'from_code': str(self.cost_center_code),
                    'to_code': str(self.cost_center_code)  # Assume same for now
                }
        
        # Map Account
        if self.account_code:
            account_type = SegmentManager.get_segment_by_type('Account')
            if account_type:
                segments_data[account_type.segment_id] = {
                    'from_code': str(self.account_code),
                    'to_code': str(self.account_code)  # Assume same for now
                }
        
        # Map Project
        if self.project_code:
            project_type = SegmentManager.get_segment_by_type('Project')
            if project_type:
                segments_data[project_type.segment_id] = {
                    'from_code': str(self.project_code),
                    'to_code': str(self.project_code)  # Assume same for now
                }
        
        if segments_data:
            try:
                self.set_segments(segments_data)
            except ValidationError as e:
                print(f"Warning: Failed to sync legacy fields to dynamic segments: {e}")
    
    def get_segment_value(self, segment_type_name, direction='from'):
        """
        Get a specific segment value for this transaction.
        
        Args:
            segment_type_name (str): Name of segment type (e.g., 'Entity', 'Account')
            direction (str): 'from' or 'to'
        
        Returns:
            str: Segment code or None
        """
        from account_and_entitys.models import XX_TransactionSegment
        
        try:
            ts = XX_TransactionSegment.objects.select_related(
                'segment_type', 'from_segment_value', 'to_segment_value'
            ).get(
                transaction_transfer=self,
                segment_type__segment_name=segment_type_name
            )
            
            if direction == 'from':
                return ts.from_segment_value.code if ts.from_segment_value else None
            else:
                return ts.to_segment_value.code if ts.to_segment_value else None
        
        except XX_TransactionSegment.DoesNotExist:
            return None
    
    def has_cross_segment_transfer(self, segment_type_name):
        """
        Check if this transaction involves a transfer between different segment values.
        
        Args:
            segment_type_name (str): Name of segment type to check
        
        Returns:
            bool: True if from_code != to_code
        """
        from_code = self.get_segment_value(segment_type_name, 'from')
        to_code = self.get_segment_value(segment_type_name, 'to')
        
        return from_code and to_code and from_code != to_code
    
    def validate_segments(self):
        """
        Validate that all required segments are present and valid.
        
        Returns:
            dict: {'valid': bool, 'errors': list}
        """
        from account_and_entitys.managers.segment_manager import SegmentManager
        
        segments_dict = self.get_segments_dict()
        
        # Convert to validation format
        validation_data = {}
        for seg_id, seg_data in segments_dict.items():
            validation_data[seg_id] = {
                'from': seg_data.get('from_code'),
                'to': seg_data.get('to_code')
            }
        
        return SegmentManager.validate_transaction_segments(validation_data)







