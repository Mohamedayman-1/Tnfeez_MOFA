import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_transfer.settings')
django.setup()

from account_and_entitys.models import XX_Segment_Funds

print("Total records:", XX_Segment_Funds.objects.count())
print("\nFirst 5 records:")
for fund in XX_Segment_Funds.objects.all()[:5]:
    print(f"ID: {fund.id}, Segment5: '{fund.Segment5}', Segment9: '{fund.Segment9}', Segment11: '{fund.Segment11}'")

print("\nDistinct Segment5 values (first 10):")
for val in XX_Segment_Funds.objects.values_list('Segment5', flat=True).distinct()[:10]:
    print(f"  '{val}'")
