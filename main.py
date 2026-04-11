"""
FastAPI + Gradio Procurement Negotiation OpenEnv
Single-process deployment with API and UI combined
"""

import traceback
import uuid
import json
from typing import Dict, Any, Tuple, List
from datetime import datetime

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


def _now_stamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _delta_arrow(current: Any, previous: Any, higher_is_better: bool = False) -> str:
    curr = _safe_float(current)
    prev = _safe_float(previous)
    if prev <= 0 and curr <= 0:
        return ""
    if abs(curr - prev) < 1e-9:
        return ""
    if curr > prev:
        return "↑" if higher_is_better else "↑"
    return "↓"


def _deal_summary_card(obs: Dict[str, Any], previous_offer: Dict[str, Any]) -> str:
    offer = _safe_offer(obs.get("current_offer", {}))
    price = _fmt_currency(offer.get("price", 0))
    sla = _safe_float(offer.get("sla", 0.0))
    support = str(offer.get("support_tier", "n/a")).title()
    payment = str(offer.get("payment_terms", "n/a")).title()
    price_delta = _delta_arrow(offer.get("price"), previous_offer.get("price"), higher_is_better=False)
    sla_delta = _delta_arrow(offer.get("sla"), previous_offer.get("sla"), higher_is_better=True)
    support_delta = ""
    prev_support = str(previous_offer.get("support_tier", "")).lower()
    curr_support = str(offer.get("support_tier", "")).lower()
    support_rank = {"standard": 1, "business": 2, "premium": 3}
    if support_rank.get(curr_support, 0) > support_rank.get(prev_support, 0):
        support_delta = "↑"
    elif support_rank.get(curr_support, 0) < support_rank.get(prev_support, 0):
        support_delta = "↓"

    payment_delta = ""
    term_rank = {"net-30": 1, "net-45": 2, "net-60": 3, "net-90": 4}
    prev_pay = str(previous_offer.get("payment_terms", "")).lower()
    curr_pay = str(offer.get("payment_terms", "")).lower()
    if term_rank.get(curr_pay, 0) > term_rank.get(prev_pay, 0):
        payment_delta = "↑"
    elif term_rank.get(curr_pay, 0) < term_rank.get(prev_pay, 0):
        payment_delta = "↓"

    return f"""
    <div class='card'>
      <h3>Deal Summary</h3>
      <div class='metric-row'><span>Price</span><strong>{price} <span class='delta'>{price_delta}</span></strong></div>
      <div class='metric-row'><span>SLA</span><strong>{sla:.2f}% <span class='delta'>{sla_delta}</span></strong></div>
      <div class='metric-row'><span>Support</span><strong>{support} <span class='delta'>{support_delta}</span></strong></div>
      <div class='metric-row'><span>Payment</span><strong>{payment} <span class='delta'>{payment_delta}</span></strong></div>
    </div>
    """


def _score_card(obs: Dict[str, Any]) -> str:
    score = max(0.0, min(1.0, _safe_float(obs.get("deal_value_so_far", 0.0))))
    pct = int(score * 100)
    round_num = int(_safe_float(obs.get("round_number", 0.0), 0.0))
    if pct < 30:
        label = "Poor deal"
        cls = "score-bad"
    elif pct < 70:
        label = "Fair deal"
        cls = "score-mid"
    else:
        label = "Great deal"
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


def _vendor_behavior_insight(previous_offer: Dict[str, Any], current_offer: Dict[str, Any], vendor_response: str) -> str:
    insights: List[str] = []
    prev_price = _safe_float(previous_offer.get("price"))
    curr_price = _safe_float(current_offer.get("price"))
    prev_sla = _safe_float(previous_offer.get("sla"))
    curr_sla = _safe_float(current_offer.get("sla"))
    term_rank = {"net-30": 1, "net-45": 2, "net-60": 3, "net-90": 4}
    prev_term = term_rank.get(str(previous_offer.get("payment_terms", "")).lower(), 0)
    curr_term = term_rank.get(str(current_offer.get("payment_terms", "")).lower(), 0)

    if prev_price > 0 and curr_price > 0:
        delta_pct = ((prev_price - curr_price) / prev_price) * 100
        if delta_pct > 3:
            insights.append("Flexible on price")
        elif delta_pct < 1:
            insights.append("Resistant on price")

    if curr_sla > prev_sla:
        insights.append("Flexible on SLA")
    elif curr_sla <= prev_sla and vendor_response == "countered":
        insights.append("Holding SLA firm")

    if curr_term > prev_term:
        insights.append("Prefers longer payment cycles")
    elif curr_term < prev_term:
        insights.append("Open to faster payment")

    if not insights:
        insights.append("Testing your negotiation boundary")

    return "Vendor Insight:\n\n" + "\n".join([f"- {item}" for item in insights])


def _round_progress(round_num: int, max_rounds: int) -> str:
    round_num = max(0, min(max_rounds, round_num))
    active = round_num if round_num > 0 else 1
    nodes = []
    for idx in range(1, max_rounds + 1):
        cls = "node active" if idx <= active else "node"
        nodes.append(f"<span class='{cls}'></span>")
    return (
        "<div class='card'>"
        "<h3>Round Progress</h3>"
        f"<div class='round-track'>{''.join(nodes)}</div>"
        f"<div class='muted'>Round {round_num} of {max_rounds}</div>"
        "</div>"
    )


def _suggested_move(obs: Dict[str, Any]) -> str:
    offer = _safe_offer(obs.get("current_offer", {}))
    price = _safe_float(offer.get("price", 0.0))
    sla = _safe_float(offer.get("sla", 99.5))
    payment = str(offer.get("payment_terms", "net-30")).lower()
    suggested_price = max(70000.0, price * 0.95)
    next_payment = "net-60" if payment in {"net-30", "net-45"} else payment
    return (
        "Recommended Move:\n"
        f"- Lower price to {_fmt_currency(suggested_price)}\n"
        f"- Push payment to {next_payment}\n"
        f"- Keep SLA near {sla:.2f}%\n"
        "- Keep support unchanged for leverage"
    )


def suggest_best_move(last_obs: Dict[str, Any], current_hint: str) -> str:
    if not last_obs:
        return "Hint: Start a negotiation first."
    return current_hint + "\n\n" + _suggested_move(last_obs)


def _timeline_markdown(lines: List[str]) -> str:
    if not lines:
        return "No negotiation rounds yet."
    return "\n".join([f"- {line}" for line in lines])


def _user_offer_text(move: str, price: float, sla: float, support_tier: str, payment_terms: str, note: str) -> str:
    stamp = _now_stamp()
    base = (
        f"[{stamp}] You\n"
        f"Offering {_fmt_currency(price)}, {payment_terms.title()}, {support_tier.title()} support, SLA {sla:.2f}%\n"
        f"Move: {move.upper()}"
    )
    if note.strip():
        return f"{base}\nMessage: {note.strip()}"
    return base


def _sync_slider_to_number(slider_value: float, number_value: float):
    slider_int = int(round(_safe_float(slider_value, 0.0)))
    number_int = int(round(_safe_float(number_value, 0.0)))
    if slider_int == number_int:
        return gr.update()
    return slider_int


def _sync_number_to_slider(number_value: float, slider_value: float):
    number_int = int(round(_safe_float(number_value, 0.0)))
    slider_int = int(round(_safe_float(slider_value, 0.0)))
    if number_int == slider_int:
        return gr.update()
    return number_int


def start_negotiation(task: str) -> Tuple[str, str, List[Tuple[str, str]], str, str, str, List[str], str, str, str, Dict[str, Any]]:
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
        vendor_chat = f"[{_now_stamp()}] Vendor\n{vendor_text}"
        chat_history = [(f"[{_now_stamp()}] You\nLet's negotiate this {task} deal.", vendor_chat)]

        timeline = [f"Round {int(_safe_float(obs.get('round_number', 0), 0.0))}: Session initialized"]
        max_rounds = {"saas_renewal": 8, "cloud_infra_deal": 12, "enterprise_bundle": 18}.get(task, 12)
        insight = _vendor_behavior_insight({}, current_offer, str(obs.get("vendor_response", "initial")).lower())

        status = f"Session started: {session_id[:8]}..."
        return (
            status,
            session_id,
            chat_history,
            _deal_summary_card(obs, {}),
            _score_card(obs),
            _timeline_markdown(timeline),
            timeline,
            _strategy_hint(obs),
            insight,
            _round_progress(int(_safe_float(obs.get("round_number", 0.0), 0.0)), max_rounds),
            json.dumps(data, indent=2),
            obs,
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
            "Vendor Insight:\n\n- No active signal yet.",
            "<div class='card'><h3>Round Progress</h3><div class='muted'>No round yet.</div></div>",
            json.dumps({"error": str(e)}, indent=2),
            {},
        )


def send_action(
    session_id: str,
    chat_history: List[Tuple[str, str]],
    timeline: List[str],
    last_obs: Dict[str, Any],
    task: str,
    move: str,
    price: float,
    payment_terms: str,
    sla: float,
    support_tier: str,
    note: str,
) -> Tuple[str, List[Tuple[str, str]], str, str, str, List[str], str, str, str, Dict[str, Any]]:
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
            "Vendor Insight:\n\n- Start a session to infer behavior.",
            "<div class='card'><h3>Round Progress</h3><div class='muted'>No round yet.</div></div>",
            json.dumps({"error": "Start negotiation first"}, indent=2),
            last_obs or {},
        )

    try:
        api_url = "http://localhost:7860"
        current_history = list(chat_history or [])
        current_timeline = list(timeline or [])
        previous_offer = _safe_offer((last_obs or {}).get("current_offer", {}))

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

        vendor_text = _vendor_move_highlight(
            previous_offer,
            offer,
            str(obs.get("vendor_response", "countered")),
            str(obs.get("vendor_message", "")),
        )
        vendor_chat = f"[{_now_stamp()}] Vendor\n{vendor_text}"

        current_history.append((user_text, vendor_chat))

        round_number = int(_safe_float(obs.get("round_number", 0.0), 0.0))
        current_timeline.append(
            f"Round {round_number}: You {move.upper()} | Reward {reward:.3f} | Vendor {str(obs.get('vendor_response', '')).upper()}"
        )

        status = f"Action sent | Reward: {reward:.3f} | Done: {done}"
        if done:
            status += f" | Final Score: {_safe_float(obs.get('deal_value_so_far', 0.0)):.3f}"

        max_rounds = {"saas_renewal": 8, "cloud_infra_deal": 12, "enterprise_bundle": 18}.get(task, 12)
        insight = _vendor_behavior_insight(previous_offer, offer, str(obs.get("vendor_response", "")).lower())

        return (
            status,
            current_history,
            _deal_summary_card(obs, previous_offer),
            _score_card(obs),
            _timeline_markdown(current_timeline),
            current_timeline,
            _strategy_hint(obs),
            insight,
            _round_progress(round_number, max_rounds),
            json.dumps(data, indent=2),
            obs,
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
            "Vendor Insight:\n\n- Unable to infer behavior from failed action.",
            "<div class='card'><h3>Round Progress</h3><div class='muted'>No update.</div></div>",
            json.dumps({"error": str(e)}, indent=2),
            last_obs or {},
        )


def send_accept(
    session_id: str,
    chat_history: List[Tuple[str, str]],
    timeline: List[str],
    last_obs: Dict[str, Any],
    task: str,
    price: float,
    payment_terms: str,
    sla: float,
    support_tier: str,
) -> Tuple[str, List[Tuple[str, str]], str, str, str, List[str], str, str, str, Dict[str, Any]]:
    return send_action(session_id, chat_history, timeline, last_obs, task, "accept", price, payment_terms, sla, support_tier, "Accepting current terms")


def send_reject(
    session_id: str,
    chat_history: List[Tuple[str, str]],
    timeline: List[str],
    last_obs: Dict[str, Any],
    task: str,
    price: float,
    payment_terms: str,
    sla: float,
    support_tier: str,
) -> Tuple[str, List[Tuple[str, str]], str, str, str, List[str], str, str, str, Dict[str, Any]]:
    return send_action(session_id, chat_history, timeline, last_obs, task, "reject", price, payment_terms, sla, support_tier, "Rejecting offer")


APP_CSS = """
body { background: radial-gradient(circle at 10% 10%, #1f2937, #0f172a 45%, #020617); }
.gradio-container { max-width: 1280px !important; }
.panel { border: 1px solid rgba(148,163,184,0.25); border-radius: 16px; background: rgba(15, 23, 42, 0.8); box-shadow: 0 12px 30px rgba(0,0,0,0.28); }
.card { border: 1px solid rgba(148,163,184,0.25); border-radius: 14px; background: rgba(15, 23, 42, 0.8); padding: 14px 16px; margin-bottom: 10px; }
.card h3 { margin: 0 0 10px 0; font-size: 18px; }
.metric-row { display: flex; justify-content: space-between; margin: 7px 0; font-size: 15px; }
.delta { font-size: 14px; color: #38bdf8; }
.muted { color: #94a3b8; font-size: 13px; margin-top: 8px; }
.score-line { display: flex; gap: 10px; align-items: baseline; margin-bottom: 8px; }
.score-track { width: 100%; height: 11px; background: rgba(148,163,184,0.25); border-radius: 999px; overflow: hidden; }
.score-fill { height: 100%; border-radius: 999px; transition: width 0.45s ease-in-out; }
.score-bad { background: linear-gradient(90deg, #dc2626, #f97316); }
.score-mid { background: linear-gradient(90deg, #f59e0b, #facc15); }
.score-good { background: linear-gradient(90deg, #22c55e, #10b981); }
.round-track { display: flex; gap: 8px; margin-top: 8px; }
.node { width: 12px; height: 12px; border-radius: 50%; background: rgba(148,163,184,0.35); display: inline-block; }
.node.active { background: linear-gradient(135deg, #0ea5e9, #22c55e); box-shadow: 0 0 12px rgba(56, 189, 248, 0.6); }
.message { animation: fadeUp 0.35s ease; }
#accept-btn { background: #15803d !important; color: white !important; border-color: #22c55e !important; }
#accept-btn:hover { filter: brightness(1.08); transform: translateY(-1px); }
#reject-btn { background: #b91c1c !important; color: white !important; border-color: #ef4444 !important; }
#reject-btn:hover { filter: brightness(1.08); transform: translateY(-1px); }
#send-btn:hover, #accept-btn:hover, #reject-btn:hover { transition: all 0.2s ease; }
@keyframes fadeUp {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: translateY(0); }
}
"""


# Build Gradio UI
with gr.Blocks(title="Negotiation Dashboard", theme=gr.themes.Base(), css=APP_CSS) as demo:
    gr.Markdown("# Negotiation Command Center")
    gr.Markdown("Chat-style procurement negotiation with live analytics and strategy guidance.")

    session_id_state = gr.State("")
    timeline_state = gr.State([])
    task_state = gr.State("saas_renewal")
    last_obs_state = gr.State({})

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

            chatbot = gr.Chatbot(label="Negotiation Chat", height=480, bubble_full_width=False, elem_classes=["message"])

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
                send_btn = gr.Button("Send Offer", variant="primary", scale=2, elem_id="send-btn")
                accept_btn = gr.Button("Accept Deal", variant="secondary", scale=1, elem_id="accept-btn")
                reject_btn = gr.Button("Reject Deal", variant="stop", scale=1, elem_id="reject-btn")
                suggest_btn = gr.Button("Suggest Best Move", variant="secondary", scale=2)

        with gr.Column(scale=5, elem_classes=["panel"]):
            deal_summary_html = gr.HTML("<div class='card'><h3>Deal Summary</h3><div class='muted'>Start a negotiation to view metrics.</div></div>")
            score_html = gr.HTML("<div class='card'><h3>Negotiation Score</h3><div class='muted'>No score yet.</div></div>")
            hint_markdown = gr.Markdown("Hint: Start a negotiation to get strategy suggestions.")
            behavior_markdown = gr.Markdown("Vendor Insight:\n\n- Start a negotiation to infer behavior.")
            round_progress_html = gr.HTML("<div class='card'><h3>Round Progress</h3><div class='muted'>No round yet.</div></div>")
            timeline_markdown = gr.Markdown("No negotiation rounds yet.")
            with gr.Accordion("Advanced / Debug", open=False):
                response_json = gr.Textbox(label="API Response", lines=10, interactive=False)

    # Sync slider + numeric input without circular update loops
    price_slider.change(_sync_slider_to_number, inputs=[price_slider, price_number], outputs=[price_number])
    price_number.change(_sync_number_to_slider, inputs=[price_number, price_slider], outputs=[price_slider])

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
            behavior_markdown,
            round_progress_html,
            response_json,
            last_obs_state,
        ],
    )

    start_btn.click(lambda t: t, inputs=[task_dropdown], outputs=[task_state])

    send_btn.click(
        send_action,
        inputs=[
            session_id_state,
            chatbot,
            timeline_state,
            last_obs_state,
            task_state,
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
            behavior_markdown,
            round_progress_html,
            response_json,
            last_obs_state,
        ],
    )

    accept_btn.click(
        send_accept,
        inputs=[
            session_id_state,
            chatbot,
            timeline_state,
            last_obs_state,
            task_state,
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
            behavior_markdown,
            round_progress_html,
            response_json,
            last_obs_state,
        ],
    )

    reject_btn.click(
        send_reject,
        inputs=[
            session_id_state,
            chatbot,
            timeline_state,
            last_obs_state,
            task_state,
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
            behavior_markdown,
            round_progress_html,
            response_json,
            last_obs_state,
        ],
    )

    suggest_btn.click(
        suggest_best_move,
        inputs=[last_obs_state, hint_markdown],
        outputs=[hint_markdown],
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
