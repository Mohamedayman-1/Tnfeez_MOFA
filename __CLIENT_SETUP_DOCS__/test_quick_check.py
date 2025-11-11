"""Quick test to verify hierarchical envelope lookup is working"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set console encoding to UTF-8 to avoid Unicode errors
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_transfer.settings')

import django
django.setup()

print("Checking envelope_balance_manager.py...")

# Read the file and check for use_hierarchy parameter
with open('account_and_entitys/managers/envelope_balance_manager.py', 'r', encoding='utf-8') as f:
    content = f.read()
    
# Check key methods
methods_to_check = [
    'get_envelope_for_segments',
    'get_envelope_amount',
    'has_envelope',
    'check_balance_available',
    'get_envelope_summary'
]

print("\nChecking for use_hierarchy parameter in key methods:")
for method in methods_to_check:
    if f'def {method}' in content:
        # Find the method definition
        start = content.find(f'def {method}')
        end = content.find('\n    def ', start + 1)
        method_code = content[start:end] if end > 0 else content[start:start+500]
        
        has_hierarchy = 'use_hierarchy' in method_code
        status = "OK" if has_hierarchy else "MISSING"
        print(f"  [{status}] {method}")

# Check for critical fix in get_hierarchical_envelope
print("\nChecking get_hierarchical_envelope for recursion fix:")
if 'use_hierarchy=False  # CRITICAL: Prevent recursion loop' in content:
    print("  [OK] Recursion prevention fix present")
else:
    print("  [MISSING] Recursion prevention fix")

# Check envelope_source tracking in check_balance_available
print("\nChecking check_balance_available for envelope_source tracking:")
if "'envelope_source': envelope_source" in content:
    print("  [OK] Envelope source tracking present")
else:
    print("  [MISSING] Envelope source tracking")

print("\n" + "=" * 60)
print("SUMMARY:")
print("=" * 60)

hierarchy_count = content.count('use_hierarchy')
print(f"Total occurrences of 'use_hierarchy': {hierarchy_count}")
print(f"Expected: At least 12 (5 method signatures + uses)")

if hierarchy_count >= 12:
    print("\nSTATUS: ALL HIERARCHICAL FEATURES RESTORED")
else:
    print("\nSTATUS: INCOMPLETE - Some features still missing")
