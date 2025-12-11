# Codex Master Specification Prompt for the GRMS Backend

Codex, you are developing the backend for the **Gravel Road Management System (GRMS)**.  
This repository implements a PostGIS-enabled Django + Django REST Framework system for:

- Road & structure inventory  
- Condition surveys (network & detailed)  
- Traffic surveys & ADT/PCU computation  
- MCI calculation  
- ERA maintenance quantity estimation  
- Prioritization  
- BOQ generation  
- Annual work plans  
- QA workflows  

Your job is to **implement the full backend system** using the specifications in:

- `docs/GRMS_SRAD_full_v1.2_NOV_03.docx`
- `docs/comment on GRMS sep 24.docx`

Treat these documents as your **authoritative functional specification**.

You MUST implement the system exactly according to the SRAD.

You are allowed to use your flexibility in:
- architecture  
- helpers  
- refactoring  
- code organization  
but you must **never violate SRAD rules or the data model described within it.**

---

# 1. System Architecture Rules

You MUST use:

### Django 4.2
- As the main backend framework  
- With ORM models for all SRAD tables  

### Django REST Framework
- `ModelViewSet` for CRUD  
- Routers in `grms/urls.py`  
- Pagination, filtering, ordering  

### PostGIS / GeoDjango
- Road geometry: `LineStringField`  
- Structure & furniture coordinates: `PointField`  

### Folder Structure (MANDATORY)

All code must live in the following structure:

```
project/
    settings.py
    urls.py

grms/
    models.py
    serializers.py
    views.py
    urls.py
    admin.py
    admin_config.py
    utils.py
    services/
        mci.py
        traffic.py
        quantity.py
        prioritization.py
        boq.py
    management/
        commands/
            compute_mci.py
            compute_traffic_summary.py
            compute_prioritization.py
            compute_boq.py
    tests/
        test_mci.py
        test_traffic.py
        test_quantity.py
        test_prioritization.py
        test_boq.py
```

You may create new modules within `services/` as needed.

---

# 2. GRMS Data Model Rules (SRAD-Based)

Codex must implement models exactly as defined in the SRAD, including:

### 2.1 Road Hierarchy
- `Road`  
- `RoadSection`  
- `RoadSegment`  

### 2.2 Structure Inventory
- `StructureInventory`  
- Bridge details  
- Culvert details  
- Gabion wall details  
- Retaining wall details  
- Ford details  

### 2.3 Condition Surveys (network & detailed)
- `RoadConditionSurvey`  
- `RoadDetailedSurvey`  
- `StructureConditionSurvey`  
- `StructureDetailedSurvey`  
- `FurnitureConditionSurvey`  

### 2.4 Traffic System
- `TrafficSurvey`  
- `TrafficCountRecord`  
- `TrafficCycleSummary`  
- `TrafficSurveySummary`  
- `PCULookup`  
- `NightAdjustmentLookup`  
- `TrafficQC`  
- `TrafficForPrioritization`  

### 2.5 Prioritization & Planning
- `BenefitFactors`  
- `PrioritizationResult`  
- `InterventionLookup`  
- `UnitCostTable`  
- `InterventionRequirementRoad`  
- `InterventionRequirementStructure`  
- `AnnualWorkPlan`  

### 2.6 BOQ and Quantities
- `QuantityEstimationLine`  
- `BOQLine`  
- `BOQPackage`  

### 2.7 Lookups
You MUST include:
- `QAStatus`  
- `DistressType`  
- `DistressCondition`  
- `ActivityLookup`  
- All enums and choice tables defined in SRAD.  

### 2.8 Field Names and Types
- Field names MUST match SRAD fields exactly.  
- Use decimals for quantities and measurements.  
- Use SRAD-defined units (`m`, `m2`, `m3`, `km`, `item`).  
- Use enums exactly as defined.  

### 2.9 Relationships
- Segment → Section → Road hierarchy must be respected.  
- Surveys reference segments, structures, furniture.  
- Traffic references segment.  
- Prioritization references road/section.  

---

# 3. Business Logic You MUST Implement

## 3.1 MCI Computation

Implement the SRAD-defined MCI formula using:

- severity  
- extent  
- surface condition  
- drainage  
- shoulder condition  
- gravel thickness  
- SRAD-defined weighting tables  

Output:
- Persisted MCI result linked to each survey

Trigger recalculation on:
- survey save  
- distress update  
- QA approval  

Use:
- signals  
- management command  
- or dedicated API trigger  

Only QA-*approved* surveys count.

---

## 3.2 Traffic ADT/PCU Computation

Compute traffic using SRAD logic.

### Cycle-level:
- cycle_sum_count  
- cycle_daily_avg  
- cycle_daily_24hr (night adjustment)  
- cycle_pcu  

### Survey-level:
- ADT per class  
- PCU per class  
- ADT total  
- PCU total  

### Quality scoring:
- missing cycles  
- inconsistent data  
- variation  
- confidence score  

Only QA-approved surveys contribute.

---

## 3.3 ERA Maintenance Quantity Estimation

Pipeline:

```
distress → (severity, extent) → distress_condition → activity lookup
        → quantity_value scaled by scale_basis
```

Scale basis includes:
- per_100m  
- per_segment  
- per_item  
- per_culvert  
- per_m2  
- per_m3  

Override rule:
- measured values override lookup values  
- set `computed_by_lookup=False` on overrides  

Output:
- one or more `QuantityEstimationLine` per distress  

Then aggregated into BOQ.

---

## 3.4 Prioritization Engine

Formula:

```
Score = w1*MCI + w2*TrafficFactor + w3*SocioEconomic
      + w4*Safety + w5*Connectivity
```

You MUST:
- load weights from config or model  
- use only QA-approved values  
- store results in `PrioritizationResult`  
- integrate into Annual Work Plan  

---

## 3.5 BOQ Generation

Steps:

1. Run quantity estimation  
2. Group lines by road, section, segment, activity  
3. Multiply by unit costs  
4. Produce `BOQLine`  
5. Produce `BOQPackage`  
6. Sum totals  

You MUST implement:
- `boq.py` service  
- BOQ viewsets  
- tests  

---

# 4. Admin Behavior

You MUST:
- Make all calculated fields **read-only**  
- Show computed values in admin tables  
- Provide inline editing for:
  - distress tables  
  - traffic cycles  
  - structure and road detail tables  

Admin must:
- prevent editing MCI, ADT/PCU, prioritization scores  
- display geometry fields properly  

---

# 5. Testing Requirements

Tests MUST exist for:

### MCI
- severity/extent combinations  
- full-segment case  
- edge values  

### Traffic
- cycle summaries  
- survey summaries  
- quality scoring  

### Quantity Estimation
- ERA lookup → expected activities  
- scale basis behaviour  
- measured-override behaviour  
- multi-activity outputs  

### Prioritization
- weighted scores  
- ranking correctness  

### BOQ
- quantity aggregation  
- cost aggregation  
- package generation  

Tests MUST go under:
```
grms/tests/
```

---

# 6. Code Generation Rules for Codex

When you generate code, you MUST output all relevant files:

1. Updated or new Django models  
2. Serializers  
3. Viewsets  
4. URL routing  
5. Service classes  
6. Management commands  
7. Admin changes  
8. Unit tests  
9. Migrations if needed  

Your code MUST:
- be runnable  
- use correct imports  
- follow Django conventions  
- follow SRAD rules  
- integrate cleanly with the repo  

---

# 7. Flexibility Allowed

You MAY:
- Add helper utilities  
- Add indexes or constraints  
- Create new service modules  
- Refactor duplicated logic  
- Propose optimizations  
- Improve clarity  

You MUST NOT:
- Rename SRAD-defined fields unless migrating correctly  
- Allow users to edit calculated fields  
- Break QA workflow  
- Change core business logic  

---

# 8. How the Developer Will Use You

After reading this file, Codex will respond to commands like:

- “Implement RoadSegment MCI computation.”  
- “Generate all traffic models & API endpoints.”  
- “Build quantity estimation service with ERA rules.”  
- “Add prioritization engine and tests.”  
- “Generate full BOQ pipeline.”  

Your output MUST be:
- Complete  
- Clean  
- Tested  
- Ready to paste into the repo  

Codex, use this spec for **all future work** in the GRMS backend.
