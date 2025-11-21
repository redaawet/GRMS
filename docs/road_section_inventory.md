# Road Section Inventory (Final – GRMS/ERA Aligned)

This document captures the corrected, inventory-only requirements for the Road Section entity. It excludes survey data and manual geometry entry so the form can be adopted directly in SRAD/UI and database design.

## 1. Parent Road (Inherited)
Read-only values pulled from the parent road record:
- Parent Road Name
- Road ID
- Administrative Zone
- Administrative Woreda
- Managing Authority
- Design Standard Category

## 2. Section Identification
- **Section Number** – Unique identifier within the road (e.g., 02, 03, 04…).
- **Section Sequence on Road** – Ordered position of the section along the parent road.
- **Section Name (optional)** – e.g., “Hill Crest Section”.

## 3. Chainage and Length (Mandatory)
- **Start Chainage (km)** – e.g., 12.000
- **End Chainage (km)** – e.g., 17.800
- **Length (km)** – Auto-computed by the system as *End − Start*.
- Chainages must fall within the parent road length and cannot overlap existing sections on the same road.

## 4. Physical Characteristics (Inventory Only)
- **Surface Type** – Gravel / Earth / DBST / Asphalt / Sealed.
- **Wearing Course / Gravel Thickness (cm)** – Required for **Gravel** and **paved** surfaces (DBST/Asphalt/Sealed); optional for Earth.

## 5. Administrative Context (Optional Overrides)
Use only when the section crosses into a new boundary; otherwise inherit from the parent road.
- Section Administrative Zone (optional)
- Section Administrative Woreda (optional)

## 6. Map Preview (Auto Generated)
- Derived from parent road geometry and the start/end chainages; no manual geometry entry.
- Shows the highlighted section, admin boundaries (zone/woreda), towns/landmarks, and optional base layers (satellite/terrain).
- Tools: zoom to section, pan, toggle layers, and chainage markers.

## 7. Notes (Optional)
Free-text inventory notes, e.g., “Steep gradient area” or “Seasonal flooding at km 14+300”.

## Checklist
Included: parent inheritance, section number & sequence, start/end chainage, section length (auto), surface type, thickness for gravel/paved, admin overrides, generated map preview, notes.

Removed: carriageway width (segment-level), geometry input fields, attachments, inspection/survey/MCI/priority fields.
