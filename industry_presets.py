# industry_presets.py

PRESETS = {

    "construction": {
        "drivers": [
            "labour_hours",
            "material_cost",
            "equipment_cost",
            "transport_cost"
        ],
        "description": "General construction / building jobs"
    },

    "electrical": {
        "drivers": [
            "labour_hours",
            "cable_length",
            "components_cost",
            "compliance_cost"
        ],
        "description": "Electrical installs and energy systems"
    },

    "painting": {
        "drivers": [
            "surface_area",
            "paint_cost",
            "labour_hours",
            "scaffolding_cost"
        ],
        "description": "Residential or commercial painting"
    }

}