"""
User Ability Manager

Manages user abilities on dynamic segment combinations.
Replaces legacy xx_UserAbility with flexible segment-based abilities.

Phase 4: User Models Update
"""

from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.db.models import Q


class UserAbilityManager:
    """
    Manager for XX_UserSegmentAbility model operations.
    
    Provides methods for granting, revoking, and checking user abilities
    on segment combinations (edit, approve, transfer, etc.)
    """
    
    @staticmethod
    def grant_ability(user, ability_type, segment_combination, granted_by=None, notes=''):
        """
        Grant user an ability for a specific segment combination.
        
        Args:
            user: xx_User instance
            ability_type: str - One of: EDIT, APPROVE, VIEW, DELETE, TRANSFER, REPORT
            segment_combination: dict - {segment_type_id: segment_code}
            granted_by: xx_User instance (optional)
            notes: str - Additional notes
            
        Returns:
            dict: {
                'success': bool,
                'ability': XX_UserSegmentAbility instance or None,
                'errors': list,
                'created': bool
            }
        """
        from user_management.models import XX_UserSegmentAbility
        from account_and_entitys.models import XX_SegmentType, XX_Segment
        
        errors = []
        
        try:
            # Validate ability type
            valid_types = [choice[0] for choice in XX_UserSegmentAbility.ABILITY_TYPE_CHOICES]
            if ability_type not in valid_types:
                errors.append(f"Invalid ability type '{ability_type}'. Must be one of: {valid_types}")
                return {'success': False, 'ability': None, 'errors': errors, 'created': False}
            
            # Validate segment combination
            if not isinstance(segment_combination, dict) or not segment_combination:
                errors.append("segment_combination must be a non-empty dictionary")
                return {'success': False, 'ability': None, 'errors': errors, 'created': False}
            
            # Validate each segment exists
            for seg_type_id, seg_code in segment_combination.items():
                try:
                    seg_type = XX_SegmentType.objects.get(segment_id=int(seg_type_id), is_active=True)
                    segment = XX_Segment.objects.get(
                        segment_type=seg_type,
                        code=str(seg_code),
                        is_active=True
                    )
                except XX_SegmentType.DoesNotExist:
                    errors.append(f"Segment type {seg_type_id} not found or inactive")
                    return {'success': False, 'ability': None, 'errors': errors, 'created': False}
                except XX_Segment.DoesNotExist:
                    errors.append(f"Segment '{seg_code}' not found in segment type {seg_type_id} or inactive")
                    return {'success': False, 'ability': None, 'errors': errors, 'created': False}
            
            # Normalize segment_combination keys/values to strings
            normalized_combination = {
                str(k): str(v) for k, v in segment_combination.items()
            }
            
            # Check if ability already exists
            existing = XX_UserSegmentAbility.objects.filter(
                user=user,
                ability_type=ability_type,
                segment_combination=normalized_combination
            ).first()
            
            if existing:
                if not existing.is_active:
                    # Reactivate
                    existing.is_active = True
                    existing.granted_by = granted_by
                    existing.notes = notes
                    existing.save()
                    return {
                        'success': True,
                        'ability': existing,
                        'errors': [],
                        'created': False
                    }
                else:
                    return {
                        'success': True,
                        'ability': existing,
                        'errors': ['Ability already exists and is active'],
                        'created': False
                    }
            
            # Create new ability
            ability = XX_UserSegmentAbility.objects.create(
                user=user,
                ability_type=ability_type,
                segment_combination=normalized_combination,
                is_active=True,
                granted_by=granted_by,
                notes=notes
            )
            
            return {
                'success': True,
                'ability': ability,
                'errors': [],
                'created': True
            }
            
        except Exception as e:
            errors.append(f"Error granting ability: {str(e)}")
            return {'success': False, 'ability': None, 'errors': errors, 'created': False}
    
    @staticmethod
    def revoke_ability(user, ability_type, segment_combination=None, soft_delete=True):
        """
        Revoke user ability.
        
        Args:
            user: xx_User instance
            ability_type: str - Ability type to revoke
            segment_combination: dict (optional) - Specific segment combination, or None for all
            soft_delete: bool - If True, mark as inactive; if False, delete completely
            
        Returns:
            dict: {
                'success': bool,
                'revoked_count': int,
                'errors': list
            }
        """
        from user_management.models import XX_UserSegmentAbility
        
        errors = []
        
        try:
            query = XX_UserSegmentAbility.objects.filter(
                user=user,
                ability_type=ability_type
            )
            
            if segment_combination:
                # Normalize
                normalized = {str(k): str(v) for k, v in segment_combination.items()}
                query = query.filter(segment_combination=normalized)
            
            count = query.count()
            
            if count == 0:
                return {
                    'success': True,
                    'revoked_count': 0,
                    'errors': ['No matching ability found to revoke']
                }
            
            # Revoke
            if soft_delete:
                query.update(is_active=False)
            else:
                query.delete()
            
            return {
                'success': True,
                'revoked_count': count,
                'errors': []
            }
            
        except Exception as e:
            errors.append(f"Error revoking ability: {str(e)}")
            return {'success': False, 'revoked_count': 0, 'errors': errors}
    
    @staticmethod
    def check_user_has_ability(user, ability_type, segment_combination):
        """
        Check if user has a specific ability for given segment combination.
        
        Args:
            user: xx_User instance
            ability_type: str - Ability type to check
            segment_combination: dict - {segment_type_id: segment_code}
            
        Returns:
            dict: {
                'has_ability': bool,
                'ability': XX_UserSegmentAbility instance or None,
                'matched_combinations': list
            }
        """
        from user_management.models import XX_UserSegmentAbility
        
        try:
            # Get all active abilities of this type for user
            abilities = XX_UserSegmentAbility.objects.filter(
                user=user,
                ability_type=ability_type,
                is_active=True
            )
            
            # Normalize input
            normalized_input = {str(k): str(v) for k, v in segment_combination.items()}
            
            # Check each ability to see if it matches
            matched_combinations = []
            matching_ability = None
            
            for ability in abilities:
                if ability.matches_segments(normalized_input):
                    matched_combinations.append(ability.segment_combination)
                    if not matching_ability:
                        matching_ability = ability
            
            return {
                'has_ability': len(matched_combinations) > 0,
                'ability': matching_ability,
                'matched_combinations': matched_combinations
            }
            
        except Exception as e:
            return {
                'has_ability': False,
                'ability': None,
                'matched_combinations': [],
                'error': str(e)
            }
    
    @staticmethod
    def get_user_abilities(user, ability_type=None, segment_type_id=None, include_inactive=False):
        """
        Get all abilities for a user.
        
        Args:
            user: xx_User instance
            ability_type: str (optional) - Filter by ability type
            segment_type_id: int (optional) - Filter by segment type
            include_inactive: bool - Include inactive abilities
            
        Returns:
            dict: {
                'success': bool,
                'abilities': list of dicts,
                'count': int,
                'errors': list
            }
        """
        from user_management.models import XX_UserSegmentAbility
        
        errors = []
        
        try:
            query = XX_UserSegmentAbility.objects.filter(user=user)
            
            if ability_type:
                query = query.filter(ability_type=ability_type)
            
            if not include_inactive:
                query = query.filter(is_active=True)
            
            abilities = []
            for ability in query:
                # Filter by segment type if specified
                if segment_type_id:
                    if str(segment_type_id) not in ability.segment_combination:
                        continue
                
                abilities.append({
                    'id': ability.id,
                    'ability_type': ability.ability_type,
                    'segment_combination': ability.segment_combination,
                    'segment_display': ability.get_segment_display(),
                    'is_active': ability.is_active,
                    'granted_at': ability.granted_at,
                    'granted_by': ability.granted_by.username if ability.granted_by else None,
                    'notes': ability.notes
                })
            
            return {
                'success': True,
                'abilities': abilities,
                'count': len(abilities),
                'errors': []
            }
            
        except Exception as e:
            errors.append(f"Error retrieving user abilities: {str(e)}")
            return {'success': False, 'abilities': [], 'count': 0, 'errors': errors}
    
    @staticmethod
    def get_users_with_ability(ability_type, segment_combination=None, include_inactive=False):
        """
        Get all users who have a specific ability.
        
        Args:
            ability_type: str - Ability type to search
            segment_combination: dict (optional) - Specific segment combination
            include_inactive: bool - Include inactive abilities
            
        Returns:
            dict: {
                'success': bool,
                'users': list of dicts,
                'count': int,
                'errors': list
            }
        """
        from user_management.models import XX_UserSegmentAbility
        
        errors = []
        
        try:
            query = XX_UserSegmentAbility.objects.filter(
                ability_type=ability_type
            ).select_related('user', 'granted_by')
            
            if segment_combination:
                normalized = {str(k): str(v) for k, v in segment_combination.items()}
                query = query.filter(segment_combination=normalized)
            
            if not include_inactive:
                query = query.filter(is_active=True)
            
            users = []
            for ability in query:
                users.append({
                    'user_id': ability.user.id,
                    'username': ability.user.username,
                    'segment_combination': ability.segment_combination,
                    'segment_display': ability.get_segment_display(),
                    'granted_at': ability.granted_at,
                    'is_active': ability.is_active
                })
            
            return {
                'success': True,
                'users': users,
                'count': len(users),
                'errors': []
            }
            
        except Exception as e:
            errors.append(f"Error retrieving users with ability: {str(e)}")
            return {'success': False, 'users': [], 'count': 0, 'errors': errors}
    
    @staticmethod
    def bulk_grant_abilities(user, abilities, granted_by=None):
        """
        Grant multiple abilities to a user in bulk.
        
        Args:
            user: xx_User instance
            abilities: list of dicts [{
                'ability_type': str,
                'segment_combination': dict,
                'notes': str (optional)
            }]
            granted_by: xx_User instance (optional)
            
        Returns:
            dict: {
                'success': bool,
                'granted_count': int,
                'failed_count': int,
                'results': list,
                'errors': list
            }
        """
        results = []
        granted_count = 0
        failed_count = 0
        
        for ability_data in abilities:
            result = UserAbilityManager.grant_ability(
                user=user,
                ability_type=ability_data['ability_type'],
                segment_combination=ability_data['segment_combination'],
                granted_by=granted_by,
                notes=ability_data.get('notes', '')
            )
            
            results.append(result)
            
            if result['success']:
                granted_count += 1
            else:
                failed_count += 1
        
        return {
            'success': failed_count == 0,
            'granted_count': granted_count,
            'failed_count': failed_count,
            'results': results,
            'errors': [r['errors'] for r in results if not r['success']]
        }
    
    @staticmethod
    def validate_ability_for_operation(user, operation, segment_combination):
        """
        Validate if user has ability to perform an operation on segment combination.
        
        Maps operations to ability types and checks permission.
        
        Args:
            user: xx_User instance
            operation: str - Operation name (e.g., 'edit_transfer', 'approve_transfer')
            segment_combination: dict - {segment_type_id: segment_code}
            
        Returns:
            dict: {
                'allowed': bool,
                'reason': str or None,
                'ability': XX_UserSegmentAbility or None
            }
        """
        # Map operations to ability types
        operation_mapping = {
            'edit': 'EDIT',
            'edit_transfer': 'EDIT',
            'modify': 'EDIT',
            'approve': 'APPROVE',
            'approve_transfer': 'APPROVE',
            'view': 'VIEW',
            'delete': 'DELETE',
            'transfer': 'TRANSFER',
            'transfer_budget': 'TRANSFER',
            'report': 'REPORT',
            'generate_report': 'REPORT',
        }
        
        ability_type = operation_mapping.get(operation.lower())
        
        if not ability_type:
            return {
                'allowed': False,
                'reason': f"Unknown operation '{operation}'",
                'ability': None
            }
        
        # Check if user has the ability
        result = UserAbilityManager.check_user_has_ability(
            user=user,
            ability_type=ability_type,
            segment_combination=segment_combination
        )
        
        if result['has_ability']:
            return {
                'allowed': True,
                'reason': None,
                'ability': result['ability']
            }
        else:
            return {
                'allowed': False,
                'reason': f"User does not have '{ability_type}' ability for this segment combination",
                'ability': None
            }
