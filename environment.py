"""
Negotiation environment with vendor simulator.
"""

from scenarios import SCENARIOS
from models import NegotiationAction, NegotiationObservation, NegotiationState
from typing import Tuple, Dict, Any, List
import sys


# Payment terms ranking (higher number = more favorable to vendor)
PAYMENT_RANK = {
    "net-30": 1,
    "net-45": 2,
    "net-60": 3,
    "net-90": 4,
}

# Support tier ranking (higher number = more expensive/premium)
SUPPORT_RANK = {
    "standard": 1,
    "business": 2,
    "premium": 3,
}


class VendorSimulator:
    """
    Simulates vendor behavior during negotiations.
    
    Handles vendor responses based on buyer offers, scenario constraints,
    and negotiation history.
    """
    
    def respond(
        self,
        buyer_offer: Dict[str, Any],
        scenario: Dict[str, Any],
        round_num: int,
        history: List[Dict[str, Any]],
        current_offer: Dict[str, Any] = None,
    ) -> Tuple[str, str, Dict[str, Any]]:
        """
        Generate vendor response to buyer offer.
        
        Args:
            buyer_offer: Current offer from buyer
            scenario: Scenario configuration from SCENARIOS
            round_num: Current negotiation round number
            history: List of past moves and responses
            current_offer: Current vendor position (for accumulating concessions)
            
        Returns:
            Tuple of (vendor_response, message, counter_offer_dict)
            where vendor_response is one of: "accepted", "rejected", "countered", "walkaway"
        """
        
        # Extract vendor constraints
        vendor_limits = scenario.get("vendor_limits", {})
        walkaway_rounds = vendor_limits.get("walkaway_rounds", 10)
        min_price = vendor_limits.get("min_price", 0)
        
        # Check if negotiation should end (walkaway)
        if round_num > walkaway_rounds:
            return (
                "walkaway",
                f"Vendor walking away after round {round_num}",
                {},
            )
        
        # Extract offer price
        offer_price = buyer_offer.get("price", 0)
        
        # Check if price is below vendor minimum
        if offer_price < min_price:
            return (
                "rejected",
                f"Price {offer_price} below vendor minimum {min_price}",
                {},
            )
        
        # Check if buyer targets are met
        if self._targets_met(buyer_offer, scenario):
            return (
                "accepted",
                "Offer meets vendor acceptance criteria.",
                buyer_offer,
            )
        
        # Generate counter offer
        counter_offer = self._generate_counter_offer(
            buyer_offer, scenario, history, current_offer
        )
        
        return (
            "countered",
            "Vendor generated counter-proposal.",
            counter_offer,
        )
    
    def _targets_met(self, buyer_offer: Dict[str, Any], scenario: Dict[str, Any]) -> bool:
        """
        Check if buyer offer meets vendor's acceptance criteria.
        
        Args:
            buyer_offer: Current offer from buyer
            scenario: Scenario configuration
            
        Returns:
            True if all targets are met, False otherwise
        """
        buyer_targets = scenario.get("buyer_targets", {})
        
        # Check each dimension in buyer_targets
        # Price: offer price must be <= target price
        if "price" in buyer_targets:
            if buyer_offer.get("price", float('inf')) > buyer_targets["price"]:
                return False
        
        # Payment terms: offer rank must be >= target rank
        if "payment_terms" in buyer_targets:
            offer_rank = PAYMENT_RANK.get(buyer_offer.get("payment_terms", "net-30"), 1)
            target_rank = PAYMENT_RANK.get(buyer_targets["payment_terms"], 1)
            if offer_rank < target_rank:
                return False
        
        # Support tier: offer rank must be >= target rank
        if "support_tier" in buyer_targets:
            offer_rank = SUPPORT_RANK.get(buyer_offer.get("support_tier", "standard"), 1)
            target_rank = SUPPORT_RANK.get(buyer_targets["support_tier"], 1)
            if offer_rank < target_rank:
                return False
        
        # SLA: offer sla must be >= target sla
        if "sla" in buyer_targets:
            if buyer_offer.get("sla", 0.0) < buyer_targets["sla"]:
                return False
        
        return True
    
    def _generate_counter_offer(
        self,
        buyer_offer: Dict[str, Any],
        scenario: Dict[str, Any],
        history: List[Dict[str, Any]],
        current_offer: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Generate counter offer from vendor.
        
        Vendor moves 30% toward buyer offer on each round for:
        - Price (toward buyer price, capped at min_price)
        - Payment terms (one step closer using PAYMENT_RANK)
        - Support tier (upgrade by one level using SUPPORT_RANK)
        - SLA (increase slightly, capped at vendor limits)
        
        Args:
            buyer_offer: Current offer from buyer
            scenario: Scenario configuration
            history: Negotiation history
            current_offer: Current vendor position (for accumulating concessions)
            
        Returns:
            Counter offer dictionary (deterministic, no randomness)
        """
        initial_offer = scenario.get("initial_offer", {})
        vendor_limits = scenario.get("vendor_limits", {})
        min_price = vendor_limits.get("min_price", initial_offer.get("price", 0))
        
        # Start with current vendor position to accumulate concessions
        if current_offer is None:
            counter_offer = initial_offer.copy()
        else:
            counter_offer = current_offer.copy()
        
        # ===== PRICE: Move 30% toward buyer =====
        if "price" in buyer_offer:
            current_price = counter_offer.get("price", initial_offer.get("price", 0))
            buyer_price = buyer_offer["price"]
            
            # new_price = current_price - 0.3 * (current_price - buyer_price)
            new_price = current_price - 0.3 * (current_price - buyer_price)
            
            # Never go below vendor minimum
            counter_offer["price"] = max(new_price, min_price)
        
        # ===== PAYMENT_TERMS: Move one step closer =====
        if "payment_terms" in buyer_offer:
            current_terms = counter_offer.get("payment_terms", "net-30")
            buyer_terms = buyer_offer["payment_terms"]
            
            current_rank = PAYMENT_RANK.get(current_terms, 1)
            buyer_rank = PAYMENT_RANK.get(buyer_terms, 1)
            
            # If buyer terms are more favorable (higher rank), move toward them
            if buyer_rank > current_rank:
                # Move one step closer
                new_rank = min(current_rank + 1, buyer_rank)
                # Find the term string for this rank
                for term, rank in PAYMENT_RANK.items():
                    if rank == new_rank:
                        counter_offer["payment_terms"] = term
                        break
        
        # ===== SUPPORT_TIER: Upgrade by one level =====
        if "support_tier" in buyer_offer:
            current_tier = counter_offer.get("support_tier", "standard")
            buyer_tier = buyer_offer["support_tier"]
            
            current_rank = SUPPORT_RANK.get(current_tier, 1)
            buyer_rank = SUPPORT_RANK.get(buyer_tier, 1)
            
            # If buyer tier is more premium (higher rank), move toward it
            if buyer_rank > current_rank:
                # Upgrade by one level
                new_rank = min(current_rank + 1, buyer_rank)
                # Find the tier string for this rank
                for tier, rank in SUPPORT_RANK.items():
                    if rank == new_rank:
                        counter_offer["support_tier"] = tier
                        break
        
        # ===== SLA: Increase slightly but cap at limits =====
        if "sla" in buyer_offer:
            current_sla = counter_offer.get("sla", 99.0)
            buyer_sla = buyer_offer["sla"]
            max_sla = vendor_limits.get("max_sla", 100.0)
            
            # If buyer SLA is higher, move toward it by 30%
            if buyer_sla > current_sla:
                new_sla = current_sla + 0.3 * (buyer_sla - current_sla)
                counter_offer["sla"] = min(new_sla, max_sla)
        
        return counter_offer


class NegotiationEnvironment:
    """
    Negotiation environment with state management and reward computation.
    
    Manages negotiation episodes, vendor interactions, and reinforcement
    learning loop for procurement scenarios.
    """
    
    def __init__(self):
        """Initialize environment with vendor simulator."""
        self._vendor = VendorSimulator()
        self._state = None
    
    def reset(self, task_name: str) -> NegotiationObservation:
        """
        Reset environment for a new negotiation episode.
        
        Args:
            task_name: Name of scenario ("saas_renewal", "cloud_infra_deal", "enterprise_bundle")
            
        Returns:
            Initial NegotiationObservation for the episode
        """
        if task_name not in SCENARIOS:
            raise ValueError(f"Unknown task: {task_name}. Available: {list(SCENARIOS.keys())}")
        
        scenario = SCENARIOS[task_name]
        initial_offer = scenario.get("initial_offer", {})
        buyer_targets = scenario.get("buyer_targets", {})
        
        # Initialize state
        self._state = NegotiationState(
            task_name=task_name,
            round_number=0,
            current_offer=initial_offer.copy(),
            initial_offer=initial_offer.copy(),
            buyer_targets=buyer_targets,
            history=[],
            done=False,
            final_score=None,
        )
        
        # Return initial observation
        return NegotiationObservation(
            vendor_response="initial",
            current_offer=initial_offer.copy(),
            vendor_message="Vendor initial offer presented",
            round_number=0,
            concessions_won=[],
            deal_value_so_far=0.0,
            available_moves=["propose", "accept", "reject", "counter"],
            task_brief=f"Negotiate {task_name} to meet buyer targets",
        )
    
    def step(self, action: NegotiationAction) -> Tuple[NegotiationObservation, float, bool, Dict[str, Any]]:
        """
        Execute one step of negotiation.
        
        Args:
            action: NegotiationAction with move, offer, justification
            
        Returns:
            Tuple of (observation, reward, done, info)
        """
        if self._state is None:
            raise RuntimeError("Call reset() before step()")
        
        scenario = SCENARIOS[self._state.task_name]
        self._state.round_number += 1
        
        # Record buyer's action in history
        self._state.history.append({
            "round": self._state.round_number,
            "actor": "buyer",
            "move": action.move,
            "offer": action.offer,
            "justification": action.justification,
            "split_products": action.split_products,
        })
        
        # Get vendor response
        vendor_response, vendor_msg, counter_offer = self._vendor.respond(
            buyer_offer=action.offer,
            scenario=scenario,
            round_num=self._state.round_number,
            history=self._state.history,
            current_offer=self._state.current_offer,
        )
        
        # Update state based on vendor response
        done = False
        reward = 0.0
        
        if vendor_response == "accepted":
            self._state.current_offer = action.offer.copy()
            self._state.done = True
            done = True
            reward = self._compute_reward(action.offer, scenario, self._state.history)
        
        elif vendor_response == "rejected":
            self._state.done = True
            done = True
            reward = 0.0  # No reward for rejection
        
        elif vendor_response == "walkaway":
            self._state.done = True
            done = True
            reward = 0.0  # No reward for walkaway
        
        elif vendor_response == "countered":
            self._state.current_offer = counter_offer.copy()
            reward = self._compute_reward(self._state.current_offer, scenario, self._state.history)
        
        # Record vendor's response
        self._state.history.append({
            "round": self._state.round_number,
            "actor": "vendor",
            "move": vendor_response,
            "offer": counter_offer,
            "message": vendor_msg,
        })
        
        # Compute deal value so far (normalized reward)
        deal_value = self._compute_reward(self._state.current_offer, scenario)
        
        # Build info dict
        info = {
            "vendor_response": vendor_response,
            "vendor_message": vendor_msg,
            "deal_value": deal_value,
        }
        
        # Create observation
        observation = NegotiationObservation(
            vendor_response=vendor_response,
            current_offer=self._state.current_offer.copy(),
            vendor_message=vendor_msg,
            round_number=self._state.round_number,
            concessions_won=self._extract_concessions(),
            deal_value_so_far=deal_value,
            available_moves=["propose", "accept", "reject", "counter"] if not done else [],
            task_brief=f"Round {self._state.round_number}",
        )
        
        return observation, reward, done, info
    
    def state(self) -> NegotiationState:
        """
        Get current negotiation state.
        
        Returns:
            NegotiationState instance
        """
        if self._state is None:
            raise RuntimeError("Environment not initialized. Call reset() first.")
        return self._state
    
    def _compute_reward(self, current_offer: Dict[str, Any], scenario: Dict[str, Any], history: List[Dict[str, Any]] = None) -> float:
        """
        Compute reward for current negotiation state.
        
        For enterprise_bundle (split_crm strategy), uses grader logic to compute reward.
        For other scenarios, uses price/support/payment/sla rewards.
        
        Args:
            current_offer: Current offer in negotiation state
            scenario: Scenario configuration
            history: Negotiation history (for bundle trap evaluation)
            
        Returns:
            Reward value (float, normalized to [0, 1])
        """
        from graders import grade_episode
        
        # For enterprise_bundle with split_crm strategy, use grader to compute reward
        if scenario.get("optimal_strategy") == "split_crm" and history is not None:
            return grade_episode(current_offer, scenario, history)
        
        # Standard reward computation for other scenarios
        reward = 0.0
        initial_offer = scenario.get("initial_offer", {})
        buyer_targets = scenario.get("buyer_targets", {})
        
        # ===== PRICE REWARD =====
        if "price" in current_offer and "price" in initial_offer:
            price_saved = initial_offer["price"] - current_offer["price"]
            target_savings = initial_offer.get("price", 1) - buyer_targets.get("price", initial_offer.get("price", 1))
            
            if price_saved > 0:
                # Scale reward by percentage of target savings achieved
                if target_savings > 0:
                    reward += min(price_saved / target_savings * 10.0, 10.0)
                else:
                    reward += 5.0
        
        # ===== PAYMENT TERMS REWARD =====
        if "payment_terms" in current_offer:
            current_rank = PAYMENT_RANK.get(current_offer.get("payment_terms", "net-30"), 1)
            target_rank = PAYMENT_RANK.get(buyer_targets.get("payment_terms", "net-30"), 1)
            
            if current_rank >= target_rank:
                reward += 2.0
        
        # ===== SUPPORT TIER REWARD =====
        if "support_tier" in current_offer:
            current_tier = SUPPORT_RANK.get(current_offer.get("support_tier", "standard"), 1)
            target_tier = SUPPORT_RANK.get(buyer_targets.get("support_tier", "standard"), 1)
            
            if current_tier >= target_tier:
                reward += 2.0
        
        # Normalize reward to [0.0, 1.0]
        return round(min(max(reward / 14.0, 0.0), 1.0), 4)
    
    def _extract_concessions(self) -> List[str]:
        """
        Extract list of concessions won so far.
        
        Returns:
            List of concession descriptions
        """
        concessions = []
        if not self._state.history:
            return concessions
        
        initial = self._state.initial_offer
        current = self._state.current_offer
        
        # Price concession
        if initial.get("price", 0) > current.get("price", 0):
            price_diff = initial.get("price", 0) - current.get("price", 0)
            concessions.append(f"Price reduced by {price_diff}")
        
        # Payment terms concession
        if initial.get("payment_terms") != current.get("payment_terms"):
            concessions.append(f"Payment terms improved to {current.get('payment_terms')}")
        
        # Support tier concession
        if initial.get("support_tier") != current.get("support_tier"):
            concessions.append(f"Support tier upgraded to {current.get('support_tier')}")
        
        # SLA concession
        if initial.get("sla", 0) < current.get("sla", 0):
            sla_diff = current.get("sla", 0) - initial.get("sla", 0)
            concessions.append(f"SLA improved by {sla_diff:.2f}")
        
        return concessions
