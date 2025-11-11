"""
Quick script to verify segment level corrections
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_transfer.settings')
django.setup()

from account_and_entitys.models import XX_Segment, XX_SegmentType

print("=" * 70)
print("Segment Level Verification")
print("=" * 70)

# Get all segment types
segment_types = XX_SegmentType.objects.all().order_by('segment_id')

for seg_type in segment_types:
    print(f"\n{seg_type.segment_name} (ID: {seg_type.segment_id})")
    print("-" * 70)
    
    # Get level distribution
    segments = XX_Segment.objects.filter(segment_type=seg_type)
    total = segments.count()
    
    print(f"Total segments: {total}")
    
    # Count by level
    from django.db.models import Count
    level_counts = segments.values('level').annotate(count=Count('level')).order_by('level')
    
    print("\nLevel Distribution:")
    for item in level_counts:
        level = item['level']
        count = item['count']
        print(f"  Level {level}: {count} segments")
    
    # Show some examples from each level
    print("\nExamples:")
    for level in range(0, 8):
        examples = segments.filter(level=level).order_by('code')[:3]
        if examples.exists():
            print(f"  Level {level}:")
            for seg in examples:
                parent_display = seg.parent_code if seg.parent_code else "ROOT"
                print(f"    - {seg.code} (parent: {parent_display}) - {seg.alias or 'No alias'}")

# Test specific hierarchy
print("\n" + "=" * 70)
print("Hierarchy Test: Entity 11000 and its children")
print("=" * 70)

root = XX_Segment.objects.filter(segment_type_id=1, code='11000').first()
if root:
    print(f"\nRoot: {root.code} (Level {root.level}, Parent: {root.parent_code or 'NULL'})")
    print(f"Alias: {root.alias}")
    
    # Get children
    children = XX_Segment.objects.filter(segment_type_id=1, parent_code=root.code).order_by('code')
    if children.exists():
        print(f"\nChildren of {root.code}:")
        for child in children:
            print(f"  - {child.code} (Level {child.level}) - {child.alias}")
            
            # Get grandchildren
            grandchildren = XX_Segment.objects.filter(segment_type_id=1, parent_code=child.code).order_by('code')
            if grandchildren.exists():
                print(f"    Grandchildren:")
                for gc in grandchildren:
                    print(f"      - {gc.code} (Level {gc.level}) - {gc.alias}")

# Test account hierarchy
print("\n" + "=" * 70)
print("Hierarchy Test: Account 51000 and its children")
print("=" * 70)

acc_root = XX_Segment.objects.filter(segment_type_id=2, code='51000').first()
if acc_root:
    print(f"\nRoot: {acc_root.code} (Level {acc_root.level}, Parent: {acc_root.parent_code or 'NULL'})")
    print(f"Alias: {acc_root.alias}")
    
    # Get children
    children = XX_Segment.objects.filter(segment_type_id=2, parent_code=acc_root.code).order_by('code')
    if children.exists():
        print(f"\nChildren of {acc_root.code}: ({children.count()} total)")
        for child in children[:5]:  # Show first 5
            print(f"  - {child.code} (Level {child.level}) - {child.alias}")

# Verify level 0 only has roots (no parent or empty parent)
print("\n" + "=" * 70)
print("Verification: All Level 0 segments should have no parent")
print("=" * 70)

level_0_with_parent = XX_Segment.objects.filter(level=0).exclude(
    parent_code__isnull=True
).exclude(parent_code='')

if level_0_with_parent.exists():
    print(f"\n⚠️  WARNING: Found {level_0_with_parent.count()} level 0 segments WITH parents!")
    for seg in level_0_with_parent[:5]:
        print(f"  - {seg.code} (Type: {seg.segment_type.segment_name}, Parent: {seg.parent_code})")
else:
    print("\n✅ All level 0 segments are correctly root nodes (no parent)")

print("\n" + "=" * 70)
print("Verification Complete!")
print("=" * 70)
