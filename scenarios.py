"""
Procurement negotiation scenarios configuration.
"""

SCENARIOS = {
    "saas_renewal": {
        "initial_offer": {
            "price": 120000,
            "payment_terms": "net-30",
            "sla": 99.5,
            "support_tier": "standard",
        },
        "vendor_limits": {
            "min_price": 100000,
            "walkaway_rounds": 8,
            "persona": "balanced",
        },
        "buyer_targets": {
            "price": 108000,
            "payment_terms": "net-60",
            "sla": 99.9,
            "support_tier": "standard",
        },
        "max_steps": 15,
    },

    "cloud_infra_deal": {
        "initial_offer": {
            "price": 280000,
            "payment_terms": "net-45",
            "sla": 99.9,
            "support_tier": "standard",
        },
        "vendor_limits": {
            "min_price": 250000,
            "walkaway_rounds": 6,
            "persona": "firm",
        },
        "buyer_targets": {
            "price": 260000,
            "payment_terms": "net-60",
            "sla": 99.99,
            "support_tier": "premium",
        },
        "max_steps": 20,
    },

    "enterprise_bundle": {
        "initial_offer": {
            "products": {
                "crm": {"price": 150000},
                "dataplatform": {"price": 180000},
                "security": {"price": 95000},
            },
            "bundle_discount": 0.15,
        },
        "vendor_limits": {
            "products": {
                "crm": {"min_price": 130000},
                "dataplatform": {"min_price": 155000},
                "security": {"min_price": 80000},
            },
            "walkaway_rounds": 5,
            "persona": "aggressive",
        },
        "buyer_targets": {
            "strategy": "split_crm",
        },
        "max_steps": 25,
    },
}