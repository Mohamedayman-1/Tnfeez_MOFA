# Segment Upload - Quick Reference Card

## 🚀 New Unified Upload Endpoint

```bash
POST /api/accounts-entities/segments/upload/?segment_type={id|name}
```

### Works with ANY segment type dynamically! 🎉

---

## 📋 Excel File Format

| Column # | Name | Required | Description | Example |
|----------|------|----------|-------------|---------|
| 1 | Code | ✅ Yes | Segment code | `11000`, `PRJ-2025` |
| 2 | ParentCode | ❌ Optional | Parent for hierarchy | `11000`, `PRJ-2025` |
| 3 | Alias | ❌ Optional | Display name | `Finance Division` |
| 4 | EnvelopeAmount | ❌ Optional | Budget limit | `1000000.00` |

**Template:**
```excel
Code       | ParentCode | Alias              | EnvelopeAmount
11000      |            | Finance Division   | 5000000.00
11100      | 11000      | Accounting Dept    | 1000000.00
```

---

## 🎯 Quick Examples

### Upload Entities
```bash
curl -X POST \
  -H "Authorization: Bearer {token}" \
  -F "file=@entities.xlsx" \
  "https://api.example.com/api/accounts-entities/segments/upload/?segment_type=Entity"
```

### Upload Accounts (by ID)
```bash
curl -X POST \
  -H "Authorization: Bearer {token}" \
  -F "file=@accounts.xlsx" \
  "https://api.example.com/api/accounts-entities/segments/upload/?segment_type=2"
```

### Upload Projects
```bash
curl -X POST \
  -H "Authorization: Bearer {token}" \
  -F "file=@projects.xlsx" \
  "https://api.example.com/api/accounts-entities/segments/upload/?segment_type=Project"
```

---

## ✨ Key Features

| Feature | Status | Description |
|---------|--------|-------------|
| **Dynamic** | ✅ | Works with unlimited segment types |
| **Auto-Level** | ✅ | Calculates hierarchy levels automatically |
| **Envelope** | ✅ | Optional budget/envelope amounts |
| **Upsert** | ✅ | Creates new or updates existing |
| **Validation** | ✅ | Parent existence, numeric envelopes |
| **Legacy Compatible** | ✅ | Old endpoints still work |

---

## 📊 Response Format

### Success
```json
{
  "status": "ok",
  "message": "Processed 5 Entity segments successfully.",
  "summary": {
    "created": 3,
    "updated": 2,
    "skipped": 0,
    "errors": [],
    "segment_type": "Entity",
    "segment_type_id": 1
  }
}
```

### With Errors
```json
{
  "status": "ok",
  "message": "Processed 4 Entity segments successfully.",
  "summary": {
    "created": 4,
    "updated": 0,
    "skipped": 1,
    "errors": [
      {
        "code": "11110",
        "error": "Parent code '11100' not found. Process parent rows first."
      }
    ],
    "segment_type": "Entity",
    "segment_type_id": 1
  }
}
```

---

## 🔧 Level Calculation (Automatic!)

| Scenario | Level | Calculation |
|----------|-------|-------------|
| No parent | 0 | Root segment |
| Parent at level 0 | 1 | parent.level + 1 |
| Parent at level 1 | 2 | parent.level + 1 |
| Parent at level N | N+1 | parent.level + 1 |

**Example:**
```excel
Code   | ParentCode | → Level (Auto)
11000  |            | → 0 (root)
11100  | 11000      | → 1 (child)
11110  | 11100      | → 2 (grandchild)
```

---

## ⚠️ Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| "Parent not found" | Child before parent | Upload parents first |
| "Invalid envelope" | Non-numeric value | Use decimal: `1000000.00` |
| "segment_type required" | Missing parameter | Add `?segment_type=X` |
| "segment_type not found" | Wrong ID/name | Check `/segment-types/` |
| All rows skipped | Wrong format | Check Excel structure |

---

## 🎓 Best Practices

### ✅ DO
- Include header row (auto-skipped)
- Upload parents before children
- Use consistent code format
- Test with small file first
- Include envelope amounts for projects

### ❌ DON'T
- Skip parent segments
- Use spaces in codes
- Mix currencies in envelope amounts
- Upload unsorted hierarchy
- Forget segment_type parameter

---

## 📚 Documentation Links

- **Full Guide:** `SEGMENT_BULK_UPLOAD_GUIDE.md`
- **API Reference:** `DYNAMIC_SEGMENT_API_GUIDE.md`
- **Implementation:** `SEGMENT_UPLOAD_SUMMARY.md`
- **Complete CRUD:** `COMPLETE_CRUD_API_SUMMARY.md`

---

## 🔄 Migration Path

### Old Way (Still Works)
```bash
POST /api/accounts-entities/projects/upload/
POST /api/accounts-entities/accounts/upload/
POST /api/accounts-entities/entities/upload/
```

### New Way (Recommended)
```bash
POST /api/accounts-entities/segments/upload/?segment_type=Project
POST /api/accounts-entities/segments/upload/?segment_type=Account
POST /api/accounts-entities/segments/upload/?segment_type=Entity
```

### Future (Custom Segments)
```bash
POST /api/accounts-entities/segments/upload/?segment_type=Department
POST /api/accounts-entities/segments/upload/?segment_type=Location
# Works with ANY segment type!
```

---

## 🎉 Summary

**One endpoint for ALL segment types:**
- ✅ Entities (Cost Centers)
- ✅ Accounts
- ✅ Projects
- ✅ **ANY future segment type!**

**Features:**
- ✅ Auto-calculates levels
- ✅ Supports envelopes
- ✅ Validates parents
- ✅ Upserts safely
- ✅ Fully dynamic

**Query Parameters:**
- `segment_type` (required): ID or name

**Excel Columns:**
1. Code (required)
2. ParentCode (optional)
3. Alias (optional)
4. EnvelopeAmount (optional)

**Try it now!** 🚀

---

**Last Updated:** November 6, 2025  
**Version:** 1.0  
**Status:** ✅ Ready to Use
