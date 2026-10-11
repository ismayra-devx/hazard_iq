// ==============================================================================
// HazardIQ Cedar Policy Specification (Version 2.0 - API Contract Alignment)
// ==============================================================================
// Evaluates commuter route safety verdicts (ALLOW_ROUTE / DENY_ROUTE).
// Principals: Commuter context (vehicle_type: "two_wheeler", "car", "pedestrian")
// Actions: Action::"NavigateSegment"
// Resources: RoadSegment
// Context: hazard_mode, water_depth_inches, shade_coverage_percent
// ==============================================================================

// Policy 1: DENY two-wheeler transit when water depth exceeds safe clearance (6 inches)
forbid (
    principal,
    action == Action::"NavigateSegment",
    resource
)
when {
    context.hazard_mode == "monsoon" &&
    principal.vehicle_type == "two_wheeler" &&
    context.water_depth_inches > 6
};

// Policy 2: DENY pedestrian crossing when water depth exceeds safe threshold (3 inches)
forbid (
    principal,
    action == Action::"NavigateSegment",
    resource
)
when {
    context.hazard_mode == "monsoon" &&
    principal.vehicle_type == "pedestrian" &&
    context.water_depth_inches > 3
};

// Policy 3: DENY car transit when water depth exceeds sedan clearance (10 inches)
forbid (
    principal,
    action == Action::"NavigateSegment",
    resource
)
when {
    context.hazard_mode == "monsoon" &&
    principal.vehicle_type == "car" &&
    context.water_depth_inches > 10
};

// Policy 4: DENY two-wheeler or pedestrian transit under extreme unshaded heat (< 25% canopy)
forbid (
    principal,
    action == Action::"NavigateSegment",
    resource
)
when {
    context.hazard_mode == "heatwave" &&
    (principal.vehicle_type == "two_wheeler" || principal.vehicle_type == "pedestrian") &&
    context.shade_coverage_percent < 25
};

// Policy 5: ALLOW route when conditions are within verified safety tolerances
permit (
    principal,
    action == Action::"NavigateSegment",
    resource
)
when {
    (context.hazard_mode == "monsoon" && context.water_depth_inches <= 6) ||
    (context.hazard_mode == "heatwave" && context.shade_coverage_percent >= 25)
};
