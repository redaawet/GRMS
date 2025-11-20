# Codex Prompt for Calculated Fields

In this repo, use the documents `docs/GRMS_SRAD_full_v1.2_NOV_03.docx` and `docs/comment on GRMS sep 24.docx` as the functional spec for the Gravel Road Management System.
Some database fields and tables are **calculated**, not manually entered:

* MCI (Maintenance Condition Index) per road segment
* Prioritization score: `Score = w1*MCI + w2*TrafficFactor + w3*SocioEconomicScore + w4*SafetyScore + w5*ConnectivityScore`
* Maintenance quantity estimates from ERA lookup matrices (distress → activity → quantity, with `computed_by_lookup` flags, scale_basis, etc.)
* BOQ aggregation tables (summed quantities per activity/segment/road).

Tasks:

1. Identify all models where these values should live (e.g. road_segment, survey/distress rows, distress_activity, BOQ lines) based on the SRAD.
2. Implement Python functions/services to:
   * compute MCI from distress data,
   * compute the prioritization score using the weights from config,
   * compute maintenance quantities using the ERA lookup tables,
   * aggregate BOQ quantities per road / package.
3. Wire these calculations so they run automatically (e.g. on survey save / via management commands), and **do not let users edit the calculated fields in the Django admin** (read-only fields).
4. Add unit tests using a few example cases from the document (distress → expected quantity, MCI, prioritization score) to verify the calculations.
5. Show me the updated models, services/utils, and tests you created or modified, with brief comments explaining where each calculation is implemented.

You can tweak filenames/paths if your docs are stored somewhere else in the repo. If you want, I can help you write 2–3 concrete test cases (input → expected MCI/BOQ) for Codex to use.
