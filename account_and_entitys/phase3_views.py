"""
Phase 3 REST API Views
======================
REST API endpoints for Envelope, Mapping, and Transfer Limit management.
Uses new simplified segment structure: {"1": "E001", "2": "A100", "3": "P001"}
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from decimal import Decimal
from django.db import transaction as db_transaction

from .models import (
    XX_SegmentEnvelope,
    XX_SegmentMapping,
    XX_SegmentTransferLimit,
    XX_Segment,
    XX_SegmentType
)
from .managers.envelope_balance_manager import EnvelopeBalanceManager
from .managers.segment_mapping_manager import SegmentMappingManager
from .managers.segment_transfer_limit_manager import SegmentTransferLimitManager


# ============================================================================
# ENVELOPE VIEWS
# ============================================================================

class SegmentEnvelopeListCreateView(APIView):
    """
    List all envelopes or create a new envelope.
    
    GET: List envelopes with optional filters
    POST: Create new envelope
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        List envelopes with optional filters.
        
        Query Parameters:
        - fiscal_year: Filter by fiscal year
        - segment_type: Filter by segment type ID
        - segment_code: Filter by segment code
        - is_active: Filter by active status (default: true)
        """
        try:
            fiscal_year = request.query_params.get('fiscal_year')
            segment_type = request.query_params.get('segment_type')
            segment_code = request.query_params.get('segment_code')
            is_active = request.query_params.get('is_active', 'true').lower() == 'true'
            
            # Base query
            envelopes = XX_SegmentEnvelope.objects.filter(is_active=is_active)
            
            # Apply filters
            if fiscal_year:
                envelopes = envelopes.filter(fiscal_year=fiscal_year)
            
            if segment_type and segment_code:
                # Filter by specific segment in combination
                matching_envelopes = []
                for env in envelopes:
                    if env.segment_combination.get(str(segment_type)) == segment_code:
                        matching_envelopes.append(env)
                envelopes = matching_envelopes
            
            # Serialize data
            data = []
            for env in (envelopes if isinstance(envelopes, list) else envelopes.all()):
                data.append({
                    'id': env.id,
                    'segment_combination': env.segment_combination,
                    'envelope_amount': str(env.envelope_amount),
                    'fiscal_year': env.fiscal_year,
                    'description': env.description,
                    'is_active': env.is_active,
                    'created_at': env.created_at.isoformat(),
                    'updated_at': env.updated_at.isoformat()
                })
            
            return Response({
                'success': True,
                'count': len(data),
                'envelopes': data
            })
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """
        Create a new envelope.
        
        Request Body:
        {
            "segment_combination": {"1": "E001", "2": "A100"},
            "envelope_amount": "100000.00",
            "fiscal_year": "FY2025",
            "description": "Budget for E001-A100",
            "is_active": true
        }
        """
        try:
            data = request.data
            
            # Validate required fields
            if 'segment_combination' not in data:
                return Response({
                    'success': False,
                    'error': 'segment_combination is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if 'envelope_amount' not in data:
                return Response({
                    'success': False,
                    'error': 'envelope_amount is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate segment combination
            segment_combination = data['segment_combination']
            if not isinstance(segment_combination, dict):
                return Response({
                    'success': False,
                    'error': 'segment_combination must be a dictionary'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate segments exist
            for seg_type_id, seg_code in segment_combination.items():
                try:
                    segment = XX_Segment.objects.get(
                        segment_type_id=int(seg_type_id),
                        code=seg_code,
                        is_active=True
                    )
                except XX_Segment.DoesNotExist:
                    return Response({
                        'success': False,
                        'error': f'Segment {seg_code} not found for segment type {seg_type_id}'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create envelope
            envelope = XX_SegmentEnvelope.objects.create(
                segment_combination=segment_combination,
                envelope_amount=Decimal(str(data['envelope_amount'])),
                fiscal_year=data.get('fiscal_year'),
                description=data.get('description'),
                is_active=data.get('is_active', True)
            )
            
            return Response({
                'success': True,
                'message': 'Envelope created successfully',
                'envelope': {
                    'id': envelope.id,
                    'segment_combination': envelope.segment_combination,
                    'envelope_amount': str(envelope.envelope_amount),
                    'fiscal_year': envelope.fiscal_year,
                    'description': envelope.description,
                    'is_active': envelope.is_active,
                    'created_at': envelope.created_at.isoformat()
                }
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SegmentEnvelopeDetailView(APIView):
    """
    Get, update, or delete a specific envelope.
    
    GET: Get envelope details
    PUT: Update envelope
    DELETE: Delete envelope
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, envelope_id):
        """Get envelope details by ID"""
        try:
            envelope = XX_SegmentEnvelope.objects.get(id=envelope_id)
            
            # Get consumed balance
            consumed = EnvelopeBalanceManager.calculate_consumed_balance(
                envelope.segment_combination,
                envelope.fiscal_year
            )
            
            remaining = envelope.envelope_amount - consumed
            utilization = (consumed / envelope.envelope_amount * 100) if envelope.envelope_amount > 0 else 0
            
            return Response({
                'success': True,
                'envelope': {
                    'id': envelope.id,
                    'segment_combination': envelope.segment_combination,
                    'envelope_amount': str(envelope.envelope_amount),
                    'consumed_amount': str(consumed),
                    'remaining_balance': str(remaining),
                    'utilization_percent': float(utilization),
                    'fiscal_year': envelope.fiscal_year,
                    'description': envelope.description,
                    'is_active': envelope.is_active,
                    'created_at': envelope.created_at.isoformat(),
                    'updated_at': envelope.updated_at.isoformat()
                }
            })
        
        except XX_SegmentEnvelope.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Envelope not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request, envelope_id):
        """Update envelope"""
        try:
            envelope = XX_SegmentEnvelope.objects.get(id=envelope_id)
            data = request.data
            
            # Update fields
            if 'envelope_amount' in data:
                envelope.envelope_amount = Decimal(str(data['envelope_amount']))
            if 'fiscal_year' in data:
                envelope.fiscal_year = data['fiscal_year']
            if 'description' in data:
                envelope.description = data['description']
            if 'is_active' in data:
                envelope.is_active = data['is_active']
            
            envelope.save()
            
            return Response({
                'success': True,
                'message': 'Envelope updated successfully',
                'envelope': {
                    'id': envelope.id,
                    'segment_combination': envelope.segment_combination,
                    'envelope_amount': str(envelope.envelope_amount),
                    'fiscal_year': envelope.fiscal_year,
                    'description': envelope.description,
                    'is_active': envelope.is_active,
                    'updated_at': envelope.updated_at.isoformat()
                }
            })
        
        except XX_SegmentEnvelope.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Envelope not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, envelope_id):
        """Delete envelope (soft delete by setting is_active=False)"""
        try:
            envelope = XX_SegmentEnvelope.objects.get(id=envelope_id)
            envelope.is_active = False
            envelope.save()
            
            return Response({
                'success': True,
                'message': 'Envelope deactivated successfully'
            })
        
        except XX_SegmentEnvelope.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Envelope not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SegmentEnvelopeCheckBalanceView(APIView):
    """
    Check balance availability for a segment combination.
    Supports hierarchical lookup.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Check if sufficient balance is available.
        
        Request Body:
        {
            "segment_combination": {"1": "E001", "2": "A100"},
            "required_amount": "5000.00",
            "fiscal_year": "FY2025",
            "use_hierarchy": true
        }
        """
        try:
            data = request.data
            
            # Validate required fields
            if 'segment_combination' not in data:
                return Response({
                    'success': False,
                    'error': 'segment_combination is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if 'required_amount' not in data:
                return Response({
                    'success': False,
                    'error': 'required_amount is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            segment_combination = data['segment_combination']
            required_amount = Decimal(str(data['required_amount']))
            fiscal_year = data.get('fiscal_year')
            use_hierarchy = data.get('use_hierarchy', True)
            
            # Check balance
            result = EnvelopeBalanceManager.check_balance_available(
                segment_combination,
                required_amount,
                fiscal_year,
                use_hierarchy
            )
            
            # Convert Decimal to string for JSON
            if 'envelope_amount' in result:
                result['envelope_amount'] = str(result['envelope_amount'])
            if 'consumed_amount' in result:
                result['consumed_amount'] = str(result['consumed_amount'])
            if 'remaining_balance' in result:
                result['remaining_balance'] = str(result['remaining_balance'])
            
            return Response({
                'success': True,
                'balance_check': result
            })
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SegmentEnvelopeSummaryView(APIView):
    """Get comprehensive envelope summary with hierarchy details"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Get envelope summary.
        
        Request Body:
        {
            "segment_combination": {"1": "E001", "2": "A100"},
            "fiscal_year": "FY2025",
            "use_hierarchy": true
        }
        """
        try:
            data = request.data
            
            if 'segment_combination' not in data:
                return Response({
                    'success': False,
                    'error': 'segment_combination is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            segment_combination = data['segment_combination']
            fiscal_year = data.get('fiscal_year')
            use_hierarchy = data.get('use_hierarchy', True)
            
            # Get summary
            summary = EnvelopeBalanceManager.get_envelope_summary(
                segment_combination,
                fiscal_year,
                use_hierarchy
            )
            
            # Convert Decimal to string
            if 'envelope_amount' in summary:
                summary['envelope_amount'] = str(summary['envelope_amount'])
            if 'consumed_amount' in summary:
                summary['consumed_amount'] = str(summary['consumed_amount'])
            if 'remaining_balance' in summary:
                summary['remaining_balance'] = str(summary['remaining_balance'])
            
            return Response({
                'success': True,
                'summary': summary
            })
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# MAPPING VIEWS
# ============================================================================

class SegmentMappingListCreateView(APIView):
    """
    List all mappings or create a new mapping.
    
    GET: List mappings with optional filters
    POST: Create new mapping
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """List mappings with optional filters"""
        try:
            segment_type_id = request.query_params.get('segment_type')
            source_code = request.query_params.get('source_code')
            target_code = request.query_params.get('target_code')
            is_active = request.query_params.get('is_active', 'true').lower() == 'true'
            
            # Base query
            mappings = XX_SegmentMapping.objects.filter(is_active=is_active)
            
            # Apply filters
            if segment_type_id:
                mappings = mappings.filter(segment_type_id=int(segment_type_id))
            if source_code:
                mappings = mappings.filter(source_segment__code=source_code)
            if target_code:
                mappings = mappings.filter(target_segment__code=target_code)
            
            # Serialize data
            data = []
            for mapping in mappings:
                data.append({
                    'id': mapping.id,
                    'segment_type_id': mapping.segment_type_id,
                    'segment_type_name': mapping.segment_type.segment_name,
                    'source_code': mapping.source_segment.code,
                    'source_alias': mapping.source_segment.alias,
                    'target_code': mapping.target_segment.code,
                    'target_alias': mapping.target_segment.alias,
                    'mapping_type': mapping.mapping_type,
                    'description': mapping.description,
                    'is_active': mapping.is_active,
                    'created_at': mapping.created_at.isoformat()
                })
            
            return Response({
                'success': True,
                'count': len(data),
                'mappings': data
            })
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """Create a new mapping"""
        try:
            data = request.data
            
            # Validate required fields
            required_fields = ['segment_type_id', 'source_code', 'target_code']
            for field in required_fields:
                if field not in data:
                    return Response({
                        'success': False,
                        'error': f'{field} is required'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            segment_type_id = int(data['segment_type_id'])
            source_code = data['source_code']
            target_code = data['target_code']
            
            # Get segments
            try:
                source_segment = XX_Segment.objects.get(
                    segment_type_id=segment_type_id,
                    code=source_code
                )
                target_segment = XX_Segment.objects.get(
                    segment_type_id=segment_type_id,
                    code=target_code
                )
            except XX_Segment.DoesNotExist as e:
                return Response({
                    'success': False,
                    'error': f'Segment not found: {str(e)}'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Validate no circular mapping
            validation = SegmentMappingManager.validate_no_circular_mapping(
                segment_type_id,
                source_code,
                target_code
            )
            
            if not validation['valid']:
                return Response({
                    'success': False,
                    'error': validation['errors'][0]
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create mapping
            mapping = XX_SegmentMapping.objects.create(
                segment_type_id=segment_type_id,
                source_segment=source_segment,
                target_segment=target_segment,
                mapping_type=data.get('mapping_type', 'STANDARD'),
                description=data.get('description'),
                is_active=data.get('is_active', True)
            )
            
            return Response({
                'success': True,
                'message': 'Mapping created successfully',
                'mapping': {
                    'id': mapping.id,
                    'segment_type_id': mapping.segment_type_id,
                    'source_code': mapping.source_segment.code,
                    'target_code': mapping.target_segment.code,
                    'mapping_type': mapping.mapping_type,
                    'description': mapping.description,
                    'is_active': mapping.is_active
                }
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SegmentMappingDetailView(APIView):
    """Get, update, or delete a specific mapping"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, mapping_id):
        """Get mapping details"""
        try:
            mapping = XX_SegmentMapping.objects.get(id=mapping_id)
            
            return Response({
                'success': True,
                'mapping': {
                    'id': mapping.id,
                    'segment_type_id': mapping.segment_type_id,
                    'segment_type_name': mapping.segment_type.segment_name,
                    'source_code': mapping.source_segment.code,
                    'source_alias': mapping.source_segment.alias,
                    'target_code': mapping.target_segment.code,
                    'target_alias': mapping.target_segment.alias,
                    'mapping_type': mapping.mapping_type,
                    'description': mapping.description,
                    'is_active': mapping.is_active,
                    'created_at': mapping.created_at.isoformat(),
                    'updated_at': mapping.updated_at.isoformat()
                }
            })
        
        except XX_SegmentMapping.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Mapping not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request, mapping_id):
        """Update mapping"""
        try:
            mapping = XX_SegmentMapping.objects.get(id=mapping_id)
            data = request.data
            
            # Update fields
            if 'mapping_type' in data:
                mapping.mapping_type = data['mapping_type']
            if 'description' in data:
                mapping.description = data['description']
            if 'is_active' in data:
                mapping.is_active = data['is_active']
            
            mapping.save()
            
            return Response({
                'success': True,
                'message': 'Mapping updated successfully',
                'mapping': {
                    'id': mapping.id,
                    'mapping_type': mapping.mapping_type,
                    'description': mapping.description,
                    'is_active': mapping.is_active
                }
            })
        
        except XX_SegmentMapping.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Mapping not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, mapping_id):
        """Delete mapping"""
        try:
            mapping = XX_SegmentMapping.objects.get(id=mapping_id)
            mapping.is_active = False
            mapping.save()
            
            return Response({
                'success': True,
                'message': 'Mapping deactivated successfully'
            })
        
        except XX_SegmentMapping.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Mapping not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SegmentMappingLookupView(APIView):
    """Lookup mappings for a segment"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Lookup mappings for source or target.
        
        Request Body:
        {
            "segment_type_id": 2,
            "source_code": "A101",  // OR
            "target_code": "A200",  // For reverse lookup
            "apply_to_combination": {"1": "E001", "2": "A101"}  // Optional
        }
        """
        try:
            data = request.data
            
            # Apply to combination mode doesn't need segment_type_id
            if 'apply_to_combination' in data:
                combination = data['apply_to_combination']
                mapped = SegmentMappingManager.apply_mapping_to_combination(combination)
                
                return Response({
                    'success': True,
                    'lookup_type': 'combination',
                    'original_combination': combination,
                    'mapped_combination': mapped
                })
            
            # For forward/reverse lookup, segment_type_id is required
            if 'segment_type_id' not in data:
                return Response({
                    'success': False,
                    'error': 'segment_type_id is required for forward/reverse lookup'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            segment_type_id = int(data['segment_type_id'])
            
            # Forward lookup
            if 'source_code' in data:
                source_code = data['source_code']
                targets = SegmentMappingManager.get_target_segments(
                    segment_type_id,
                    source_code
                )
                
                return Response({
                    'success': True,
                    'lookup_type': 'forward',
                    'source_code': source_code,
                    'target_codes': targets
                })
            
            # Reverse lookup
            elif 'target_code' in data:
                target_code = data['target_code']
                sources = SegmentMappingManager.get_source_segments(
                    segment_type_id,
                    target_code
                )
                
                return Response({
                    'success': True,
                    'lookup_type': 'reverse',
                    'target_code': target_code,
                    'source_codes': sources
                })
            
            else:
                return Response({
                    'success': False,
                    'error': 'Either source_code or target_code is required'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# TRANSFER LIMIT VIEWS
# ============================================================================

class SegmentTransferLimitListCreateView(APIView):
    """List all transfer limits or create a new limit"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """List transfer limits with optional filters"""
        try:
            fiscal_year = request.query_params.get('fiscal_year')
            is_active = request.query_params.get('is_active', 'true').lower() == 'true'
            
            # Base query
            limits = XX_SegmentTransferLimit.objects.filter(is_active=is_active)
            
            # Apply filters
            if fiscal_year:
                limits = limits.filter(fiscal_year=fiscal_year)
            
            # Serialize data
            data = []
            for limit in limits:
                data.append({
                    'id': limit.id,
                    'segment_combination': limit.segment_combination,
                    'is_transfer_allowed': limit.is_transfer_allowed,
                    'is_transfer_allowed_as_source': limit.is_transfer_allowed_as_source,
                    'is_transfer_allowed_as_target': limit.is_transfer_allowed_as_target,
                    'source_count': limit.source_count,
                    'target_count': limit.target_count,
                    'max_source_transfers': limit.max_source_transfers,
                    'max_target_transfers': limit.max_target_transfers,
                    'fiscal_year': limit.fiscal_year,
                    'notes': limit.notes,
                    'is_active': limit.is_active,
                    'created_at': limit.created_at.isoformat()
                })
            
            return Response({
                'success': True,
                'count': len(data),
                'limits': data
            })
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """Create a new transfer limit"""
        try:
            data = request.data
            
            if 'segment_combination' not in data:
                return Response({
                    'success': False,
                    'error': 'segment_combination is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create limit
            limit = XX_SegmentTransferLimit.objects.create(
                segment_combination=data['segment_combination'],
                is_transfer_allowed=data.get('is_transfer_allowed', True),
                is_transfer_allowed_as_source=data.get('is_transfer_allowed_as_source', True),
                is_transfer_allowed_as_target=data.get('is_transfer_allowed_as_target', True),
                max_source_transfers=data.get('max_source_transfers'),
                max_target_transfers=data.get('max_target_transfers'),
                source_count=data.get('source_count', 0),
                target_count=data.get('target_count', 0),
                fiscal_year=data.get('fiscal_year'),
                notes=data.get('notes'),
                is_active=data.get('is_active', True)
            )
            
            return Response({
                'success': True,
                'message': 'Transfer limit created successfully',
                'limit': {
                    'id': limit.id,
                    'segment_combination': limit.segment_combination,
                    'is_transfer_allowed_as_source': limit.is_transfer_allowed_as_source,
                    'is_transfer_allowed_as_target': limit.is_transfer_allowed_as_target,
                    'max_source_transfers': limit.max_source_transfers,
                    'max_target_transfers': limit.max_target_transfers
                }
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SegmentTransferLimitDetailView(APIView):
    """Get, update, or delete a specific transfer limit"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, limit_id):
        """Get limit details"""
        try:
            limit = XX_SegmentTransferLimit.objects.get(id=limit_id)
            
            return Response({
                'success': True,
                'limit': {
                    'id': limit.id,
                    'segment_combination': limit.segment_combination,
                    'is_transfer_allowed': limit.is_transfer_allowed,
                    'is_transfer_allowed_as_source': limit.is_transfer_allowed_as_source,
                    'is_transfer_allowed_as_target': limit.is_transfer_allowed_as_target,
                    'source_count': limit.source_count,
                    'target_count': limit.target_count,
                    'max_source_transfers': limit.max_source_transfers,
                    'max_target_transfers': limit.max_target_transfers,
                    'fiscal_year': limit.fiscal_year,
                    'notes': limit.notes,
                    'is_active': limit.is_active,
                    'created_at': limit.created_at.isoformat(),
                    'updated_at': limit.updated_at.isoformat()
                }
            })
        
        except XX_SegmentTransferLimit.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Transfer limit not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request, limit_id):
        """Update limit"""
        try:
            limit = XX_SegmentTransferLimit.objects.get(id=limit_id)
            data = request.data
            
            # Update fields
            if 'is_transfer_allowed' in data:
                limit.is_transfer_allowed = data['is_transfer_allowed']
            if 'is_transfer_allowed_as_source' in data:
                limit.is_transfer_allowed_as_source = data['is_transfer_allowed_as_source']
            if 'is_transfer_allowed_as_target' in data:
                limit.is_transfer_allowed_as_target = data['is_transfer_allowed_as_target']
            if 'max_source_transfers' in data:
                limit.max_source_transfers = data['max_source_transfers']
            if 'max_target_transfers' in data:
                limit.max_target_transfers = data['max_target_transfers']
            if 'notes' in data:
                limit.notes = data['notes']
            if 'is_active' in data:
                limit.is_active = data['is_active']
            
            limit.save()
            
            return Response({
                'success': True,
                'message': 'Transfer limit updated successfully'
            })
        
        except XX_SegmentTransferLimit.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Transfer limit not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, limit_id):
        """Delete limit"""
        try:
            limit = XX_SegmentTransferLimit.objects.get(id=limit_id)
            limit.is_active = False
            limit.save()
            
            return Response({
                'success': True,
                'message': 'Transfer limit deactivated successfully'
            })
        
        except XX_SegmentTransferLimit.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Transfer limit not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SegmentTransferLimitValidateView(APIView):
    """Validate transfer permissions"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Validate if transfer is allowed.
        
        Request Body:
        {
            "segment_combination": {"1": "E001", "2": "A100"},
            "direction": "source",  // or "target"
            "fiscal_year": "FY2025"
        }
        """
        try:
            data = request.data
            
            if 'segment_combination' not in data:
                return Response({
                    'success': False,
                    'error': 'segment_combination is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if 'direction' not in data:
                return Response({
                    'success': False,
                    'error': 'direction is required (source or target)'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            segment_combination = data['segment_combination']
            direction = data['direction'].lower()
            fiscal_year = data.get('fiscal_year')
            
            # Validate direction
            if direction == 'source':
                result = SegmentTransferLimitManager.can_transfer_from_segments(
                    segment_combination,
                    fiscal_year
                )
            elif direction == 'target':
                result = SegmentTransferLimitManager.can_transfer_to_segments(
                    segment_combination,
                    fiscal_year
                )
            else:
                return Response({
                    'success': False,
                    'error': 'direction must be either "source" or "target"'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Convert limit object to dict if present
            if result.get('limit'):
                limit = result['limit']
                result['limit'] = {
                    'id': limit.id,
                    'segment_combination': limit.segment_combination,
                    'source_count': limit.source_count,
                    'target_count': limit.target_count,
                    'max_source_transfers': limit.max_source_transfers,
                    'max_target_transfers': limit.max_target_transfers
                }
            
            return Response({
                'success': True,
                'validation': result
            })
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
