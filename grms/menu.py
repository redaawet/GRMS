MENU_GROUPS = {
    # Core road geometry and socio-economic data
    "Core_Road_Inventory": [
        ("Road", "Roads"),
        ("RoadSection", "Road sections"),
        ("RoadSegment", "Road segments"),
        ("RoadSocioEconomic", "Road socio-economic"),
    ],

    # Structure inventory and detailed records
    "Structure_Inventory": [
        ("StructureInventory", "Structure inventories"),
        ("BridgeDetail", "Bridge details"),
        ("CulvertDetail", "Culvert details"),
        ("FordDetail", "Ford details"),
        ("RetainingWallDetail", "Retaining wall details"),
        ("GabionWallDetail", "Gabion wall details"),
        ("FurnitureInventory", "Furniture inventories"),
    ],

    # Basic condition survey headers
    "Condition_Surveys": [
        ("StructureConditionSurvey", "Structure condition surveys"),
        ("BridgeConditionSurvey", "Bridge condition surveys"),
        ("CulvertConditionSurvey", "Culvert condition surveys"),
        ("OtherStructureConditionSurvey", "Other structure condition surveys"),
        ("RoadConditionSurvey", "Road condition surveys"),
        ("FurnitureConditionSurvey", "Furniture condition surveys"),
    ],

    # Detailed distress surveys (road, structure, furniture)
    "Detailed_Distress_Surveys": [
        ("RoadConditionDetailedSurvey", "Road detailed surveys"),
        ("StructureConditionDetailedSurvey", "Structured detailed surveys"),
        ("FurnitureConditionDetailedSurvey", "Furniture detailed surveys"),
    ],

    # Traffic & Transport data collection and lookup
    "Traffic_Transport": [
        ("TrafficSurvey", "Traffic surveys"),
        ("TrafficCountRecord", "Traffic counts"),
        ("NightAdjustmentLookup", "Night adjustment lookups"),
        ("PcuLookup", "PCU lookups"),
        ("TrafficQC", "Traffic QC issues"),
        ("TrafficCycleSummary", "Traffic cycle summaries"),
        ("TrafficSurveySummary", "Traffic survey summaries"),
        ("TrafficForPrioritization", "Traffic for prioritization"),
        ("TrafficSurveyOverall", "Traffic survey overall summaries"),
    ],

    # Maintenance & Planning (interventions and work plans)
    "Maintenance_Planning": [
        ("StructureIntervention", "Structure interventions"),
        ("RoadSectionIntervention", "Road section interventions"),
        ("BenefitFactor", "Benefit factors"),
        ("PrioritizationResult", "Prioritization results"),
        ("AnnualWorkPlan", "Annual work plans"),
    ],

    # Reference & Lookups with multiple sub-groups
    "Reference_Lookups": {
        "Asset Classification": [
            ("ActivityLookup", "Activity lookups"),
            ("InterventionLookup", "Intervention lookups"),
            ("UnitCost", "Unit costs"),
        ],
        "Condition & Survey": [
            ("ConditionRating", "Condition ratings"),
            ("QAStatus", "QA statuses"),
        ],
        "Distress Classification": [
            ("DistressType", "Distress types"),
            ("DistressCondition", "Distress conditions"),
            ("DistressActivity", "Distress activities"),
        ],
        "Admin & Connectivity": [
            ("RoadLinkTypeLookup", "Road link types"),
            ("AdminZone", "Administrative zones"),
            ("AdminWoreda", "Administrative woredas"),
        ],
    },

    # Prioritization and benefit evaluation
    "Prioritization_Benefit_Model": [
        ("BenefitCategory", "Benefit categories"),
        ("BenefitCriterion", "Benefit criteria"),
        ("BenefitCriterionScale", "Benefit criterion scales"),
        ("RoadSocioEconomic", "Road socio-economic"),
    ],

    # System administration
    "System_Administration": [
        ("User", "Users"),
        ("Group", "Groups"),
    ],
}
