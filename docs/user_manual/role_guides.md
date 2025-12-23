# Role guides (RBAC)

Use these quick references to understand what each role can view and execute in the grouped AdminSite.

## Admin
- **Can see/do**: All menus; manage users/roles; configure lookups; approve/reject surveys; run management commands (MCI, benefits, traffic summaries); export any report.
- **Cannot do**: Skip QA for unreviewed data when governance requires dual approval; bypass database credentials rotation.
- **Daily workflow**: Check import error logs → nudge data collectors → approve reviewed surveys → run nightly computations → export MCI/Prioritization for leadership.

## Engineer
- **Can see/do**: Road/section/segment inventory, condition surveys, traffic summaries, QA status changes for assigned roads, run compute commands from shell, export Excel/PDF.
- **Cannot do**: Create or edit user accounts/roles; change production env vars; delete approved records without admin sign-off.
- **Daily workflow**: Validate new condition surveys → mark QA status → run `compute_mci <year>` → review Segment MCI results → share prioritized list.

## Data Collector
- **Can see/do**: Create/edit roads, sections, segments (if permitted), add condition surveys, add traffic surveys and count records, run dry-run imports, view their own QA flags.
- **Cannot do**: Approve surveys, run compute commands, change user/role settings, export global reports beyond their scope.
- **Daily workflow**: Enter field data → run dry-run import for the day’s counts → fix any FK/errors → resubmit → wait for engineer/admin QA feedback.

## Viewer
- **Can see/do**: Read-only access to inventory, surveys, QA status, and reports; export filtered Excel/PDF.
- **Cannot do**: Create/edit/delete data; approve QA; run management commands; manage users.
- **Daily workflow**: Filter by road or year → export Excel/PDF snapshots → use for presentations or analytics tools.
