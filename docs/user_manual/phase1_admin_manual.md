# Phase 1 Admin Manual (Grouped AdminSite)

This manual walks through day-to-day tasks in the custom AdminSite with grouped index tiles.
Use the navigation paths shown in each step (e.g., **Admin Dashboard → Inventory → Roads**) and capture screenshots at the indicated steps for your deployment wiki.

## 1. Log in
1. Browse to the admin root (e.g., `https://<host>/admin/`).
2. Enter your username/password (from your onboarding email) and click **Log in**.
3. You will land on the **Grouped Admin Dashboard** where menu cards are organized by Inventory, Surveys, QA/Approvals, and Reports. *(Screenshot: Grouped dashboard after login.)*

## 2. Menus at a glance
- **Inventory**: Roads, Sections, Segments, reference lookups (Zones, Woredas).
- **Surveys**: Road Condition Surveys, Traffic Surveys, Traffic Count Records.
- **QA / Approvals**: QA status changes for condition and traffic surveys.
- **Reports & Exports**: MCI/Prioritization outputs, traffic summaries, and Excel/PDF exports.
- **Admin**: Users, groups/roles, permissions, and configuration tables.

## 3. Road inventory entry (Road → Section → Segment)
1. **Create a Road**: Admin Dashboard → **Inventory → Roads → Add**.
   - Required: `Road ID (RTR-###)`, `From`, `To`, `Design Standard`, `Surface Type`, `Managing Authority`, `Total Length (km)`, `Admin Zone`.
   - Optional: geometry via start/end coordinates or uploaded geometry. Save to activate Section creation. *(Screenshot: Road add form.)*
2. **Add Sections**: Admin Dashboard → **Inventory → Road sections → Add**.
   - Choose the road; enter `Start chainage (km)`, `End chainage (km)`, `Surface type`, optional `Section name`. Geometry slices automatically if the road geometry is present.
   - Validation enforces no gaps/overlaps across sections. *(Screenshot: Section form showing chainage fields.)*
3. **Add Segments**: Admin Dashboard → **Inventory → Road segments → Add**.
   - Pick a section; set `Station from/to (km)`, `Cross section`, `Terrain (transverse/longitudinal)`, drainage/shoulder presence, `Carriageway width`.
   - Segment identifiers auto-generate and chainage must stay within the parent section. *(Screenshot: Segment form.)*

## 4. Condition survey entry/import
- **Manual entry**: Admin Dashboard → **Surveys → Road condition surveys → Add**.
  1. Select the `Road segment`.
  2. Record drainage/shoulder condition lookups, `Surface condition`, `Gravel thickness`, `Bottleneck` flag/size, `Inspection date`, `Inspector`.
  3. Save to create or update the record. *(Screenshot: Condition survey form.)*
- **Bulk import**:
  1. Navigate to **Surveys → Road condition surveys** list.
  2. Use the import action that matches your deployment (see `import_templates.md` for columns and dry-run steps).
  3. Run a **Dry-run** first to validate rows; download the error log, fix, and re-import with the same file once errors are resolved.

## 5. Traffic survey entry/import
- **Create a Traffic Survey header**: Admin Dashboard → **Surveys → Traffic surveys → Add**.
  1. Pick the `Road`, set `Survey year`, `Cycle number`, `Count start/end date`, `Count hours per day`, and `Method/Observer`.
  2. Provide the station location (lat/lng) using the map widget.
- **Add daily count records**: After saving, use the inline **Traffic count records** to add rows per day (cars, light goods, minibuses, etc.). *(Screenshot: Traffic count inline form.)*
- **Bulk import**:
  1. Go to **Surveys → Traffic count records** list or the survey detail action.
  2. Upload the traffic count Excel template (see `import_templates.md`).
  3. Run **Dry-run** to check FK references to `traffic_survey` and road, then re-import after fixing the error log.

## 6. Approvals and QA
1. Open **QA / Approvals → Traffic surveys** or **QA / Approvals → Road condition surveys**.
2. Filter by `QA status` (Draft, In Review, Approved).
3. Select one or many rows → choose **Mark as Approved** (or the equivalent action) → confirm.
4. QA actions trigger automated QC checks (hour mismatches, missing days) and update timestamps. *(Screenshot: QA action dropdown.)*

## 7. Running MCI and prioritization
1. Ensure condition surveys are entered and approved for the target fiscal year.
2. From the server shell (repo root):
   - `python manage.py compute_mci <fiscal_year>` to calculate MCI per segment.
   - `python manage.py compute_benefits <fiscal_year>` then `python manage.py compute_prioritization` to refresh prioritization results.
3. Refresh the Admin dashboard (**Reports & Exports**) to view updated MCI/benefit tables.

## 8. Generating reports
- **MCI/Prioritization tables**: Admin Dashboard → **Reports & Exports → Segment MCI results** or **Prioritization results**. Use filters (year, road) then **Export**.
- **Traffic summaries**: Admin Dashboard → **Reports & Exports → Traffic survey summaries/overall**. Filter by fiscal year or road.
- **Excel/PDF**: Use the list actions to export the current queryset. When exporting PDF, ensure wkhtmltopdf (or your configured renderer) is installed on the host. *(Screenshot: changelist action menu.)*

## 9. Exporting Excel/PDF
1. Apply filters on the changelist (e.g., Road sections for one road).
2. Select rows (or leave empty to export all filtered rows).
3. Choose **Export to Excel** or **Export to PDF** from the action dropdown and confirm.
4. The file downloads with the applied filters; share it with stakeholders or attach to approval memos. *(Screenshot: export action confirmation.)*

## 10. Example daily flows
- **Admin**: Review imports → Approve QA queues → Export weekly Excel for stakeholders.
- **Engineer**: Validate new condition surveys → Run `compute_mci` → Download MCI/Prioritization PDF → Share with planning.
- **Data Collector**: Enter or import traffic/condition surveys → check dry-run logs → resubmit until QA passes.
- **Viewer**: Log in → Browse readonly reports → Export filtered Excel for analysis.
