# Visual Architecture Diagrams

## System Architecture Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLIENT INSTALLATION                          │
│                                                                  │
│  1. Run: python manage.py setup_client --interactive            │
│     └─► Creates: XX_SegmentType records in database             │
│                                                                  │
│  2. Load master data (segments values)                          │
│     └─► Creates: XX_Segment records                             │
│                                                                  │
│  3. System ready for transactions!                              │
└─────────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RUNTIME OPERATIONS                            │
│                                                                  │
│  User creates Budget Transfer                                   │
│         │                                                        │
│         ├─► Frontend calls: GET /api/segments/types/config/     │
│         │   Response: {"segments": [Entity, Account, Project]}  │
│         │                                                        │
│         ├─► Frontend renders dynamic form with 3 dropdowns      │
│         │                                                        │
│         ├─► User selects: Entity=12345, Account=67890, ...      │
│         │                                                        │
│         └─► Frontend calls: POST /api/transfers/                │
│             Body: {                                              │
│               "segments": {                                      │
│                 "Entity": "12345",                               │
│                 "Account": "67890",                              │
│                 "Project": "98765"                               │
│               },                                                 │
│               "from_center": 1000,                               │
│               "to_center": 500                                   │
│             }                                                    │
│         │                                                        │
│         ├─► Backend: SegmentManager.validate_transaction_segments() │
│         │   ✓ All required segments present                     │
│         │   ✓ Segment codes exist in database                   │
│         │                                                        │
│         ├─► Backend: Create xx_TransactionTransfer record       │
│         │                                                        │
│         └─► Backend: Create XX_TransactionSegment records       │
│             (one per segment type)                               │
└─────────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ORACLE INTEGRATION                             │
│                                                                  │
│  Transaction approved → Generate FBDI                            │
│         │                                                        │
│         ├─► journal_template_manager.create_sample_journal_data_dynamic() │
│         │   Reads: XX_TransactionSegment records                │
│         │   Maps to: SEGMENT1, SEGMENT2, SEGMENT3, ...          │
│         │   Generates: Excel with GL_INTERFACE sheet            │
│         │                                                        │
│         ├─► upload_fbdi_to_oracle()                             │
│         │   Converts Excel → CSV → ZIP                          │
│         │   POSTs to Oracle SOAP API                            │
│         │                                                        │
│         └─► Oracle imports journal entry ✅                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Database Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                         SEGMENT CONFIGURATION                    │
└─────────────────────────────────────────────────────────────────┘

    XX_SegmentType                         XX_Segment
    ┌──────────────────┐                   ┌────────────────────┐
    │ segment_id (PK)  │◄─────────────────┤ segment_type_id    │
    │ segment_name     │  1            ∞   │ code               │
    │ oracle_seg_num   │                   │ parent_code        │
    │ is_required      │                   │ alias              │
    │ has_hierarchy    │                   │ envelope_amount    │
    └──────────────────┘                   └────────────────────┘
            │                                       │
            │                                       │
            │ Example Data:                         │ Example Data:
            │ ┌──────────────────────┐             │ ┌─────────────────┐
            │ │ id=1, name=Entity    │             │ │ type_id=1       │
            │ │ id=2, name=Account   │             │ │ code=12345      │
            │ │ id=3, name=Project   │             │ │ parent=1000     │
            │ └──────────────────────┘             │ │ alias=Main Dept │
            │                                       │ └─────────────────┘
            │                                       │
            ▼                                       ▼

┌─────────────────────────────────────────────────────────────────┐
│                      TRANSACTION SEGMENTS                        │
└─────────────────────────────────────────────────────────────────┘

    xx_BudgetTransfer
    ┌───────────────────┐
    │ transaction_id    │
    │ amount            │        1
    │ status            │◄───────────┐
    │ requested_by      │            │
    └───────────────────┘            │
            │                        │
            │ 1                      │
            │                        │
            ▼ ∞                      │
    xx_TransactionTransfer            │
    ┌───────────────────┐            │
    │ transfer_id       │            │
    │ transaction_id    │────────────┘
    │ from_center       │        1
    │ to_center         │◄───────────┐
    │ [legacy fields]   │            │
    └───────────────────┘            │
            │                        │
            │ 1                      │
            │                        │
            ▼ ∞                      │
    XX_TransactionSegment             │
    ┌──────────────────────┐         │
    │ transaction_transfer │─────────┘
    │ segment_type         │──┐
    │ segment_value        │──│──► Points to XX_SegmentType
    │ from_segment_value   │  │
    │ to_segment_value     │  └───► Points to XX_Segment
    └──────────────────────┘

    Example Transaction Segments:
    ┌────────────────────────────────────────────────┐
    │ Transaction 123 has 3 segment records:         │
    │                                                │
    │ 1. segment_type=Entity,  value=12345           │
    │ 2. segment_type=Account, value=67890           │
    │ 3. segment_type=Project, value=98765           │
    └────────────────────────────────────────────────┘
```

---

## Oracle Balance Report Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     ORACLE BALANCE REPORT                        │
└─────────────────────────────────────────────────────────────────┘

    1. Download from Oracle (Excel)
    ┌─────────────────────────────────────────────┐
    │ Control Budget │ Ledger │ Period │ Segment1 │ Segment2 │ Segment3 │ Budget YTD │
    │ Main Budget    │ 1001   │ Sep-25 │ 12345    │ 67890    │ 98765    │ 1000000    │
    │ Main Budget    │ 1001   │ Sep-25 │ 12346    │ 67891    │ 98766    │ 500000     │
    └─────────────────────────────────────────────┘
            ▼
    2. Parse with parse_balance_report_dynamic()
       - Detects segment columns (Segment1, Segment2, ...)
       - Maps to client's segment configuration
       - Extracts financial data
            ▼
    3. Store in XX_DynamicBalanceReport
    ┌──────────────────────────────────────────────┐
    │ id │ period │ segment_values (JSON)          │ budget_ytd │
    │ 1  │ Sep-25 │ {"1":"12345","2":"67890",...}  │ 1000000    │
    │ 2  │ Sep-25 │ {"1":"12346","2":"67891",...}  │ 500000     │
    └──────────────────────────────────────────────┘
            ▼
    4. Query by segment
       query_balance_by_segments(
           segment_filters={1: "12345", 2: "67890"},
           as_of_period="Sep-25"
       )
       → Returns matching balance records
```

---

## Segment Hierarchy Example

```
┌─────────────────────────────────────────────────────────────────┐
│                  HIERARCHICAL SEGMENT STRUCTURE                  │
│                        (Example: Entity)                         │
└─────────────────────────────────────────────────────────────────┘

    Database Records (XX_Segment):
    ┌────────────────────────────────────────────┐
    │ code  │ parent_code │ alias              │
    │ 1000  │ NULL        │ Main Organization  │
    │ 1100  │ 1000        │ Finance Dept       │
    │ 1110  │ 1100        │ Accounting         │
    │ 1120  │ 1100        │ Budgeting          │
    │ 1200  │ 1000        │ Operations Dept    │
    │ 1210  │ 1200        │ Logistics          │
    └────────────────────────────────────────────┘

    Tree Representation:
    
    1000 (Main Organization)
    │
    ├─── 1100 (Finance Dept)
    │    │
    │    ├─── 1110 (Accounting)
    │    │
    │    └─── 1120 (Budgeting)
    │
    └─── 1200 (Operations Dept)
         │
         └─── 1210 (Logistics)

    API Call:
    GET /api/segments/types/1/hierarchy/
    
    Response:
    {
      "segment_type": "Entity",
      "hierarchy": [
        {
          "code": "1000",
          "alias": "Main Organization",
          "level": 0,
          "children": [
            {
              "code": "1100",
              "alias": "Finance Dept",
              "level": 1,
              "children": [
                {"code": "1110", "alias": "Accounting", "level": 2, "children": []},
                {"code": "1120", "alias": "Budgeting", "level": 2, "children": []}
              ]
            },
            {
              "code": "1200",
              "alias": "Operations Dept",
              "level": 1,
              "children": [
                {"code": "1210", "alias": "Logistics", "level": 2, "children": []}
              ]
            }
          ]
        }
      ]
    }

    Usage in Dashboard:
    - User has access to "1100" (Finance Dept)
    - SegmentManager.get_all_children('Entity', '1100')
      Returns: ['1110', '1120']
    - Dashboard shows transactions for: 1100, 1110, 1120
```

---

## Client Comparison: 2-Segment vs 5-Segment

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT A (2 Segments)                     │
└─────────────────────────────────────────────────────────────────┘

    Configuration:
    {
      "segments": [
        {"segment_id": 1, "segment_name": "Entity"},
        {"segment_id": 2, "segment_name": "Account"}
      ]
    }

    Transaction Form:
    ┌────────────────────────────┐
    │ Entity:   [Dropdown]       │
    │ Account:  [Dropdown]       │
    │ Amount:   [_______]        │
    │                            │
    │ [Submit Transfer]          │
    └────────────────────────────┘

    Oracle GL_INTERFACE:
    ┌───────────────────────────────────────────────┐
    │ SEGMENT1 │ SEGMENT2 │ SEGMENT3 │ ... │ DR   │
    │ 12345    │ 67890    │ NULL     │ ... │ 1000 │
    └───────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────┐
│                      CLIENT B (5 Segments)                       │
└─────────────────────────────────────────────────────────────────┘

    Configuration:
    {
      "segments": [
        {"segment_id": 1, "segment_name": "Entity"},
        {"segment_id": 2, "segment_name": "Account"},
        {"segment_id": 3, "segment_name": "Project"},
        {"segment_id": 4, "segment_name": "LineItem"},
        {"segment_id": 5, "segment_name": "Department"}
      ]
    }

    Transaction Form:
    ┌────────────────────────────┐
    │ Entity:     [Dropdown]     │
    │ Account:    [Dropdown]     │
    │ Project:    [Dropdown]     │
    │ LineItem:   [Dropdown]     │
    │ Department: [Dropdown]     │
    │ Amount:     [_______]      │
    │                            │
    │ [Submit Transfer]          │
    └────────────────────────────┘

    Oracle GL_INTERFACE:
    ┌───────────────────────────────────────────────────────┐
    │ SEGMENT1 │ SEGMENT2 │ SEGMENT3 │ SEGMENT4 │ SEGMENT5 │ DR   │
    │ 12345    │ 67890    │ 98765    │ ABC123   │ DEP001   │ 1000 │
    └───────────────────────────────────────────────────────┘

    ✅ Same codebase handles both!
```

---

## Migration Timeline Visual

```
┌─────────────────────────────────────────────────────────────────┐
│                    MIGRATION TIMELINE (13 Weeks)                 │
└─────────────────────────────────────────────────────────────────┘

Week 1-2: Core Models & Configuration
▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 20h
├─ Create XX_SegmentType, XX_Segment models
├─ Build SegmentManager class
└─ Configuration file structure

Week 3-4: Database Migration
░░░░░░░░░░░░░░▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░ 40h
├─ Data migration scripts
├─ Backward compatibility layer
└─ Testing with both old/new systems

Week 5-6: Business Logic
░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓▓▓▓▓▓▓▓▓▓▓▓▓▓ 60h
├─ Update transaction creation logic
├─ Dynamic validation
└─ Envelope/hierarchy management

Week 7-8: API & Serializers
▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 40h
├─ New API endpoints
├─ Dynamic serializers
└─ ViewSets for segments

Week 9-10: Oracle Integration
░░░░░░░░░░░░░░▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░ 40h
├─ Dynamic FBDI generation
├─ Balance report parsing
└─ Testing with Oracle sandbox

Week 11-12: Setup & Deployment
░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓▓▓▓▓▓▓▓▓▓▓▓▓▓ 20h
├─ setup_client command
├─ Deployment scripts
└─ Documentation

Week 13: Testing & Training
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓▓ 40h
├─ Comprehensive testing
├─ User acceptance testing
└─ Team training

Total: 260 hours (~13 weeks with 1 developer)
       130 hours (~7 weeks with 2 developers)
       65 hours (~3-4 weeks with 4 developers)
```

---

## Before & After Code Comparison

```python
┌─────────────────────────────────────────────────────────────────┐
│                          BEFORE (Hardcoded)                      │
└─────────────────────────────────────────────────────────────────┘

# Creating a transaction (OLD WAY)
transaction = xx_TransactionTransfer.objects.create(
    transaction_id=123,
    cost_center_code=12345,  # ❌ Hardcoded Entity
    account_code=67890,      # ❌ Hardcoded Account
    project_code="98765",    # ❌ Hardcoded Project
    from_center=1000,
    to_center=500
)

# Querying (OLD WAY)
transfers = xx_TransactionTransfer.objects.filter(
    cost_center_code=12345  # ❌ Only works for Entity
)

# Hierarchy (OLD WAY)
children = EnvelopeManager.get_all_children(
    XX_Project.objects.all(),  # ❌ Hardcoded to projects
    "100"
)


┌─────────────────────────────────────────────────────────────────┐
│                           AFTER (Dynamic)                        │
└─────────────────────────────────────────────────────────────────┘

# Creating a transaction (NEW WAY)
transaction = xx_TransactionTransfer.objects.create(
    transaction_id=123,
    from_center=1000,
    to_center=500
)

# Assign dynamic segments ✅ Works with any number of segments
segments = {
    "Entity": "12345",
    "Account": "67890",
    "Project": "98765",
    "LineItem": "ABC123"  # ✅ Can add more!
}
SegmentManager.create_transaction_segments(transaction, segments)

# Querying (NEW WAY) ✅ Works for any segment type
from account_and_entitys.models import XX_TransactionSegment

transfers = xx_TransactionTransfer.objects.filter(
    transaction_segments__segment_type__segment_name='Entity',
    transaction_segments__segment_value__code='12345'
).distinct()

# Hierarchy (NEW WAY) ✅ Works for any hierarchical segment
children = SegmentManager.get_all_children(
    'Entity',  # ✅ or 'Account', 'Project', any configured segment
    "100"
)
```

---

## Frontend Integration Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     FRONTEND (React/Vue/Angular)                 │
└─────────────────────────────────────────────────────────────────┘

1. App Initialization
   ┌──────────────────────────────────────┐
   │ componentDidMount() {                │
   │   fetchSegmentConfig()               │
   │ }                                    │
   └──────────────────────────────────────┘
            │
            ▼
   GET /api/segments/types/config/
   
   Response:
   {
     "segments": [
       {
         "segment_id": 1,
         "segment_name": "Entity",
         "is_required": true,
         "has_hierarchy": true
       },
       {
         "segment_id": 2,
         "segment_name": "Account",
         "is_required": true,
         "has_hierarchy": true
       },
       ...
     ]
   }
            │
            ▼
2. Dynamic Form Rendering
   ┌──────────────────────────────────────────────┐
   │ {segments.map(segment => (                   │
   │   <FormField key={segment.segment_id}>       │
   │     <label>{segment.segment_name}</label>    │
   │     {segment.has_hierarchy ? (               │
   │       <HierarchicalSelect                    │
   │         name={segment.segment_name}          │
   │         required={segment.is_required}       │
   │         endpoint={`/api/segments/types/      │
   │                    ${segment.segment_id}/    │
   │                    values/`}                 │
   │       />                                     │
   │     ) : (                                    │
   │       <SimpleSelect ... />                   │
   │     )}                                       │
   │   </FormField>                               │
   │ ))}                                          │
   └──────────────────────────────────────────────┘
            │
            ▼
3. User Fills Form
   ┌────────────────────────────┐
   │ Entity:   [Main Dept ▼]    │ ─┐
   │ Account:  [Salaries  ▼]    │  │
   │ Project:  [Project A ▼]    │  │ Dynamic fields!
   │ Amount:   [1000]           │  │
   │                            │ ─┘
   │ [Submit]                   │
   └────────────────────────────┘
            │
            ▼
4. Submit Transaction
   POST /api/transfers/
   {
     "transaction_id": 123,
     "segments": {
       "Entity": "12345",
       "Account": "67890",
       "Project": "98765"
     },
     "from_center": 1000,
     "to_center": 500
   }
```

---

## Success Metrics Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│                      IMPLEMENTATION METRICS                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────┬──────────────┬──────────────┐
│ Metric                  │ Before       │ After        │
├─────────────────────────┼──────────────┼──────────────┤
│ Supported Segments      │ 3 (fixed)    │ 2-30 (flex)  │
│ Client Setup Time       │ 3-4 weeks    │ 15 minutes   │
│ Code Changes per Client │ 50+ files    │ 0 (config)   │
│ Database Tables         │ 3 segment    │ 1 generic    │
│ API Endpoints           │ 15 (fixed)   │ 5 (dynamic)  │
│ Frontend Components     │ 10 (custom)  │ 1 (reusable) │
│ Maintenance Effort      │ High         │ Low          │
│ Scalability             │ Poor         │ Excellent    │
└─────────────────────────┴──────────────┴──────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   CLIENT DEPLOYMENT STATUS                   │
└─────────────────────────────────────────────────────────────┘

Client A (2 segments) ████████████████████ 100% ✅
Client B (3 segments) ████████████████████ 100% ✅
Client C (4 segments) ████████████████░░░░  75% 🔄
Client D (5 segments) ████████░░░░░░░░░░░░  40% 🔄

┌─────────────────────────────────────────────────────────────┐
│                       PERFORMANCE                            │
└─────────────────────────────────────────────────────────────┘

Page Load Time:         ▓▓▓░░░░░░░ 1.2s (target: <2s) ✅
API Response Time:      ▓░░░░░░░░░ 180ms (target: <500ms) ✅
Database Query Time:    ▓░░░░░░░░░ 45ms (target: <100ms) ✅
FBDI Generation Time:   ▓▓▓▓░░░░░░ 2.5s (target: <5s) ✅
```

---

## Folder Structure Overview

```
Tnfeez_dynamic/
│
├── __CLIENT_SETUP_DOCS__/              ◄── YOU ARE HERE
│   ├── README.md                       ← Quick reference (this file)
│   ├── 01_DYNAMIC_SEGMENTS_ARCHITECTURE.md
│   ├── 02_IMPLEMENTATION_GUIDE_CODE.md
│   ├── 03_TRANSACTION_API_UPDATES.md
│   ├── 04_ORACLE_INTEGRATION_DEPLOYMENT.md
│   └── 05_VISUAL_DIAGRAMS.md           ← Visual guides
│
├── config/                             ◄── Client configurations
│   ├── segments_config.json            ← Default (3 segments)
│   ├── segments_config_2seg.json       ← 2-segment example
│   └── segments_config_5seg.json       ← 5-segment example
│
├── account_and_entitys/
│   ├── models.py                       ← XX_SegmentType, XX_Segment
│   ├── managers/
│   │   └── segment_manager.py          ← Core business logic
│   ├── management/commands/
│   │   ├── setup_client.py             ← Client setup wizard
│   │   └── migrate_legacy_segments.py  ← Data migration
│   └── utils.py                        ← Balance report parsing
│
├── transaction/
│   ├── models.py                       ← xx_TransactionTransfer
│   ├── serializers.py                  ← Dynamic serializers
│   └── views.py                        ← Transaction APIs
│
├── test_upload_fbdi/
│   ├── journal_template_manager.py     ← Dynamic FBDI generation
│   └── budget_template_manager.py      ← Dynamic budget import
│
└── budget_management/
    ├── models.py                       ← xx_BudgetTransfer
    └── views.py                        ← Dashboard logic

```

---

**Ready to implement?** Start with document 01, follow the implementation guide, and refer back to this visual reference as needed!
