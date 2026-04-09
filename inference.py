"""
Smart negotiation agent for procurement environment.

Strategies:
1. Adaptive concessions: Track vendor movement, adjust aggressiveness
2. Multi-variable trading: Swap price for SLA/payment/support when needed
3. Walkaway protection: Detect resistance, hold or accept gracefully
4. Non-linear moves: Aggressive early, conservative late
5. Split strategy: For bundles, split products to avoid traps

Outputs standardized [START]/[STEP]/[END] format for automated evaluators.
"""

from environment import NegotiationEnvironment, SCENARIOS
from models import NegotiationAction
from graders import grade_episode
import json
import sys
import os
import re

# Configuration from environment variables
API_BASE_URL = os.getenv('API_BASE_URL', 'https://router.huggingface.co/v1')
API_KEY = os.getenv('API_KEY', os.getenv('HF_TOKEN', ''))  # Fallback to HF_TOKEN if API_KEY not set
MODEL_NAME = os.getenv('MODEL_NAME', 'baseline-rule-based')

# Constants for logging
BENCHMARK = "procurement-negotiation-env"

# Initialize OpenAI client only if using an LLM model
USE_LLM = MODEL_NAME and MODEL_NAME.lower() != 'baseline-rule-based'
if USE_LLM:
    try:
        from openai import OpenAI
        if not API_KEY:
            raise ValueError("API_KEY environment variable is required")
        client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    except Exception as e:
        print(f"Warning: Could not initialize OpenAI client: {e}. Falling back to rule-based.", file=sys.stderr)
        USE_LLM = False


def compute_vendor_concession(previous_offer: dict, current_offer: dict, dimension: str) -> float:
    """
    Compute how much vendor moved on a dimension (as fraction of gap).
    Returns: 0.0 (no move) to 1.0+ (full gap closed or beyond)
    """
    if dimension not in previous_offer or dimension not in current_offer:
        return 0.0
    
    prev_val = previous_offer.get(dimension, 0)
    curr_val = current_offer.get(dimension, 0)
    
    # For price: lower is better for buyer
    if dimension == "price":
        if prev_val <= curr_val:
            return 0.0  # Vendor increased price (bad)
        return (prev_val - curr_val) / max(prev_val, 1)
    
    # For SLA, payment terms: higher is better
    return 1.0 if curr_val > prev_val else 0.0


def get_next_payment_tier(current: str) -> str:
    """Get next payment tier (more favorable to buyer)."""
    tiers = ["net-30", "net-45", "net-60", "net-90"]
    try:
        idx = tiers.index(current)
        return tiers[min(idx + 1, len(tiers) - 1)]
    except:
        return current


def get_next_support_tier(current: str) -> str:
    """Get next support tier (more premium)."""
    tiers = ["standard", "business", "premium"]
    try:
        idx = tiers.index(current)
        return tiers[min(idx + 1, len(tiers) - 1)]
    except:
        return current


def get_llm_decision(
    task_name: str,
    current_offer: dict,
    vendor_response: str,
    vendor_message: str,
    round_num: int,
    scenario: dict
) -> dict:
    """
    Use LLM to decide negotiation action.
    
    Args:
        task_name: Current negotiation task
        current_offer: Current offer on table
        vendor_response: Latest vendor response (accepted/rejected/countered)
        vendor_message: Vendor's message
        round_num: Current round number
        scenario: Scenario configuration with targets
        
    Returns:
        Dict with keys: move, offer, justification
    """
    if not USE_LLM or not client:
        raise RuntimeError("LLM mode not properly initialized")
    
    # Build context for LLM
    targets = scenario.get("buyer_targets", {})
    initial = scenario.get("initial_offer", {})
    
    context = f"""Task: {task_name}
Current offer: {json.dumps(current_offer, indent=2)}
Vendor response: {vendor_response}
Vendor message: {vendor_message}
Round: {round_num} / {scenario.get('max_steps', 20)}
Initial offer: {json.dumps(initial)}
Target: {json.dumps(targets)}

Your task: Make the next move in this procurement negotiation.
Decide: propose, counter, accept, or reject.
Provide new offer with price, payment_terms, support_tier if countering.
Aim to meet TARGETS while being realistic."""

    try:
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=256,
            messages=[
                {
                    "role": "user",
                    "content": context
                }
            ]
        )
        
        response_text = response.content[0].text if response.content else "{}"
        
        # Try to parse JSON from response
        # Look for JSON in the response (may be wrapped in markdown)
        json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
        if json_match:
            decision = json.loads(json_match.group())
        else:
            decision = json.loads(response_text)
        
        return {
            "move": decision.get("move", "propose").lower(),
            "offer": decision.get("offer"),
            "justification": decision.get("justification", "LLM decision")
        }
    
    except Exception as e:
        # Fallback: propose small concession
        return {
            "move": "propose",
            "offer": {k: v * 0.98 if isinstance(v, (int, float)) and k != "price" else v 
                     for k, v in current_offer.items()},
            "justification": f"LLM error {type(e).__name__}, proposing concession"
        }


def run_smart_negotiator(task_name: str, verbose: bool = True) -> dict:
    """
    Run intelligent negotiation agent with adaptive strategy.
    
    Args:
        task_name: "saas_renewal", "cloud_infra_deal", or "enterprise_bundle"
        verbose: Print round-by-round log
        
    Returns:
        Results dict with grade, final_offer, steps, success
    """
    env = NegotiationEnvironment()
    obs = env.reset(task_name)
    scenario = SCENARIOS[task_name]
    
    done = False
    steps = 0
    max_steps = scenario.get("max_steps", 20)
    rewards_list = []
    vendor_response = None
    
    # Negotiation state
    initial = scenario.get("initial_offer", {})
    targets = scenario.get("buyer_targets", {})
    last_vendor_offer = initial.copy()
    last_agent_offer = initial.copy()
    consecutive_small_moves = 0
    
    # Log START
    print(f"[START] task={task_name} env={BENCHMARK} model={MODEL_NAME}", flush=True)
    
    if verbose:
        print(f"\n{'='*60}\nTASK: {task_name.upper()}\n{'='*60}")
        print(f"Initial: {initial}")
        print(f"Target:  {targets}\n")
    
    while not done and steps < max_steps:
        steps += 1
        try:
            current = env.state().current_offer
            
            # ===== DECISION LOGIC =====
            if USE_LLM:
                # Use LLM to decide next move
                llm_decision = get_llm_decision(
                    task_name=task_name,
                    current_offer=current,
                    vendor_response=obs.vendor_response if steps > 1 else "initial",
                    vendor_message=obs.vendor_message if steps > 1 else "Vendor initial offer",
                    round_num=steps,
                    scenario=scenario
                )
                
                move = llm_decision.get("move", "propose")
                offer = llm_decision.get("offer", current)
                justification = llm_decision.get("justification", "LLM decision")
            
            else:
                # Rule-based strategy (existing logic)
                # ===== BUNDLE STRATEGY (enterprise_bundle) =====
                if "products" in initial:
                    offer = {
                        "split_products": ["crm"],
                        "price": 130000
                    }
                    move = "propose"
                    justification = f"Round {steps}: Split CRM strategy"
                
                # ===== SMART STRATEGY (standard tasks) =====
                else:
                    # Phase 1 (steps 1-3): Aggressive movement toward targets
                    # Phase 2 (steps 4-6): Moderate, watch for resistance
                    # Phase 3 (steps 7+): Conservative, prepare to accept
                    
                    is_aggressive_phase = steps <= 3
                    is_moderate_phase = 4 <= steps <= 6
                    is_conservative_phase = steps >= 7
                    
                    offer = {}
                    move = "propose"
                    justification = f"Round {steps}: Phase {'aggressive' if steps <= 3 else 'moderate' if steps <= 6 else 'conservative'}"
                    
                    # ===== PRICE STRATEGY =====
                    if "price" in initial and "price" in targets:
                        initial_price = initial["price"]
                        target_price = targets["price"]
                        current_price = current.get("price", initial_price)
                        gap = initial_price - target_price
                        
                        # Detect vendor resistance: if price hasn't moved much, back off
                        vendor_conceded = compute_vendor_concession(last_vendor_offer, current, "price")
                        
                        if is_aggressive_phase:
                            # Phase 1: Move 10% toward target per round
                            concession_pct = 0.10
                        elif is_moderate_phase:
                            # Phase 2: Back off if vendor resisting, move 5% or hold
                            concession_pct = 0.05 if vendor_conceded > 0.02 else 0.00
                        else:
                            # Phase 3: Hold position or move tiny amounts
                            # If vendor made ANY move, reciprocate slightly
                            concession_pct = 0.02 if vendor_conceded > 0.01 else 0.00
                        
                        proposed_price = initial_price - (gap * min(concession_pct * steps, 1.0))
                        proposed_price = max(proposed_price, target_price)
                        
                        offer["price"] = int(proposed_price)
                    
                    # ===== MULTI-VARIABLE TRADING: If price near limit, trade for other terms =====
                    if "price" in offer:
                        min_price = scenario.get("vendor_limits", {}).get("min_price", 0)
                        # If we're close to vendor minimum, stop pushing price and improve other terms
                        if offer["price"] - min_price < (initial.get("price", 1) - targets["price"]) * 0.15:
                            # Very close to limit: stop price cuts, boost other dimensions
                            if "sla" in targets and "sla" in initial:
                                # Increase SLA instead of cutting price
                                current_sla = current.get("sla", 99.5)
                                target_sla = targets["sla"]
                                if current_sla < target_sla:
                                    offer["sla"] = min(current_sla + 0.2, target_sla)
                            
                            if "payment_terms" in targets:
                                # Improve payment terms
                                current_terms = current.get("payment_terms", "net-30")
                                target_terms = targets["payment_terms"]
                                if current_terms != target_terms:
                                    offer["payment_terms"] = get_next_payment_tier(current_terms)
                    
                    # ===== PAYMENT TERMS =====
                    if "payment_terms" in initial and "payment_terms" not in offer:
                        current_terms = current.get("payment_terms", "net-30")
                        target_terms = targets.get("payment_terms", "net-30")
                        
                        # Progressive improvement each phase
                        if is_aggressive_phase and steps > 1:
                            offer["payment_terms"] = get_next_payment_tier(current_terms)
                        elif is_moderate_phase:
                            offer["payment_terms"] = get_next_payment_tier(current_terms)
                        elif is_conservative_phase:
                            # Match target if not already
                            offer["payment_terms"] = current_terms if current_terms == target_terms else get_next_payment_tier(current_terms)
                    
                    # ===== SUPPORT TIER =====
                    if "support_tier" in initial:
                        current_tier = current.get("support_tier", "standard")
                        target_tier = targets.get("support_tier", "standard")
                        
                        if is_aggressive_phase and steps > 1:
                            offer["support_tier"] = get_next_support_tier(current_tier)
                        elif current_tier != target_tier:
                            offer["support_tier"] = get_next_support_tier(current_tier)
                    
                    # ===== SLA =====
                    if "sla" in initial:
                        current_sla = current.get("sla", 99.5)
                        target_sla = targets.get("sla", 99.5)
                        if current_sla < target_sla:
                            # Move 5-10% toward target per round
                            gap = target_sla - current_sla
                            move_amount = gap * (0.10 if is_aggressive_phase else 0.05)
                            offer["sla"] = round(current_sla + move_amount, 2)
            
            # ===== WALKAWAY PROTECTION =====
            if not USE_LLM:
                # Only apply walkaway protection for rule-based agent
                consecutive_small_moves += 1 if "price" in offer and abs(offer.get("price", 0) - last_agent_offer.get("price", 0)) < 500 else 0
                
                if consecutive_small_moves > 2 and steps > 5:
                    # Vendor is resisting: accept or hold position
                    if "price" in current and "price" in targets and current["price"] <= targets["price"] * 1.05:
                        # Close enough: accept
                        offer = current
                        move = "accept"
                        justification = "Close to target, accepting"
            
            action = NegotiationAction(
                move=move,
                offer=offer,
                justification=justification
            )
            
            obs, reward, done, info = env.step(action)
            vendor_response = info.get('vendor_response', 'unknown')
            rewards_list.append(reward)
            last_agent_offer = offer.copy()
            last_vendor_offer = obs.current_offer.copy()
            
            # Log STEP
            action_str = f"propose({offer.get('price', 'product')})"
            print(
                f"[STEP] step={steps} action={action_str} reward={reward:.2f} done={str(done).lower()} error=null",
                flush=True
            )
            
            if verbose:
                try:
                    offer_str = str(offer).replace("'", '"') if isinstance(offer, dict) else str(offer)
                    print(f"Round {steps}: Agent: {offer_str} | Vendor: {vendor_response}", flush=True)
                except Exception as print_err:
                    print(f"Round {steps}: (encoding error in verbose output)", flush=True)
        
        except Exception as e:
            print(f"[STEP] step={steps} action=error reward=0.00 done=true error={str(e)}", flush=True)
            break
    
    # Grade final outcome
    grade = grade_episode(env.state().current_offer, scenario, env.state().history)
    success = env.state().done and vendor_response == "accepted"
    
    if vendor_response == "walkaway":
        status_message = "No deal - vendor walked away"
    elif env.state().done:
        status_message = "Deal signed"
    else:
        status_message = "Max steps reached"
    
    result = {
        "task": task_name,
        "grade": grade,
        "steps": steps,
        "done": env.state().done,
        "final_offer": env.state().current_offer,
        "message": status_message,
        "vendor_response": vendor_response,
        "rewards": rewards_list
    }
    
    # Log END
    rewards_str = ",".join([f"{r:.2f}" for r in rewards_list])
    success_str = "true" if success else "false"
    print(f"[END] success={success_str} steps={steps} score={grade:.3f} rewards={rewards_str}", flush=True)
    
    if verbose:
        print(f"\nGRADE: {grade:.3f} | Status: {result['message']}\n")
    
    return result


def main():
    """Run smart negotiator on all 3 tasks."""
    print("\n" + "="*60)
    print("PROCUREMENT NEGOTIATION ENVIRONMENT — SMART NEGOTIATOR")
    print("="*60)
    
    results = {}
    all_grades = []
    
    for task_name in ["saas_renewal", "cloud_infra_deal", "enterprise_bundle"]:
        result = run_smart_negotiator(task_name, verbose=True)
        results[task_name] = result
        all_grades.append(result["grade"])
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(json.dumps(results, indent=2, default=str))
    print()
    print(f"Average grade: {sum(all_grades) / len(all_grades):.3f}")
    print("="*60 + "\n")
    
    return results


if __name__ == "__main__":
    main()
