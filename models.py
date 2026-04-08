"""
Negotiation environment models for OpenEnv.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any


class NegotiationAction(BaseModel):
    """
    Represents a negotiation action taken by the buyer agent.
    
    Attributes:
        move: Type of move - one of "propose", "accept", "reject", "counter"
        offer: Dictionary containing the proposed offer details
        justification: Reasoning or explanation for the move
        split_products: Optional list of products for splitting tactics
    """
    move: str
    offer: Dict[str, Any]
    justification: str
    split_products: Optional[List[str]] = None
    
    @field_validator("move")
    @classmethod
    def validate_move(cls, v):
        """Ensure move is one of the valid negotiation actions."""
        valid_moves = {"propose", "accept", "reject", "counter"}
        if v not in valid_moves:
            raise ValueError(f"move must be one of {valid_moves}, got {v}")
        return v
    
    @field_validator("offer")
    @classmethod
    def validate_offer(cls, v):
        """Ensure offer is a non-empty dictionary with valid price if present."""
        if not isinstance(v, dict) or len(v) == 0:
            raise ValueError("offer must be a non-empty dictionary")
        
        # Enforce price positive if present
        price = v.get("price")
        if price is not None and price <= 0:
            raise ValueError("price must be positive")
        
        return v


class NegotiationObservation(BaseModel):
    """
    Represents the observation received from the negotiation environment.
    
    Attributes:
        vendor_response: Vendor's action response
        current_offer: Current offer on the table
        vendor_message: Message or rationale from vendor
        round_number: Current negotiation round
        concessions_won: List of concessions obtained so far
        deal_value_so_far: Accumulated value from the deal
        available_moves: List of valid moves available to the agent
        task_brief: Brief description of the negotiation task
        done: Whether negotiation is complete
        reward: Reward value for the step
        metadata: Additional metadata
    """
    vendor_response: str
    current_offer: Dict[str, Any]
    vendor_message: str
    round_number: int
    concessions_won: List[str]
    deal_value_so_far: float
    available_moves: List[str]
    task_brief: str
    done: bool = False
    reward: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator("available_moves")
    @classmethod
    def validate_available_moves(cls, v):
        """Ensure all moves in available_moves are valid."""
        valid_moves = {"propose", "accept", "reject", "counter"}
        for move in v:
            if move not in valid_moves:
                raise ValueError(f"Invalid move in available_moves: {move}")
        return v


class NegotiationState(BaseModel):
    """
    Represents the internal state of the negotiation.
    
    Attributes:
        task_name: Name of the negotiation scenario
        round_number: Current round of negotiation
        current_offer: Current offer being negotiated
        initial_offer: Vendor's initial offer
        buyer_targets: Target goals for the buyer
        history: List of past moves and responses
        done: Whether negotiation is complete
        final_score: Final score if negotiation is complete
    """
    task_name: str
    round_number: int
    current_offer: Dict[str, Any]
    initial_offer: Dict[str, Any]
    buyer_targets: Dict[str, Any]
    history: List[Dict[str, Any]] = Field(default_factory=list)
    done: bool = False
    final_score: Optional[float] = None
    
    @field_validator("current_offer", "initial_offer", "buyer_targets", mode="before")
    @classmethod
    def validate_sla(cls, v):
        """Validate SLA values are between 99.0 and 100.0 if present."""
        if isinstance(v, dict):
            sla = v.get("sla")
            if sla is not None:
                if not isinstance(sla, (int, float)) or not (99.0 <= sla <= 100.0):
                    raise ValueError(f"SLA must be between 99.0 and 100.0, got {sla}")
        return v
