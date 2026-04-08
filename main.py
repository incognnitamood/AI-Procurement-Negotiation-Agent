"""
FastAPI + Gradio Procurement Negotiation OpenEnv
Single-process deployment with API and UI combined
"""

import traceback
import uuid
import json
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
import gradio as gr
import requests

from environment import NegotiationEnvironment
from models import NegotiationAction

print("[INFO] Starting OpenEnv API Server with Gradio UI", flush=True)

# Session storage
SESSIONS: Dict[str, Dict[str, Any]] = {}

app = FastAPI(title="Procurement Negotiation OpenEnv")

@app.get("/")
def root():
    """Root endpoint - redirect to UI."""
    return RedirectResponse(url="/ui")

@app.post("/reset")
async def reset(request: Request):
    """Reset negotiation environment."""
    try:
        try:
            body = await request.json()
        except:
            body = {}
        
        task = body.get("task") or body.get("task_name", "saas_renewal")
        
        # Check if session already exists
        if "session_id" in body and body["session_id"] in SESSIONS:
            session_id = body["session_id"]
            obs = SESSIONS[session_id]["obs"]
            obs_dict = obs.model_dump()
            reward = obs_dict.pop("reward", None)
            done = obs_dict.pop("done", None)
            return {
                "observation": obs_dict,
                "reward": float(reward) if reward is not None else 0.0,
                "done": bool(done) if done is not None else False,
                "info": {"task": task, "session_id": session_id}
            }
        
        # Create new session
        session_id = str(uuid.uuid4())
        env = NegotiationEnvironment()
        obs = env.reset(task)
        SESSIONS[session_id] = {"env": env, "obs": obs, "task": task}
        
        obs_dict = obs.model_dump()
        reward = obs_dict.pop("reward", None)
        done = obs_dict.pop("done", None)
        
        return {
            "observation": obs_dict,
            "reward": float(reward) if reward is not None else 0.0,
            "done": bool(done) if done is not None else False,
            "info": {"task": task, "session_id": session_id}
        }
    except Exception as e:
        print(f"[ERROR] /reset: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/step")
async def step(request: Request):
    """Execute negotiation step."""
    try:
        try:
            body = await request.json()
        except:
            body = {}
        
        session_id = body.get("session_id")
        action_data = body.get("action")
        
        if not session_id or not action_data:
            raise ValueError("Missing session_id or action")
        
        if session_id not in SESSIONS:
            raise ValueError(f"Session not found: {session_id}")
        
        env = SESSIONS[session_id]["env"]
        action = NegotiationAction(**action_data)
        obs, reward, done, info = env.step(action)
        
        SESSIONS[session_id]["obs"] = obs
        
        obs_dict = obs.model_dump()
        obs_dict.pop("reward", None)
        obs_dict.pop("done", None)
        
        return {
            "observation": obs_dict,
            "reward": float(reward) if reward is not None else 0.0,
            "done": bool(done) if done is not None else False,
            "info": info
        }
    except Exception as e:
        print(f"[ERROR] /step: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/state")
async def get_state(session_id: str):
    """Get negotiation state."""
    try:
        if session_id not in SESSIONS:
            raise ValueError(f"Session not found: {session_id}")
        
        env = SESSIONS[session_id]["env"]
        state = env.state()
        return {"state": state.model_dump()}
    except Exception as e:
        print(f"[ERROR] /state: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok"}

# ==================== GRADIO UI ====================

def start_negotiation(task: str) -> tuple:
    """Initialize negotiation via API."""
    try:
        api_url = "http://localhost:7860"
        resp = requests.post(f"{api_url}/reset", json={"task": task}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        session_id = data["info"]["session_id"]
        obs = data["observation"]
        
        response_json = json.dumps(data, indent=2)
        
        return (
            f"✅ Session started: {session_id[:8]}...",
            session_id,
            response_json,
            obs.get("vendor_message", ""),
            str(obs.get("current_offer", {})),
            obs.get("deal_value_so_far", 0.0),
            str(obs.get("round_number", 0))
        )
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        print(f"[ERROR] start_negotiation: {error_msg}")
        return (error_msg, "", json.dumps({"error": str(e)}, indent=2), "", "{}", 0.0, "0")

def send_action(
    session_id: str,
    move: str,
    price: float,
    payment_terms: str,
    sla: float,
    support_tier: str,
    justification: str
) -> tuple:
    """Submit action via API."""
    if not session_id:
        return ("❌ No active session", json.dumps({"error": "Start negotiation first"}, indent=2), "", "{}", 0.0, "0")
    
    try:
        api_url = "http://localhost:7860"
        
        action = {
            "move": move,
            "offer": {
                "price": float(price),
                "payment_terms": payment_terms,
                "sla": float(sla),
                "support_tier": support_tier
            },
            "justification": justification
        }
        
        resp = requests.post(
            f"{api_url}/step",
            json={"session_id": session_id, "action": action},
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        
        obs = data["observation"]
        reward = data.get("reward", 0)
        done = data.get("done", False)
        
        response_json = json.dumps(data, indent=2)
        
        status = f"✅ Action sent | Reward: {reward:.3f} | Done: {done}"
        if done:
            status += f" | Final Score: {obs.get('deal_value_so_far', 0):.3f}"
        
        return (
            status,
            response_json,
            obs.get("vendor_message", ""),
            str(obs.get("current_offer", {})),
            obs.get("deal_value_so_far", 0.0),
            str(obs.get("round_number", 0))
        )
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        print(f"[ERROR] send_action: {error_msg}")
        return (error_msg, json.dumps({"error": str(e)}, indent=2), "", "{}", 0.0, "0")

# Build Gradio UI
with gr.Blocks(title="🤝 Procurement Negotiation Agent", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🤝 Procurement Negotiation Agent")
    gr.Markdown("Negotiate across **price**, **SLA**, **support tier**, and **payment terms** with an adaptive vendor.")
    
    session_id_state = gr.State("")
    
    with gr.Group():
        gr.Markdown("## 1️⃣ Start Negotiation")
        
        with gr.Row():
            task_dropdown = gr.Dropdown(
                label="Select Task",
                choices=["saas_renewal", "cloud_infra_deal", "enterprise_bundle"],
                value="saas_renewal",
                scale=1
            )
            start_btn = gr.Button("🚀 Start", variant="primary", scale=1)
        
        status_textbox = gr.Textbox(label="Status", interactive=False, lines=1)
    
    with gr.Group():
        gr.Markdown("## 2️⃣ Submit Your Offer")
        
        with gr.Row():
            move_dropdown = gr.Dropdown(
                label="Move",
                choices=["propose", "counter", "accept", "reject"],
                value="propose",
                scale=1
            )
            price_number = gr.Number(label="Price ($)", value=115000, scale=1)
            sla_slider = gr.Slider(label="SLA %", minimum=99.0, maximum=100.0, step=0.01, value=99.5, scale=1)
        
        with gr.Row():
            support_dropdown = gr.Dropdown(
                label="Support Tier",
                choices=["standard", "business", "premium"],
                value="standard",
                scale=1
            )
            payment_dropdown = gr.Dropdown(
                label="Payment Terms",
                choices=["net-30", "net-45", "net-60", "net-90"],
                value="net-30",
                scale=1
            )
            justification_textbox = gr.Textbox(
                label="Justification",
                lines=1,
                scale=2
            )
        
        send_btn = gr.Button("📨 Send Action", variant="primary")
    
    with gr.Group():
        gr.Markdown("## 3️⃣ Response")
        
        response_json = gr.Textbox(
            label="Full API Response (JSON)",
            lines=8,
            interactive=False,
            max_lines=16
        )
        
        with gr.Row():
            vendor_msg = gr.Textbox(label="Vendor Message", interactive=False, scale=2)
            current_offer = gr.Textbox(label="Current Offer", interactive=False, scale=1)
        
        with gr.Row():
            deal_value = gr.Number(label="Deal Value", interactive=False, value=0.0, scale=1)
            round_num = gr.Textbox(label="Round", interactive=False, scale=1)
    
    # Event handlers
    start_btn.click(
        start_negotiation,
        inputs=[task_dropdown],
        outputs=[status_textbox, session_id_state, response_json, vendor_msg, current_offer, deal_value, round_num]
    )
    
    send_btn.click(
        send_action,
        inputs=[
            session_id_state, move_dropdown, price_number, payment_dropdown,
            sla_slider, support_dropdown, justification_textbox
        ],
        outputs=[status_textbox, response_json, vendor_msg, current_offer, deal_value, round_num]
    )

# Mount Gradio at /ui
print("[INFO] Mounting Gradio UI at /ui", flush=True)
gr.mount_gradio_app(app, demo, path="/ui")

def main():
    """Main entry point for the application."""
    import uvicorn
    print("[INFO] OpenEnv API Server + Gradio UI starting on 0.0.0.0:7860", flush=True)
    print("[INFO] API Endpoints: /reset (POST), /step (POST), /state (GET), /health (GET)", flush=True)
    print("[INFO] UI available at http://localhost:7860/ui", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()
