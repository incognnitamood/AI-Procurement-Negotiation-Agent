"""
Hybrid FastAPI + Gradio Application
Runs both API endpoints and web UI in a single process

API Endpoints (for OpenEnv validator):
  - POST /reset
  - POST /step
  - GET /state

UI (for human interaction):
  - GET / (Gradio interface at root)
"""

import traceback
from typing import Dict, Any, Optional
import uuid

import gradio as gr
from fastapi import FastAPI, HTTPException, Body
from environment import NegotiationEnvironment
from models import NegotiationAction
from scenarios import SCENARIOS

print("[INFO] Starting hybrid FastAPI + Gradio application", flush=True)

# ============================================================================
# SHARED SESSION STORE (used by both API and UI)
# ============================================================================
SESSIONS: Dict[str, Dict[str, Any]] = {}

def create_session(task: str) -> str:
    """Create a new session and return session_id."""
    session_id = str(uuid.uuid4())
    env = NegotiationEnvironment()
    obs = env.reset(task)
    
    SESSIONS[session_id] = {
        "env": env,
        "task": task,
        "obs": obs,
    }
    return session_id

def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve session data."""
    return SESSIONS.get(session_id)

# ============================================================================
# FASTAPI ENDPOINTS (for OpenEnv validator)
# ============================================================================
app = FastAPI(title="Procurement Negotiation OpenEnv")

@app.post("/reset")
async def reset(request: Dict[str, Any] = Body(default={})):
    """
    Reset negotiation environment.
    
    Request:
        {"task": "saas_renewal", "session_id": "optional-id"}
    
    Response:
        {"observation": {...}, "info": {"task": "...", "session_id": "..."}}
    """
    try:
        task = request.get("task") or request.get("task_name", "saas_renewal")
        
        # Create or reuse session
        if "session_id" in request:
            session_id = request["session_id"]
            if session_id in SESSIONS:
                return {
                    "observation": SESSIONS[session_id]["obs"].model_dump(),
                    "info": {"task": task, "session_id": session_id}
                }
        
        session_id = create_session(task)
        return {
            "observation": SESSIONS[session_id]["obs"].model_dump(),
            "info": {"task": task, "session_id": session_id}
        }
    except Exception as e:
        print(f"[ERROR] /reset: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/step")
async def step(request: Dict[str, Any] = Body(default={})):
    """
    Execute one negotiation step.
    
    Request:
        {
            "session_id": "...",
            "action": {
                "move": "propose|counter|accept|reject",
                "offer": {"price": 110000, "sla": 99.5, ...},
                "justification": "..."
            }
        }
    
    Response:
        {
            "observation": {...},
            "reward": 0.35,
            "done": false,
            "info": {...}
        }
    """
    try:
        session_id = request.get("session_id")
        action_data = request.get("action")
        
        if not session_id or not action_data:
            raise ValueError("Missing session_id or action")
        
        session = get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        env = session["env"]
        action = NegotiationAction(**action_data)
        obs, reward, done, info = env.step(action)
        
        # Update session
        SESSIONS[session_id]["obs"] = obs
        
        return {
            "observation": obs.model_dump(),
            "reward": float(reward),
            "done": bool(done),
            "info": info
        }
    except Exception as e:
        print(f"[ERROR] /step: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/state")
async def get_state(session_id: str):
    """
    Get current negotiation state.
    
    Response:
        {"state": {...}}
    """
    try:
        session = get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        env = session["env"]
        state = env.state()
        return {"state": state.model_dump()}
    except Exception as e:
        print(f"[ERROR] /state: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}

# ============================================================================
# GRADIO UI (for human interaction)
# ============================================================================

def start_negotiation(task: str, session_state) -> tuple:
    """Initialize a new negotiation (Gradio callback)."""
    if session_state:
        return "Session already active", session_state, [], [], 0.0, "0", []
    
    try:
        session_id = create_session(task)
        session_obj = SESSIONS[session_id]
        obs = session_obj["obs"]
        
        # Build offer table
        scenario = SCENARIOS.get(task, {})
        buyer_targets = scenario.get("buyer_targets", {})
        offer_table = []
        current_offer = obs.current_offer
        
        if "price" in current_offer:
            target_price = buyer_targets.get("price", "N/A")
            target_str = f"${target_price}" if target_price != "N/A" else str(target_price)
            offer_table.append(["Price", f"${current_offer['price']}", target_str])
        
        if "sla" in current_offer:
            target_sla = buyer_targets.get("sla", "N/A")
            target_str = f"{target_sla}%" if target_sla != "N/A" else str(target_sla)
            offer_table.append(["SLA", f"{current_offer['sla']}%", target_str])
        
        if "support_tier" in current_offer:
            target_support = buyer_targets.get("support_tier", "N/A")
            offer_table.append(["Support", current_offer["support_tier"], str(target_support)])
        
        if "payment_terms" in current_offer:
            target_payment = buyer_targets.get("payment_terms", "N/A")
            offer_table.append(["Payment", current_offer["payment_terms"], str(target_payment)])
        
        vendor_msg = obs.vendor_message
        chatbot_history = [(None, vendor_msg)]
        
        return "Negotiation started!", {"session_id": session_id, "task": task}, offer_table, chatbot_history, 0.0, str(obs.round_number), []
    
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"[ERROR] start_negotiation: {error_msg}\n{traceback.format_exc()}")
        return error_msg, None, [], [], 0.0, "0", []

def submit_offer(session_state: Dict, chat_history: list, move: str, price: float, sla: float, 
                 support: str, payment: str, justification: str, task: str) -> tuple:
    """Submit an offer (Gradio callback)."""
    if not session_state:
        return "Start negotiation first", [], [], 0.0, "0", []
    
    try:
        session_id = session_state.get("session_id")
        session = get_session(session_id)
        if not session:
            return "Session expired", [], [], 0.0, "0", []
        
        env = session["env"]
        action = NegotiationAction(
            move=move,
            offer={
                "price": price,
                "sla": sla,
                "support_tier": support,
                "payment_terms": payment
            },
            justification=justification
        )
        
        obs, reward, done, info = env.step(action)
        session["obs"] = obs
        
        # Build offer table
        scenario = SCENARIOS.get(task, {})
        buyer_targets = scenario.get("buyer_targets", {})
        offer_table = []
        current_offer = obs.current_offer
        
        if "price" in current_offer:
            target_price = buyer_targets.get("price", "N/A")
            target_str = f"${target_price}" if target_price != "N/A" else str(target_price)
            offer_table.append(["Price", f"${current_offer['price']}", target_str])
        
        if "sla" in current_offer:
            target_sla = buyer_targets.get("sla", "N/A")
            target_str = f"{target_sla}%" if target_sla != "N/A" else str(target_sla)
            offer_table.append(["SLA", f"{current_offer['sla']}%", target_str])
        
        if "support_tier" in current_offer:
            target_support = buyer_targets.get("support_tier", "N/A")
            offer_table.append(["Support", current_offer["support_tier"], str(target_support)])
        
        if "payment_terms" in current_offer:
            target_payment = buyer_targets.get("payment_terms", "N/A")
            offer_table.append(["Payment", current_offer["payment_terms"], str(target_payment)])
        
        chatbot_history = chat_history or []
        user_message = f"{move.capitalize()} | ${price} | SLA {sla}% | {support} | {payment}"
        vendor_msg = obs.vendor_message
        chatbot_history.append((user_message, vendor_msg))
        
        if done:
            if obs.vendor_response == "accepted":
                status = "Deal signed successfully!"
            else:
                status = "Negotiation ended"
        else:
            status = "Offer submitted, waiting for vendor response..."
        
        return status, offer_table, chatbot_history, obs.deal_value_so_far, str(obs.round_number), []
    
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"[ERROR] submit_offer: {error_msg}\n{traceback.format_exc()}")
        return error_msg, [], [], 0.0, "0", []

# Build Gradio interface
with gr.Blocks(title="🤝 Procurement Negotiation Simulator") as demo:
    gr.Markdown("# 🤝 Procurement Negotiation Simulator")
    
    with gr.Row():
        task_dropdown = gr.Dropdown(
            label="Select Task",
            choices=["saas_renewal", "cloud_infra_deal", "enterprise_bundle"],
            value="saas_renewal"
        )
        start_button = gr.Button("🚀 Start Negotiation")
        status_textbox = gr.Textbox(label="Status", interactive=False)
        session_state = gr.State()
        chatbot_history_state = gr.State([])
    
    with gr.Row():
        offer_dataframe = gr.DataFrame(
            label="Current Offer",
            headers=["Dimension", "Vendor Offer", "Your Target"],
            interactive=False
        )
    
    with gr.Row():
        move_dropdown = gr.Dropdown(
            label="Move Type",
            choices=["propose", "counter", "accept", "reject"],
            value="propose"
        )
        price_number = gr.Number(label="Price ($)", value=115000)
        sla_slider = gr.Slider(label="SLA %", minimum=99.0, maximum=100.0, step=0.01, value=99.5)
        support_dropdown = gr.Dropdown(
            label="Support Tier",
            choices=["standard", "business", "premium"],
            value="standard"
        )
        payment_dropdown = gr.Dropdown(
            label="Payment Terms",
            choices=["net-30", "net-60", "net-90"],
            value="net-30"
        )
        justification_textbox = gr.Textbox(label="Justification — explain your reasoning")
        submit_button = gr.Button("📨 Submit Offer")
    
    with gr.Row():
        chatbot = gr.Chatbot(label="Negotiation Log", height=300)
    
    with gr.Row():
        deal_slider = gr.Slider(label="Deal Value", minimum=0.0, maximum=1.0, interactive=False, value=0.0)
        round_textbox = gr.Textbox(label="Round", interactive=False)
    
    # Callbacks
    start_button.click(
        start_negotiation,
        inputs=[task_dropdown, session_state],
        outputs=[status_textbox, session_state, offer_dataframe, chatbot, deal_slider, round_textbox, chatbot_history_state]
    )
    
    submit_button.click(
        submit_offer,
        inputs=[session_state, chatbot_history_state, move_dropdown, price_number, sla_slider, 
                support_dropdown, payment_dropdown, justification_textbox, task_dropdown],
        outputs=[status_textbox, offer_dataframe, chatbot, deal_slider, round_textbox, chatbot_history_state]
    )

# ============================================================================
# MOUNT GRADIO ON FASTAPI (single process)
# ============================================================================
app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    import uvicorn
    print("[INFO] Starting server on port 7860...")
    uvicorn.run(app, host="0.0.0.0", port=7860)
