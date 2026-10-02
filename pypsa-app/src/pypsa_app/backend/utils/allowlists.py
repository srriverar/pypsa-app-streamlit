ALLOWED_STATISTICS: frozenset[str] = frozenset(
    {
        "capacity_factor",
        "capex",
        "curtailment",
        "energy_balance",
        "expanded_capacity",
        "expanded_capex",
        "fom",
        "installed_capacity",
        "installed_capex",
        "market_value",
        "opex",
        "optimal_capacity",
        "overnight_cost",
        "prices",
        "revenue",
        "supply",
        "system_cost",
        "transmission",
        "withdrawal",
    }
)

ALLOWED_CHART_TYPES: frozenset[str] = frozenset(
    {
        "area",
        "bar",
        "box",
        "histogram",
        "line",
        "map",
        "scatter",
        "violin",
    }
)
