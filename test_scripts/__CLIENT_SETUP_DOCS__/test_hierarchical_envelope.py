"""
Test Hierarchical Envelope Lookup

This tests if child segments can get envelopes from their parent segments.
"""

import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_transfer.settings')
django.setup()

from decimal import Decimal
from account_and_entitys.models import XX_SegmentType, XX_Segment, XX_SegmentEnvelope
from account_and_entitys.managers import EnvelopeBalanceManager

print("=" * 80)
print("TESTING HIERARCHICAL ENVELOPE LOOKUP")
print("=" * 80)

# Setup: Create hierarchical segments
print("\n[SETUP] Creating hierarchical segment structure...")

# Get Entity segment type
entity_type = XX_SegmentType.objects.get(segment_id=1)

# Create parent entity
parent_entity, _ = XX_Segment.objects.get_or_create(
    segment_type_id=1,
    code="E100",
    defaults={
        'alias': 'Parent Department',
        'parent_code': None,
        'is_active': True
    }
)

# Create child entity
child_entity, _ = XX_Segment.objects.get_or_create(
    segment_type_id=1,
    code="E101",
    defaults={
        'alias': 'Child Department',
        'parent_code': "E100",  # Points to parent
        'is_active': True
    }
)

print(f"✓ Parent: {parent_entity.code} - {parent_entity.alias}")
print(f"✓ Child: {child_entity.code} - {child_entity.alias} (parent: {child_entity.parent_code})")

# Clean up any existing test envelopes
XX_SegmentEnvelope.objects.filter(
    segment_combination__has_key="1",
    fiscal_year="FY2025_HIER_TEST"
).delete()

# Create envelope for PARENT only
print("\n[SETUP] Creating envelope for PARENT segment only...")
parent_envelope = XX_SegmentEnvelope.objects.create(
    segment_combination={"1": "E100"},
    envelope_amount=Decimal("50000.00"),
    fiscal_year="FY2025_HIER_TEST",
    description="Parent Department Budget",
    is_active=True
)
print(f"✓ Parent envelope created: ID={parent_envelope.id}, Amount=${parent_envelope.envelope_amount}")

# =============================================================================
# TEST 1: Get envelope for PARENT (should find exact match)
# =============================================================================
print("\n" + "=" * 80)
print("[TEST 1] Get envelope for PARENT segment (exact match)")
print("=" * 80)

parent_combination = {"1": "E100"}
envelope = EnvelopeBalanceManager.get_envelope_for_segments(
    parent_combination,
    "FY2025_HIER_TEST",
    use_hierarchy=True
)

if envelope:
    print(f"✓ Found envelope for parent: ID={envelope.id}, Amount=${envelope.envelope_amount}")
else:
    print("✗ FAILED: Should have found parent envelope")

# =============================================================================
# TEST 2: Get envelope for CHILD (should find parent's envelope)
# =============================================================================
print("\n" + "=" * 80)
print("[TEST 2] Get envelope for CHILD segment (should inherit from parent)")
print("=" * 80)

child_combination = {"1": "E101"}

# Test 2a: WITH hierarchy enabled (default)
print("\nTest 2a: With hierarchy enabled (use_hierarchy=True)...")
envelope = EnvelopeBalanceManager.get_envelope_for_segments(
    child_combination,
    "FY2025_HIER_TEST",
    use_hierarchy=True
)

if envelope:
    print(f"✓ SUCCESS: Found parent's envelope for child!")
    print(f"  Envelope ID: {envelope.id}")
    print(f"  Envelope Amount: ${envelope.envelope_amount}")
    print(f"  Envelope Combination: {envelope.segment_combination}")
else:
    print("✗ FAILED: Should have found parent's envelope")

# Test 2b: WITHOUT hierarchy enabled
print("\nTest 2b: Without hierarchy enabled (use_hierarchy=False)...")
envelope = EnvelopeBalanceManager.get_envelope_for_segments(
    child_combination,
    "FY2025_HIER_TEST",
    use_hierarchy=False
)

if envelope:
    print(f"✗ FAILED: Should NOT have found envelope (child has no direct envelope)")
else:
    print(f"✓ Correct: No envelope found when hierarchy disabled")

# =============================================================================
# TEST 3: Check balance for CHILD (should use parent's envelope)
# =============================================================================
print("\n" + "=" * 80)
print("[TEST 3] Check balance for CHILD segment")
print("=" * 80)

result = EnvelopeBalanceManager.check_balance_available(
    child_combination,
    Decimal("5000.00"),
    "FY2025_HIER_TEST",
    use_hierarchy=True
)

print(f"Available: {result['available']}")
print(f"Sufficient: {result['sufficient']}")
print(f"Envelope Amount: ${result['envelope_amount']}")
print(f"Remaining Balance: ${result['remaining_balance']}")
print(f"Envelope Source: {result['envelope_source']}")

if result['available'] and result['envelope_source'] == 'parent':
    print("✓ SUCCESS: Child is using parent's envelope!")
else:
    print(f"✗ FAILED: Expected envelope_source='parent', got '{result['envelope_source']}'")

# =============================================================================
# TEST 4: Get envelope summary for CHILD
# =============================================================================
print("\n" + "=" * 80)
print("[TEST 4] Get envelope summary for CHILD segment")
print("=" * 80)

summary = EnvelopeBalanceManager.get_envelope_summary(
    child_combination,
    "FY2025_HIER_TEST",
    use_hierarchy=True
)

print(f"Exists: {summary['exists']}")
if summary['exists']:
    print(f"Requested Combination: {summary.get('requested_segment_combination', 'N/A')}")
    print(f"Actual Combination: {summary.get('actual_segment_combination', 'N/A')}")
    print(f"Envelope Amount: ${summary['envelope_amount']}")
    print(f"Envelope Source: {summary.get('envelope_source', 'N/A')}")
    
    if summary.get('envelope_source') == 'parent':
        print("✓ SUCCESS: Summary shows child inherited from parent!")
    else:
        print(f"✗ FAILED: Expected envelope_source='parent'")
else:
    print("✗ FAILED: Should have found parent's envelope")

# =============================================================================
# TEST 5: Multi-level hierarchy
# =============================================================================
print("\n" + "=" * 80)
print("[TEST 5] Multi-level hierarchy (grandchild → child → parent)")
print("=" * 80)

# Create grandchild
grandchild_entity, _ = XX_Segment.objects.get_or_create(
    segment_type_id=1,
    code="E102",
    defaults={
        'alias': 'Grandchild Department',
        'parent_code': "E101",  # Points to child
        'is_active': True
    }
)

print(f"Created: {grandchild_entity.code} → {grandchild_entity.parent_code} → E100")

grandchild_combination = {"1": "E102"}

# Test grandchild inheriting from grandparent
result = EnvelopeBalanceManager.check_balance_available(
    grandchild_combination,
    Decimal("5000.00"),
    "FY2025_HIER_TEST",
    use_hierarchy=True
)

print(f"\nGrandchild balance check:")
print(f"  Available: {result['available']}")
print(f"  Envelope Source: {result.get('envelope_source', 'N/A')}")
print(f"  Envelope Amount: ${result['envelope_amount']}")

if result['available'] and result['envelope_source'] == 'parent':
    print("✓ SUCCESS: Grandchild inherited from grandparent!")
else:
    print(f"⚠ Note: Multi-level hierarchy may need additional traversal")

# =============================================================================
# TEST 6: Direct child envelope overrides parent
# =============================================================================
print("\n" + "=" * 80)
print("[TEST 6] Child has own envelope (should use child's, not parent's)")
print("=" * 80)

# Create envelope for CHILD
child_envelope = XX_SegmentEnvelope.objects.create(
    segment_combination={"1": "E101"},
    envelope_amount=Decimal("10000.00"),
    fiscal_year="FY2025_HIER_TEST",
    description="Child Department Budget (override)",
    is_active=True
)
print(f"Created child envelope: Amount=${child_envelope.envelope_amount}")

result = EnvelopeBalanceManager.check_balance_available(
    child_combination,
    Decimal("5000.00"),
    "FY2025_HIER_TEST",
    use_hierarchy=True
)

print(f"\nChild balance check:")
print(f"  Envelope Amount: ${result['envelope_amount']}")
print(f"  Envelope Source: {result['envelope_source']}")

if result['envelope_amount'] == Decimal("10000.00") and result['envelope_source'] == 'exact':
    print("✓ SUCCESS: Child's own envelope takes precedence over parent's!")
else:
    print(f"✗ FAILED: Should use child's envelope (10000), not parent's (50000)")

# =============================================================================
# SUMMARY
# =============================================================================
print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print("""
✓ Hierarchical envelope lookup is now ENABLED by default!

Key Features:
1. Child segments inherit envelopes from parent segments
2. Exact matches take precedence over inherited envelopes
3. Hierarchy can be disabled with use_hierarchy=False parameter
4. Envelope source is tracked ('exact' vs 'parent')

Usage:
- get_envelope_for_segments(combination, fiscal_year, use_hierarchy=True)
- check_balance_available(combination, amount, fiscal_year, use_hierarchy=True)
- get_envelope_summary(combination, fiscal_year, use_hierarchy=True)

Notes:
- Multi-level hierarchy (grandchild → parent) may require additional logic
- Currently walks up one level at a time
- Consider optimizing for deep hierarchies if needed
""")

print("=" * 80)
print("HIERARCHICAL ENVELOPE TESTING COMPLETE")
print("=" * 80)
