"""
FastAPI + Gradio Procurement Negotiation OpenEnv
Single-process deployment with API and UI combined
"""

import traceback
import uuid
import json
from typing import Dict, Any, Tuple, List

from fastapi import FastAPI, HTTPException, Request
import gradio as gr
import requests

from environment import NegotiationEnvironment
from models import NegotiationAction

print("[INFO] Starting OpenEnv API Server with Gradio UI", flush=True)

# Session storage
SESSIONS: Dict[str, Dict[str, Any]] = {}

app = FastAPI(title="Procurement Negotiation OpenEnv")

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

def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_offer(offer: Any) -> Dict[str, Any]:
    if not isinstance(offer, dict):
        return {}
    return offer


def _fmt_currency(value: Any) -> str:
    return f"${_safe_float(value):,.0f}"


def _deal_summary_card(obs: Dict[str, Any]) -> str:
    offer = _safe_offer(obs.get("current_offer", {}))
    price = _fmt_currency(offer.get("price", 0))
    sla = _safe_float(offer.get("sla", 0.0))
    support = str(offer.get("support_tier", "n/a")).title()
    payment = str(offer.get("payment_terms", "n/a")).title()
    return f"""
    <div class='card'>
      <h3>Deal Summary</h3>
      <div class='metric-row'><span>Price</span><strong>{price}</strong></div>
      <div class='metric-row'><span>SLA</span><strong>{sla:.2f}%</strong></div>
      <div class='metric-row'><span>Support</span><strong>{support}</strong></div>
      <div class='metric-row'><span>Payment</span><strong>{payment}</strong></div>
    </div>
    """


def _score_card(obs: Dict[str, Any]) -> str:
    score = max(0.0, min(1.0, _safe_float(obs.get("deal_value_so_far", 0.0))))
    pct = int(score * 100)
    round_num = int(_safe_float(obs.get("round_number", 0.0), 0.0))
    if pct < 35:
        label = "Bad"
        cls = "score-bad"
    elif pct < 70:
        label = "Mid"
        cls = "score-mid"
    else:
        label = "Good"
        cls = "score-good"
    return f"""
    <div class='card'>
      <h3>Negotiation Score</h3>
      <div class='score-line'><strong>{pct}%</strong> <span>{label}</span></div>
      <div class='score-track'>
        <div class='score-fill {cls}' style='width:{pct}%;'></div>
      </div>
      <div class='muted'>Round {round_num}</div>
    </div>
    """


def _vendor_move_highlight(previous_offer: Dict[str, Any], current_offer: Dict[str, Any], vendor_response: str, vendor_message: str) -> str:
    title_map = {
        "countered": "Vendor Countered",
        "accepted": "Vendor Accepted",
        "rejected": "Vendor Rejected",
        "walkaway": "Vendor Walked Away",
        "initial": "Vendor Opened",
    }
    title = title_map.get(vendor_response, "Vendor Update")
    insights: List[str] = []

    prev_price = _safe_float(previous_offer.get("price"))
    curr_price = _safe_float(current_offer.get("price"))
    if prev_price > 0 and curr_price > 0:
        delta_pct = ((prev_price - curr_price) / prev_price) * 100
        if delta_pct > 0.05:
            insights.append(f"Dropped price by {delta_pct:.1f}%")
        elif delta_pct < -0.05:
            insights.append(f"Raised price by {abs(delta_pct):.1f}%")

    prev_sla = _safe_float(previous_offer.get("sla"))
    curr_sla = _safe_float(current_offer.get("sla"))
    if curr_sla > prev_sla:
        insights.append("Increased SLA")
    elif curr_sla < prev_sla:
        insights.append("Reduced SLA")

    prev_support = str(previous_offer.get("support_tier", "")).lower()
    curr_support = str(current_offer.get("support_tier", "")).lower()
    support_rank = {"standard": 1, "business": 2, "premium": 3}
    if support_rank.get(curr_support, 0) > support_rank.get(prev_support, 0):
        insights.append("Upgraded support")
    elif support_rank.get(curr_support, 0) < support_rank.get(prev_support, 0):
        insights.append("Downgraded support")

    insight_text = "\n".join([f"- {item}" for item in insights]) if insights else "- Adjusted terms"
    return f"{title}\n\n{insight_text}\n\n{vendor_message}".strip()


def _strategy_hint(obs: Dict[str, Any]) -> str:
    vendor_response = str(obs.get("vendor_response", "")).lower()
    offer = _safe_offer(obs.get("current_offer", {}))
    round_num = int(_safe_float(obs.get("round_number", 0.0), 0.0))
    sla = _safe_float(offer.get("sla", 99.5))
    payment = str(offer.get("payment_terms", "net-30")).lower()

    if vendor_response in {"accepted"}:
        return "Hint: Vendor accepted. Close now unless your target score is still low."
    if vendor_response in {"rejected", "walkaway"}:
        return "Hint: Recover by improving one dimension only, then re-open price on the next turn."
    if sla >= 99.8:
        return "Hint: SLA is expensive now. Trade SLA down slightly to unlock better price concessions."
    if payment in {"net-30", "net-45"}:
        return "Hint: Push payment terms to net-60 while keeping support stable for better overall value."
    if round_num >= 10:
        return "Hint: Late rounds favor closure. Tighten to one final counter and prepare to accept."
    return "Hint: Vendor is conceding incrementally. Move one lever at a time to preserve bargaining power."


def _timeline_markdown(lines: List[str]) -> str:
    if not lines:
        return "No negotiation rounds yet."
    return "\n".join([f"- {line}" for line in lines])


def _user_offer_text(move: str, price: float, sla: float, support_tier: str, payment_terms: str, note: str) -> str:
    base = (
        f"You: {move.upper()} | Price {_fmt_currency(price)} | SLA {sla:.2f}% | "
        f"Support {support_tier.title()} | {payment_terms.title()}"
    )
    if note.strip():
        return f"{base}\nNote: {note.strip()}"
    return base


def start_negotiation(task: str) -> Tuple[str, str, List[Tuple[str, str]], str, str, str, List[str], str, str]:
    """Initialize negotiation via API and render dashboard cards."""
    try:
        api_url = "http://localhost:7860"
        resp = requests.post(f"{api_url}/reset", json={"task": task}, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        session_id = data["info"]["session_id"]
        obs = data["observation"]
        current_offer = _safe_offer(obs.get("current_offer", {}))
        vendor_text = _vendor_move_highlight({}, current_offer, str(obs.get("vendor_response", "initial")), str(obs.get("vendor_message", "")))
        chat_history = [(f"Session started for {task}", vendor_text)]

        timeline = [f"Round {int(_safe_float(obs.get('round_number', 0), 0.0))}: Session initialized"]

        status = f"Session started: {session_id[:8]}..."
        return (
            status,
            session_id,
            chat_history,
            _deal_summary_card(obs),
            _score_card(obs),
            _timeline_markdown(timeline),
            timeline,
            _strategy_hint(obs),
            json.dumps(data, indent=2),
        )
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"[ERROR] start_negotiation: {error_msg}")
        return (
            error_msg,
            "",
            [],
            "<div class='card'><h3>Deal Summary</h3><div class='muted'>No active session</div></div>",
            "<div class='card'><h3>Negotiation Score</h3><div class='muted'>No score available</div></div>",
            "No negotiation rounds yet.",
            [],
            "Hint: Start a negotiation to get strategy suggestions.",
            json.dumps({"error": str(e)}, indent=2),
        )


def send_action(
    session_id: str,
    chat_history: List[Tuple[str, str]],
    timeline: List[str],
    move: str,
    price: float,
    payment_terms: str,
    sla: float,
    support_tier: str,
    note: str,
) -> Tuple[str, List[Tuple[str, str]], str, str, str, List[str], str, str]:
    """Submit action via API and update chat dashboard."""
    if not session_id:
        return (
            "No active session",
            chat_history or [],
            "<div class='card'><h3>Deal Summary</h3><div class='muted'>No active session</div></div>",
            "<div class='card'><h3>Negotiation Score</h3><div class='muted'>No score available</div></div>",
            _timeline_markdown(timeline or []),
            timeline or [],
            "Hint: Start a negotiation first.",
            json.dumps({"error": "Start negotiation first"}, indent=2),
        )

    try:
        api_url = "http://localhost:7860"
        current_history = list(chat_history or [])
        current_timeline = list(timeline or [])

        prev_offer: Dict[str, Any] = {}
        if current_history and isinstance(current_history[-1], tuple):
            pass

        action = {
            "move": move,
            "offer": {
                "price": float(price),
                "payment_terms": payment_terms,
                "sla": float(sla),
                "support_tier": support_tier,
            },
            "justification": note,
        }

        user_text = _user_offer_text(move, float(price), float(sla), support_tier, payment_terms, note)
        resp = requests.post(
            f"{api_url}/step",
            json={"session_id": session_id, "action": action},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        obs = data["observation"]
        reward = _safe_float(data.get("reward", 0.0))
        done = bool(data.get("done", False))
        offer = _safe_offer(obs.get("current_offer", {}))

        previous_offer = {
            "price": float(price),
            "sla": float(sla),
            "support_tier": support_tier,
            "payment_terms": payment_terms,
        }
        vendor_text = _vendor_move_highlight(
            previous_offer,
            offer,
            str(obs.get("vendor_response", "countered")),
            str(obs.get("vendor_message", "")),
        )

        current_history.append((user_text, vendor_text))

        round_number = int(_safe_float(obs.get("round_number", 0.0), 0.0))
        current_timeline.append(
            f"Round {round_number}: You {move.upper()} | Reward {reward:.3f} | Vendor {str(obs.get('vendor_response', '')).upper()}"
        )

        status = f"Action sent | Reward: {reward:.3f} | Done: {done}"
        if done:
            status += f" | Final Score: {_safe_float(obs.get('deal_value_so_far', 0.0)):.3f}"

        return (
            status,
            current_history,
            _deal_summary_card(obs),
            _score_card(obs),
            _timeline_markdown(current_timeline),
            current_timeline,
            _strategy_hint(obs),
            json.dumps(data, indent=2),
        )
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"[ERROR] send_action: {error_msg}")
        return (
            error_msg,
            chat_history or [],
            "<div class='card'><h3>Deal Summary</h3><div class='muted'>Last action failed</div></div>",
            "<div class='card'><h3>Negotiation Score</h3><div class='muted'>No score update</div></div>",
            _timeline_markdown(timeline or []),
            timeline or [],
            "Hint: Adjust your offer and retry.",
            json.dumps({"error": str(e)}, indent=2),
        )


def send_accept(
    session_id: str,
    chat_history: List[Tuple[str, str]],
    timeline: List[str],
    price: float,
    payment_terms: str,
    sla: float,
    support_tier: str,
) -> Tuple[str, List[Tuple[str, str]], str, str, str, List[str], str, str]:
    return send_action(session_id, chat_history, timeline, "accept", price, payment_terms, sla, support_tier, "Accepting current terms")


def send_reject(
    session_id: str,
    chat_history: List[Tuple[str, str]],
    timeline: List[str],
    price: float,
    payment_terms: str,
    sla: float,
    support_tier: str,
) -> Tuple[str, List[Tuple[str, str]], str, str, str, List[str], str, str]:
    return send_action(session_id, chat_history, timeline, "reject", price, payment_terms, sla, support_tier, "Rejecting offer")


APP_CSS = """
body { background: radial-gradient(circle at 10% 10%, #1f2937, #0f172a 45%, #020617); }
.gradio-container { max-width: 1280px !important; }
.panel { border: 1px solid rgba(148,163,184,0.25); border-radius: 16px; background: rgba(15, 23, 42, 0.8); box-shadow: 0 12px 30px rgba(0,0,0,0.28); }
.card { border: 1px solid rgba(148,163,184,0.25); border-radius: 14px; background: rgba(15, 23, 42, 0.8); padding: 14px 16px; margin-bottom: 10px; }
.card h3 { margin: 0 0 10px 0; font-size: 18px; }
.metric-row { display: flex; justify-content: space-between; margin: 7px 0; font-size: 15px; }
.muted { color: #94a3b8; font-size: 13px; margin-top: 8px; }
.score-line { display: flex; gap: 10px; align-items: baseline; margin-bottom: 8px; }
.score-track { width: 100%; height: 11px; background: rgba(148,163,184,0.25); border-radius: 999px; overflow: hidden; }
.score-fill { height: 100%; border-radius: 999px; }
.score-bad { background: linear-gradient(90deg, #ef4444, #f97316); }
.score-mid { background: linear-gradient(90deg, #eab308, #f59e0b); }
.score-good { background: linear-gradient(90deg, #22c55e, #10b981); }
"""


# Build Gradio UI
with gr.Blocks(title="Negotiation Dashboard", theme=gr.themes.Base(), css=APP_CSS) as demo:
    gr.Markdown("# Negotiation Command Center")
    gr.Markdown("Chat-style procurement negotiation with live analytics and strategy guidance.")

    session_id_state = gr.State("")
    timeline_state = gr.State([])

    with gr.Row():
        with gr.Column(scale=7, elem_classes=["panel"]):
            with gr.Row():
                task_dropdown = gr.Dropdown(
                    label="Task",
                    choices=["saas_renewal", "cloud_infra_deal", "enterprise_bundle"],
                    value="saas_renewal",
                    scale=3,
                )
                start_btn = gr.Button("Start Negotiation", variant="primary", scale=2)

            status_textbox = gr.Textbox(label="Session Status", interactive=False, lines=1)

            chatbot = gr.Chatbot(label="Negotiation Chat", height=480, bubble_full_width=False)

            gr.Markdown("### Compose Offer")
            with gr.Row():
                move_dropdown = gr.Dropdown(
                    label="Move",
                    choices=["propose", "counter"],
                    value="propose",
                    scale=1,
                )
                price_slider = gr.Slider(label="Price", minimum=70000, maximum=1300000, step=5000, value=180000, scale=3)
                price_number = gr.Number(label="Exact Price", value=180000, scale=2)

            sla_slider = gr.Slider(label="SLA %", minimum=99.0, maximum=100.0, step=0.01, value=99.5)

            support_radio = gr.Radio(
                label="Support Tier",
                choices=["standard", "business", "premium"],
                value="standard",
            )

            payment_radio = gr.Radio(
                label="Payment Terms",
                choices=["net-30", "net-45", "net-60", "net-90"],
                value="net-30",
            )

            note_box = gr.Textbox(label="Negotiation Message", placeholder="Example: We can move on SLA if you improve payment terms.", lines=2)

            with gr.Row():
                send_btn = gr.Button("Send Offer", variant="primary", scale=2)
                accept_btn = gr.Button("Accept Deal", variant="secondary", scale=1)
                reject_btn = gr.Button("Reject Deal", variant="stop", scale=1)

        with gr.Column(scale=5, elem_classes=["panel"]):
            deal_summary_html = gr.HTML("<div class='card'><h3>Deal Summary</h3><div class='muted'>Start a negotiation to view metrics.</div></div>")
            score_html = gr.HTML("<div class='card'><h3>Negotiation Score</h3><div class='muted'>No score yet.</div></div>")
            hint_markdown = gr.Markdown("Hint: Start a negotiation to get strategy suggestions.")
            timeline_markdown = gr.Markdown("No negotiation rounds yet.")
            with gr.Accordion("Technical Response (Optional)", open=False):
                response_json = gr.Textbox(label="API Response", lines=10, interactive=False)

    # Sync slider + numeric input
    price_slider.change(lambda x: x, inputs=[price_slider], outputs=[price_number])
    price_number.change(lambda x: x, inputs=[price_number], outputs=[price_slider])

    # Event handlers
    start_btn.click(
        start_negotiation,
        inputs=[task_dropdown],
        outputs=[
            status_textbox,
            session_id_state,
            chatbot,
            deal_summary_html,
            score_html,
            timeline_markdown,
            timeline_state,
            hint_markdown,
            response_json,
        ],
    )

    send_btn.click(
        send_action,
        inputs=[
            session_id_state,
            chatbot,
            timeline_state,
            move_dropdown,
            price_number,
            payment_radio,
            sla_slider,
            support_radio,
            note_box,
        ],
        outputs=[
            status_textbox,
            chatbot,
            deal_summary_html,
            score_html,
            timeline_markdown,
            timeline_state,
            hint_markdown,
            response_json,
        ],
    )

    accept_btn.click(
        send_accept,
        inputs=[
            session_id_state,
            chatbot,
            timeline_state,
            price_number,
            payment_radio,
            sla_slider,
            support_radio,
        ],
        outputs=[
            status_textbox,
            chatbot,
            deal_summary_html,
            score_html,
            timeline_markdown,
            timeline_state,
            hint_markdown,
            response_json,
        ],
    )

    reject_btn.click(
        send_reject,
        inputs=[
            session_id_state,
            chatbot,
            timeline_state,
            price_number,
            payment_radio,
            sla_slider,
            support_radio,
        ],
        outputs=[
            status_textbox,
            chatbot,
            deal_summary_html,
            score_html,
            timeline_markdown,
            timeline_state,
            hint_markdown,
            response_json,
        ],
    )

# Mount Gradio at root path
print("[INFO] Mounting Gradio UI at /", flush=True)
gr.mount_gradio_app(app, demo, path="/")

def main():
    """Main entry point for the application."""
    import uvicorn
    print("[INFO] OpenEnv API Server + Gradio UI starting on 0.0.0.0:7860", flush=True)
    print("[INFO] API Endpoints: /reset (POST), /step (POST), /state (GET), /health (GET)", flush=True)
    print("[INFO] UI available at http://localhost:7860/", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()
