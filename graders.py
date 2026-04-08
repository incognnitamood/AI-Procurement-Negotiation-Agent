"""
Grader functions for evaluating negotiation outcomes.
"""

from environment import SUPPORT_RANK, PAYMENT_RANK
from typing import Dict, Any, List


def grade_price(achieved_price: float, target_price: float, initial_price: float) -> float:
    """
    Grade the achieved price on a scale of 0-1.
    
    Args:
        achieved_price: Final negotiated price
        target_price: Buyer's target price
        initial_price: Vendor's initial price
        
    Returns:
        Grade between 0 and 1, where 1.0 = target met or better
    """
    # If target achieved or better
    if achieved_price <= target_price:
        return 1.0
    
    # If no progress (at or above initial)
    if achieved_price >= initial_price:
        return 0.0
    
    # Interpolate: how much of the savings gap did we achieve?
    savings_range = initial_price - target_price
    if savings_range <= 0:
        return 0.0
    
    achieved_savings = initial_price - achieved_price
    progress = achieved_savings / savings_range
    
    # Clamp to [0, 1]
    return max(0.0, min(1.0, progress))


def grade_support(achieved_tier: str, target_tier: str) -> float:
    """
    Grade achieved support tier against target on a scale of 0-1.
    
    Uses SUPPORT_RANK: standard (1) < business (2) < premium (3)
    
    Args:
        achieved_tier: Achieved support tier ("standard", "business", "premium")
        target_tier: Target support tier
        
    Returns:
        Grade between 0 and 1, where 1.0 = target met or exceeded
    """
    achieved_rank = SUPPORT_RANK.get(achieved_tier, 1)
    target_rank = SUPPORT_RANK.get(target_tier, 1)
    
    # If target met or exceeded
    if achieved_rank >= target_rank:
        return 1.0
    
    # Progress relative to target (from min_rank toward target_rank)
    min_rank = 1
    if target_rank > min_rank:
        progress = (achieved_rank - min_rank) / (target_rank - min_rank)
    else:
        progress = 1.0
    
    return max(0.0, min(1.0, progress))


def grade_payment(achieved_terms: str, target_terms: str) -> float:
    """
    Grade achieved payment terms against target on a scale of 0-1.
    
    Uses PAYMENT_RANK: net-30 (1) < net-45 (2) < net-60 (3) < net-90 (4)
    
    Args:
        achieved_terms: Achieved payment terms (e.g., "net-30")
        target_terms: Target payment terms
        
    Returns:
        Grade between 0 and 1, where 1.0 = target met or exceeded
    """
    achieved_rank = PAYMENT_RANK.get(achieved_terms, 1)
    target_rank = PAYMENT_RANK.get(target_terms, 1)
    
    # If target met or exceeded
    if achieved_rank >= target_rank:
        return 1.0
    
    # Progress relative to target (from min_rank toward target_rank)
    min_rank = 1
    if target_rank > min_rank:
        progress = (achieved_rank - min_rank) / (target_rank - min_rank)
    else:
        progress = 1.0
    
    return max(0.0, min(1.0, progress))


def grade_sla(achieved_sla: float, target_sla: float) -> float:
    """
    Grade achieved SLA against target on a scale of 0-1.
    
    Args:
        achieved_sla: Achieved SLA percentage (e.g., 99.5)
        target_sla: Target SLA percentage
        
    Returns:
        Grade between 0 and 1, where 1.0 = target met or exceeded
    """
    # If target met or exceeded
    if achieved_sla >= target_sla:
        return 1.0
    
    # SLA range is typically 99.0 to 100.0
    min_sla = 99.0
    max_sla = 100.0
    
    # Interpolate: progress from min to max
    max_range = max_sla - min_sla
    if max_range <= 0:
        return 0.0
    
    achieved_gain = achieved_sla - min_sla
    progress = achieved_gain / max_range
    
    return max(0.0, min(1.0, progress))


def grade_bundle_trap(history: List[Dict[str, Any]], scenario: Dict[str, Any]) -> float:
    """
    Grade whether agent correctly used split strategy for enterprise bundle.
    
    For enterprise_bundle scenario with optimal_strategy = "split_crm",
    return 1.0 if agent ever used split_products with "crm" in it, else 0.0.
    
    Args:
        history: Negotiation history
        scenario: Scenario configuration
        
    Returns:
        1.0 if correctly split, 0.0 otherwise (or 1.0 if not applicable)
    """
    optimal_strategy = scenario.get("optimal_strategy")
    
    # Only applies to scenarios with split_crm strategy
    if optimal_strategy != "split_crm":
        return 1.0  # Not applicable, so full credit
    
    # Check if agent used split_products with crm in any buyer move
    for entry in history:
        if entry.get("actor") == "buyer":
            split_products = entry.get("split_products")
            if split_products and "crm" in split_products:
                return 1.0
    
    # Strategy not employed
    return 0.0


def grade_episode(
    final_offer: Dict[str, Any],
    scenario: Dict[str, Any],
    history: List[Dict[str, Any]],
) -> float:
    """
    Compute overall episode grade with weighted scoring.
    
    For standard scenarios (saas_renewal, cloud_infra_deal):
    - Price: 0.4
    - Support: 0.2
    - Payment: 0.2
    - SLA: 0.2
    
    For enterprise_bundle:
    - Bundle trap (split strategy): weighted as 1.0
    
    All outputs are normalized to [0, 1].
    
    Args:
        final_offer: Final negotiated offer
        scenario: Scenario configuration
        history: Negotiation history
        
    Returns:
        Weighted grade between 0 and 1
    """
    # Check if this is enterprise_bundle by optimal_strategy
    if scenario.get("optimal_strategy") == "split_crm":
        # Enterprise bundle: grade primarily on bundle trap strategy
        return grade_bundle_trap(history, scenario)
    
    # Standard scenarios: grade on price, support, payment, sla
    initial_offer = scenario.get("initial_offer", {})
    buyer_targets = scenario.get("buyer_targets", {})
    
    score = 0.0
    
    # ===== PRICE GRADE (weight: 0.4) =====
    if "price" in final_offer and "price" in initial_offer:
        achieved_price = final_offer["price"]
        target_price = buyer_targets.get("price", initial_offer["price"])
        initial_price = initial_offer["price"]
        
        price_grade = grade_price(achieved_price, target_price, initial_price)
        score += 0.4 * price_grade
    else:
        score += 0.4  # Assume full credit if not applicable
    
    # ===== SUPPORT GRADE (weight: 0.2) =====
    if "support_tier" in final_offer:
        achieved_tier = final_offer["support_tier"]
        target_tier = buyer_targets.get("support_tier", "standard")
        
        support_grade = grade_support(achieved_tier, target_tier)
        score += 0.2 * support_grade
    else:
        score += 0.2  # Assume full credit if not applicable
    
    # ===== PAYMENT GRADE (weight: 0.2) =====
    if "payment_terms" in final_offer:
        achieved_terms = final_offer["payment_terms"]
        target_terms = buyer_targets.get("payment_terms", "net-30")
        
        payment_grade = grade_payment(achieved_terms, target_terms)
        score += 0.2 * payment_grade
    else:
        score += 0.2  # Assume full credit if not applicable
    
    # ===== SLA GRADE (weight: 0.2) =====
    if "sla" in final_offer:
        achieved_sla = final_offer["sla"]
        target_sla = buyer_targets.get("sla", 99.0)
        
        sla_grade = grade_sla(achieved_sla, target_sla)
        score += 0.2 * sla_grade
    else:
        score += 0.2  # Assume full credit if not applicable
    
    # Clamp final score to [0, 1]
    return max(0.0, min(1.0, score))
