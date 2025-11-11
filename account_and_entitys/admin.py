from django.contrib import admin
from .models import (
    XX_Account, XX_Entity, XX_PivotFund, XX_Project, XX_BalanceReport,
    XX_SegmentType, XX_Segment, XX_TransactionSegment, XX_DynamicBalanceReport,
    XX_SegmentEnvelope, XX_SegmentMapping, XX_SegmentTransferLimit
)


@admin.register(XX_Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("id", "account", "parent", "alias_default")
    search_fields = ("account", "alias_default")
    list_filter = ("parent",)


@admin.register(XX_Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "parent", "alias_default")
    search_fields = ("project", "alias_default")
    list_filter = ("parent",)


@admin.register(XX_Entity)
class EntityAdmin(admin.ModelAdmin):
    list_display = ("id", "entity", "parent", "alias_default")
    search_fields = ("entity", "alias_default")
    list_filter = ("parent",)


@admin.register(XX_PivotFund)
class PivotFundAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "entity",
        "account",
        "project",
        "year",
        "budget",
        "fund",
        "actual",
        "encumbrance",
    )
    list_filter = ("year",)
    search_fields = ("entity__entity", "account__account", "project__project")


@admin.register(XX_BalanceReport)
class BalanceReportAdmin(admin.ModelAdmin):
    """Admin interface for Balance Report model"""
    list_display = (
        "id",
        "control_budget_name",
        "ledger_name", 
        "as_of_period",
        "segment1",
        "segment2", 
        "segment3",
        "budget_ytd",
        "actual_ytd",
        "funds_available_asof",
        "created_at"
    )
    list_filter = (
        "control_budget_name",
        "ledger_name", 
        "as_of_period",
        "created_at"
    )
    search_fields = (
        "control_budget_name",
        "ledger_name",
        "segment1", 
        "segment2",
        "segment3"
    )
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    
    fieldsets = (
        ("Basic Information", {
            "fields": ("control_budget_name", "ledger_name", "as_of_period")
        }),
        ("Segments", {
            "fields": ("segment1", "segment2", "segment3")
        }),
        ("Financial Data", {
            "fields": (
                "encumbrance_ytd", 
                "other_ytd", 
                "actual_ytd", 
                "funds_available_asof", 
                "budget_ytd"
            )
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        })
    )


# @admin.register(MainCurrency)
# class MainCurrencyAdmin(admin.ModelAdmin):
#     list_display = ('id', 'name', 'icon')
#     search_fields = ('name',)
#     list_filter = ('name',)

# @admin.register(MainRoutesName)
# class MainRoutesNameAdmin(admin.ModelAdmin):
#     list_display = ('id', 'english_name', 'arabic_name')
#     search_fields = ('english_name', 'arabic_name')
#     list_filter = ('english_name',)


# ============================================================================
# DYNAMIC SEGMENT ADMINISTRATION
# ============================================================================

@admin.register(XX_SegmentType)
class SegmentTypeAdmin(admin.ModelAdmin):
    """Admin interface for dynamic segment type configuration."""
    list_display = (
        "segment_id",
        "segment_name",
        "segment_type",
        "oracle_segment_number",
        "is_required",
        "has_hierarchy",
        "is_active",
        "display_order"
    )
    list_filter = (
        "is_required",
        "has_hierarchy",
        "is_active",
        "segment_type"
    )
    search_fields = ("segment_name", "segment_type", "description")
    ordering = ("display_order", "segment_id")
    
    fieldsets = (
        ("Basic Configuration", {
            "fields": (
                "segment_id",
                "segment_name",
                "segment_type",
                "description"
            )
        }),
        ("Display & Validation", {
            "fields": (
                "display_order",
                "max_length",
                "is_required",
                "has_hierarchy",
                "is_active"
            )
        }),
        ("Oracle Integration", {
            "fields": ("oracle_segment_number",),
            "description": "Maps to Oracle Fusion SEGMENT1-SEGMENT30 columns"
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        })
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(XX_Segment)
class SegmentValueAdmin(admin.ModelAdmin):
    """Admin interface for segment values (replaces Entity/Account/Project)."""
    list_display = (
        "id",
        "segment_type",
        "code",
        "parent_code",
        "alias",
        "level",
        # envelope_amount removed - now in XX_SegmentEnvelope model
        "is_active"
    )
    list_filter = (
        "segment_type",
        "is_active",
        "level"
    )
    search_fields = ("code", "alias", "parent_code")
    ordering = ("segment_type", "code")
    autocomplete_fields = ["segment_type"]
    
    fieldsets = (
        ("Segment Information", {
            "fields": (
                "segment_type",
                "code",
                "alias"
            )
        }),
        ("Hierarchy", {
            "fields": (
                "parent_code",
                "level"
            ),
            "description": "For hierarchical segments, set parent_code to establish relationships"
        }),
        ("Status", {
            "fields": (
                # envelope_amount removed - now managed in XX_SegmentEnvelope model
                "is_active",
            )
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        })
    )
    readonly_fields = ("created_at", "updated_at")
    
    def get_queryset(self, request):
        """Optimize queries with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related("segment_type")


@admin.register(XX_TransactionSegment)
class TransactionSegmentAdmin(admin.ModelAdmin):
    """Admin interface for transaction-segment linkage."""
    list_display = (
        "id",
        "transaction_transfer",
        "segment_type",
        "from_segment_value",
        "to_segment_value",
        "created_at"
    )
    list_filter = (
        "segment_type",
        "created_at"
    )
    search_fields = (
        "transaction_transfer__transaction_code",
        "from_segment_value__code",
        "to_segment_value__code"
    )
    ordering = ("-created_at",)
    autocomplete_fields = ["segment_type"]
    
    fieldsets = (
        ("Transaction Link", {
            "fields": ("transaction_transfer",)
        }),
        ("Segment Assignment", {
            "fields": (
                "segment_type",
                "segment_value",
                "from_segment_value",
                "to_segment_value"
            )
        }),
        ("Timestamp", {
            "fields": ("created_at",),
            "classes": ("collapse",)
        })
    )
    readonly_fields = ("created_at",)
    
    def get_queryset(self, request):
        """Optimize queries with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related("transaction_transfer", "segment_type", "segment_value", "from_segment_value", "to_segment_value")


@admin.register(XX_DynamicBalanceReport)
class DynamicBalanceReportAdmin(admin.ModelAdmin):
    """Admin interface for dynamic balance reports from Oracle."""
    list_display = (
        "id",
        "control_budget_name",
        "ledger_name",
        "as_of_period",
        "display_segments",
        "budget_ytd",
        "actual_ytd",
        "funds_available_asof",
        "created_at"
    )
    list_filter = (
        "control_budget_name",
        "ledger_name",
        "as_of_period",
        "created_at"
    )
    search_fields = (
        "control_budget_name",
        "ledger_name",
        "segment_values"
    )
    ordering = ("-created_at",)
    
    fieldsets = (
        ("Report Information", {
            "fields": (
                "control_budget_name",
                "ledger_name",
                "as_of_period"
            )
        }),
        ("Segment Values", {
            "fields": ("segment_values",),
            "description": "JSON structure: {segment_id: segment_code, ...}"
        }),
        ("Financial Data", {
            "fields": (
                "encumbrance_ytd",
                "other_ytd",
                "actual_ytd",
                "funds_available_asof",
                "budget_ytd"
            )
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        })
    )
    readonly_fields = ("created_at", "updated_at")
    
    def display_segments(self, obj):
        """Display segment values in a readable format."""
        if not obj.segment_values:
            return "-"
        segments = []
        for seg_id, seg_code in sorted(obj.segment_values.items()):
            segments.append(f"S{seg_id}: {seg_code}")
        return " | ".join(segments)
    display_segments.short_description = "Segments"


# ============================================
# PHASE 3: ENVELOPE AND MAPPING ADMIN
# ============================================

@admin.register(XX_SegmentEnvelope)
class SegmentEnvelopeAdmin(admin.ModelAdmin):
    """Admin interface for segment envelopes (Phase 3)."""
    list_display = (
        "id",
        "display_segment_combination",
        "envelope_amount",
        "fiscal_year",
        "is_active",
        "created_at"
    )
    list_filter = (
        "fiscal_year",
        "is_active",
        "created_at"
    )
    search_fields = (
        "segment_combination",
        "fiscal_year",
        "description"
    )
    ordering = ("-created_at",)
    
    fieldsets = (
        ("Segment Combination", {
            "fields": ("segment_combination",),
            "description": "JSON structure: {segment_type_id: segment_code, ...}"
        }),
        ("Envelope Details", {
            "fields": (
                "envelope_amount",
                "fiscal_year",
                "description"
            )
        }),
        ("Status", {
            "fields": ("is_active",)
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        })
    )
    readonly_fields = ("created_at", "updated_at")
    
    def display_segment_combination(self, obj):
        """Display segment combination in a readable format."""
        if not obj.segment_combination:
            return "-"
        segments = []
        for seg_id, seg_code in sorted(obj.segment_combination.items(), key=lambda x: int(x[0])):
            try:
                seg_type = XX_SegmentType.objects.get(segment_id=int(seg_id))
                segments.append(f"{seg_type.segment_name}: {seg_code}")
            except XX_SegmentType.DoesNotExist:
                segments.append(f"S{seg_id}: {seg_code}")
        return " | ".join(segments)
    display_segment_combination.short_description = "Segments"


@admin.register(XX_SegmentMapping)
class SegmentMappingAdmin(admin.ModelAdmin):
    """Admin interface for segment mappings (Phase 3)."""
    list_display = (
        "id",
        "segment_type",
        "display_source_segment",
        "display_target_segment",
        "mapping_type",
        "is_active",
        "created_at"
    )
    list_filter = (
        "segment_type",
        "mapping_type",
        "is_active",
        "created_at"
    )
    search_fields = (
        "source_segment__code",
        "target_segment__code",
        "description"
    )
    ordering = ("segment_type", "source_segment__code")
    
    fieldsets = (
        ("Mapping Definition", {
            "fields": (
                "segment_type",
                "source_segment",
                "target_segment",
                "mapping_type"
            )
        }),
        ("Details", {
            "fields": ("description",)
        }),
        ("Status", {
            "fields": ("is_active",)
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        })
    )
    readonly_fields = ("created_at", "updated_at")
    
    def display_source_segment(self, obj):
        """Display source segment with code and alias."""
        return f"{obj.source_segment.code} ({obj.source_segment.alias or 'No alias'})"
    display_source_segment.short_description = "Source"
    
    def display_target_segment(self, obj):
        """Display target segment with code and alias."""
        return f"{obj.target_segment.code} ({obj.target_segment.alias or 'No alias'})"
    display_target_segment.short_description = "Target"


@admin.register(XX_SegmentTransferLimit)
class SegmentTransferLimitAdmin(admin.ModelAdmin):
    """Admin interface for segment transfer limits (Phase 3)."""
    list_display = (
        "id",
        "display_segment_combination",
        "is_transfer_allowed",
        "is_transfer_allowed_as_source",
        "is_transfer_allowed_as_target",
        "display_usage",
        "fiscal_year",
        "is_active"
    )
    list_filter = (
        "is_transfer_allowed",
        "is_transfer_allowed_as_source",
        "is_transfer_allowed_as_target",
        "is_active",
        "fiscal_year",
        "created_at"
    )
    search_fields = (
        "segment_combination",
        "notes"
    )
    ordering = ("-created_at",)
    
    fieldsets = (
        ("Segment Combination", {
            "fields": ("segment_combination", "fiscal_year"),
            "description": "JSON structure: {segment_type_id: segment_code, ...}"
        }),
        ("Transfer Permissions", {
            "fields": (
                "is_transfer_allowed",
                "is_transfer_allowed_as_source",
                "is_transfer_allowed_as_target"
            )
        }),
        ("Transfer Limits", {
            "fields": (
                "max_source_transfers",
                "max_target_transfers",
                "source_count",
                "target_count"
            )
        }),
        ("Details", {
            "fields": ("notes",)
        }),
        ("Status", {
            "fields": ("is_active",)
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        })
    )
    readonly_fields = ("created_at", "updated_at", "source_count", "target_count")
    
    def display_segment_combination(self, obj):
        """Display segment combination in a readable format."""
        if not obj.segment_combination:
            return "-"
        segments = []
        for seg_id, seg_code in sorted(obj.segment_combination.items(), key=lambda x: int(x[0])):
            try:
                seg_type = XX_SegmentType.objects.get(segment_id=int(seg_id))
                segments.append(f"{seg_type.segment_name}: {seg_code}")
            except XX_SegmentType.DoesNotExist:
                segments.append(f"S{seg_id}: {seg_code}")
        return " | ".join(segments)
    display_segment_combination.short_description = "Segments"
    
    def display_usage(self, obj):
        """Display source/target usage counts."""
        source = f"Src: {obj.source_count or 0}"
        target = f"Tgt: {obj.target_count or 0}"
        
        if obj.max_source_transfers:
            source += f"/{obj.max_source_transfers}"
        if obj.max_target_transfers:
            target += f"/{obj.max_target_transfers}"
        
        return f"{source} | {target}"
    display_usage.short_description = "Usage"
