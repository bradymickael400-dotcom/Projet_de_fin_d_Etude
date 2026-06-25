# Backend Implementation Summary - ARGOS Maritime Platform

## 📋 Overview
Complete backend API implementation to support frontend profile management, multi-container support for drivers, subscription extensions, and image access restrictions.

## 🔄 Database Schema Changes

### New Columns Added

#### `client` table
- `created_by TEXT` - Stores the user ID of who created the client (for image visibility restrictions)

#### `transporteur` table  
- `id_boites TEXT DEFAULT '[]'` - Stores JSON array of multiple boîtes (containers) for multi-container driver support

#### `agence_utilisatrice` table
- `created_by TEXT DEFAULT 'system'` - Tracks company creator

## 🛣️ API Routes Implemented

### 1. POST `/api/client/update`
**Purpose**: Update client profile information and manage multiple container associations

**Request Payload**:
```json
{
  "id_cni": "CLIENT_ID",
  "nom": "Dupont",
  "prenom": "Jean", 
  "email": "jean@example.com",
  "phone": "+33612345678",
  "boites": ["BOITE_1", "BOITE_2"],
  "type_a": "Mensuel"
}
```

**Response**: `{"status": "success"}` or `{"error": "..."}`

**Features**:
- Partial updates (only provided fields are modified)
- Multi-boîte support (replaces existing subscriptions)
- Error handling for non-existent clients

---

### 2. POST `/api/driver/update`
**Purpose**: Update driver profile information

**Request Payload**:
```json
{
  "id_cni": "DRIVER_ID",
  "nom": "Chauffeur Name",
  "login": "driver_login",
  "contact": "+33612345678",
  "moyen_transport": "Camion"
}
```

**Response**: `{"status": "success"}` or `{"error": "..."}`

---

### 3. POST `/api/company/update`
**Purpose**: Update company/agency profile

**Request Payload**:
```json
{
  "id": 1,
  "nom_agence": "New Company Name",
  "niu": "NEW_NIU",
  "email": "company@example.com",
  "lieu_residence": "Port de Casablanca"
}
```

**Response**: `{"status": "success"}` or `{"error": "..."}`

---

### 4. POST `/api/client/extend`
**Purpose**: Extend client subscription by specified number of days

**Request Payload**:
```json
{
  "id_cni": "CLIENT_ID",
  "days": 30,
  "amount": 500
}
```

**Response**: 
```json
{
  "status": "success",
  "new_end_date": "2025-02-15T10:30:00"
}
```

**Features**:
- Extends subscription end date
- Stores amount for billing purposes
- Creates `abonner.fin_a` column if not exists

---

### 5. POST `/api/client/add_containers`
**Purpose**: Add new containers to client's subscription

**Request Payload**:
```json
{
  "id_cni": "CLIENT_ID",
  "count": 3,
  "type": "DRY"
}
```

**Response**:
```json
{
  "status": "success",
  "containers_added": ["BOITE_1_C1_1705421234", "BOITE_1_C2_1705421234", ...]
}
```

**Features**:
- Generates unique container IDs with timestamp
- Links to client's active subscription
- Returns list of created container IDs

---

### 6. POST `/api/driver/manage` (ENHANCED)
**Purpose**: Manage driver assignments and blocking status - now with multi-container support

**Request Payload (Single Boîte)**:
```json
{
  "id_cni": "DRIVER_ID",
  "id_boite": "SINGLE_BOITE_ID",
  "blocked": false
}
```

**Request Payload (Multiple Boîtes)**:
```json
{
  "id_cni": "DRIVER_ID",
  "id_boites": ["BOITE_1", "BOITE_2", "BOITE_3"],
  "blocked": false
}
```

**Response**: `{"status": "success"}` or `{"error": "..."}`

**Features**:
- Backward compatible with single `id_boite` parameter
- Supports new `id_boites` array for multi-container assignment
- Stores array as JSON string in database
- Updates only one at a time (single or array, not both)

---

## 🔐 Security & Access Control

### Image Visibility Restrictions (`created_by`)
- Images can only be viewed by:
  1. The user who created the client (`created_by` match)
  2. Superadmin users (role = 'superadmin')
- Other users see: "Document visible uniquement par le créateur"

### Implementation
- Frontend checks: `c.created_by === currentUserId || role === 'superadmin'`
- Backend enforces in `register_user_file()` and `register_user()`
- Default: `created_by = "system"` for backward compatibility

---

## 📦 Schema Enhancement Functions

All functions use `IF NOT EXISTS` pattern for safe upgrades:

```python
def _ensure_client_created_by()         # Adds created_by to client
def _ensure_transporteur_schema()       # Adds id_boites to transporteur  
def _ensure_company_schema()            # Adds created_by to agence_utilisatrice
```

---

## 🔗 Frontend Integration

All frontend functions already implemented in `script.js`:

| Route | Frontend Function | Modal |
|-------|-------------------|-------|
| `/api/client/update` | `submitEditClient()` | `openEditClientModal()` |
| `/api/driver/update` | `submitEditDriver()` | `openEditDriverModal()` |
| `/api/company/update` | `submitEditCompany()` | `openEditCompanyModal()` |
| `/api/client/extend` | `submitExtendSubscription()` | `openExtendSubscriptionModal()` |
| `/api/client/add_containers` | `submitAddContainers()` | `openIncreaseContainersModal()` |
| `/api/driver/manage` | `updateDriverAssignment()` | `openDriverManageModal()` |

---

## ✅ Implementation Checklist

- [x] Database schema enhancements (created_by, id_boites)
- [x] Schema upgrade functions with IF NOT EXISTS
- [x] 5 new API routes for profile updates
- [x] Enhanced driver/manage for multi-container support
- [x] Image permission enforcement (created_by checks)
- [x] Error handling with try/catch/rollback pattern
- [x] JSON import for multi-boîtes storage
- [x] Datetime handling for subscription extension
- [x] Frontend integration ready (calls already in place)
- [x] Backward compatibility maintained

---

## 🚀 Testing Recommendations

1. **Test Create Client**
   - Register client with `created_by` set
   - Verify image visibility only for creator

2. **Test Multi-Container Driver**
   - Assign multiple boîtes to driver
   - Verify `id_boites` stored as JSON array

3. **Test Profile Updates**
   - Update each profile type with partial data
   - Verify only specified fields are modified

4. **Test Subscription Extension**
   - Extend subscription by days
   - Verify `fin_a` date calculated correctly

5. **Test Container Addition**
   - Add containers to client
   - Verify container IDs generated with timestamp

---

## 📝 Usage Example

### Creating a Multi-Container Driver
```javascript
// Frontend
await fetch('/api/driver/manage', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    id_cni: 'D123456',
    id_boites: ['BOITE_PORT1', 'BOITE_PORT2', 'BOITE_PORT3'],
    blocked: false
  })
});
```

### Updating Client & Adding Boîtes
```javascript
// Frontend
await fetch('/api/client/update', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    id_cni: 'C987654',
    nom: 'Nouvelle Entreprise',
    boites: ['BOITE1', 'BOITE2'],
    type_a: 'Trimestriel'
  })
});
```

---

## 🔄 Migration Notes

For existing data:
- `created_by` defaults to NULL (handled by UI logic)
- `id_boites` defaults to '[]' (empty array)
- Existing single `id_boite` assignments remain valid
- No data loss on upgrade

---

**Status**: ✅ Complete & Ready for Testing
**Last Updated**: 2024-12-19
