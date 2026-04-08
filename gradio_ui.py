import gradio as gr
import requests
import json
from scenarios import SCENARIOS

BASE_API_URL = "http://localhost:7860"

print("[INFO] Gradio UI starting (calls FastAPI backend via HTTP)", flush=True)

def start_negotiation(task):
    """Initialize a new negotiation via API."""
    try:
        # Call /reset endpoint
        resp = requests.post(f"{BASE_API_URL}/reset", json={"task": task}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        session_id = data["info"]["session_id"]
        obs = data["observation"]
        
        # Build offer table
        offer_table = []
        scenario = SCENARIOS.get(task, {})
        buyer_targets = scenario.get("buyer_targets", {})
        current_offer = obs.get("current_offer", {})
        
        if "price" in current_offer:
            target = buyer_targets.get("price", "N/A")
            target_str = f"${target}" if isinstance(target, (int, float)) else str(target)
            offer_table.append(["Price", f"${current_offer['price']}", target_str])
        
        if "sla" in current_offer:
            target = buyer_targets.get("sla", "N/A")
            target_str = f"{target}%" if isinstance(target, (int, float)) else str(target)
            offer_table.append(["SLA", f"{current_offer['sla']}%", target_str])
        
        if "support_tier" in current_offer:
            offer_table.append(["Support", current_offer["support_tier"], buyer_targets.get("support_tier", "N/A")])
        
        if "payment_terms" in current_offer:
            offer_table.append(["Payment", current_offer["payment_terms"], buyer_targets.get("payment_terms", "N/A")])
        
        vendor_msg = obs.get("vendor_message", "Ready to negotiate")
        chatbot_history = [(None, vendor_msg)]
        
        return (
            f"✓ Negotiation started for {task}!",
            session_id,
            offer_table,
            chatbot_history,
            obs.get("deal_value_so_far", 0.0),
            str(obs.get("round_number", 0)),
            chatbot_history
        )
    except Exception as e:
        print(f"[ERROR] start_negotiation: {str(e)}")
        return (
            f"❌ Error: {str(e)}",
            "",
            [],
            [],
            0.0,
            "0",
            []
        )

def submit_offer(session_id, chat_history, move, price, sla, support, payment, justification, task):
    """Submit an offer via API."""
    if not session_id:
        return "Start negotiation first", [], chat_history or [], 0.0, "0", chat_history or []
    
    try:
        action = {
            "move": move,
            "offer": {
                "price": float(price),
                "sla": float(sla),
                "support_tier": support,
                "payment_terms": payment
            },
            "justification": justification or ""
        }
        
        resp = requests.post(
            f"{BASE_API_URL}/step",
            json={"session_id": session_id, "action": action},
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        
        obs = data["observation"]
        reward = data.get("reward", 0)
        done = data.get("done", False)
        
        # Build offer table
        offer_table = []
        scenario = SCENARIOS.get(task, {})
        buyer_targets = scenario.get("buyer_targets", {})
        current_offer = obs.get("current_offer", {})
        
        if "price" in current_offer:
            target = buyer_targets.get("price", "N/A")
            target_str = f"${target}" if isinstance(target, (int, float)) else str(target)
            offer_table.append(["Price", f"${current_offer['price']}", target_str])
        
        if "sla" in current_offer:
            target = buyer_targets.get("sla", "N/A")
            target_str = f"{target}%" if isinstance(target, (int, float)) else str(target)
            offer_table.append(["SLA", f"{current_offer['sla']}%", target_str])
        
        if "support_tier" in current_offer:
            offer_table.append(["Support", current_offer["support_tier"], buyer_targets.get("support_tier", "N/A")])
        
        if "payment_terms" in current_offer:
            offer_table.append(["Payment", current_offer["payment_terms"], buyer_targets.get("payment_terms", "N/A")])
        
        chatbot_history = chat_history or []
        user_message = f"{move.upper()} | ${price} | SLA {sla}% | {support} | {payment}"
        vendor_msg = obs.get("vendor_message", "No response")
        chatbot_history.append((user_message, vendor_msg))
        
        if done:
            status = f"✓ Negotiation Complete! | Final Score: {obs.get('deal_value_so_far', 0):.3f}"
        else:
            status = f"Offer submitted | Reward: {reward:.3f} | Round {obs.get('round_number', 0)}"
        
        return (
            status,
            offer_table,
            chatbot_history,
            obs.get("deal_value_so_far", 0.0),
            str(obs.get("round_number", 0)),
            chatbot_history
        )
    
    except Exception as e:
        print(f"[ERROR] submit_offer: {str(e)}")
        return (f"❌ Error: {str(e)}", [], chat_history or [], 0.0, "0", chat_history or [])


with gr.Blocks(title="🤝 Procurement Negotiation Agent", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🤝 Procurement Negotiation Agent")
    gr.Markdown("Negotiate across **price**, **SLA**, **support tier**, and **payment terms** to maximize deal value.")
    
    session_id_state = gr.State("")
    chat_history_state = gr.State([])
    task_state = gr.State("saas_renewal")
    
    with gr.Row():
        with gr.Column(scale=1):
            task_dropdown = gr.Dropdown(
                label="Select Task",
                choices=["saas_renewal", "cloud_infra_deal", "enterprise_bundle"],
                value="saas_renewal"
            )
            start_button = gr.Button("🚀 Start Negotiation", variant="primary", size="lg")
        
        with gr.Column(scale=2):
            status_textbox = gr.Textbox(label="Status", interactive=False)
    
    with gr.Row():
        offer_dataframe = gr.DataFrame(
            label="Current Offer vs. Your Targets",
            headers=["Dimension", "Vendor Offer", "Your Target"],
            interactive=False,
            row_count=5
        )
    
    gr.Markdown("## Submit Your Next Move")
    
    with gr.Row():
        with gr.Column(scale=1):
            move_dropdown = gr.Dropdown(
                label="Move Type",
                choices=["propose", "counter", "accept", "reject"],
                value="propose"
            )
        with gr.Column(scale=1):
            price_number = gr.Number(label="Price ($)", value=115000, minimum=0)
        with gr.Column(scale=1):
            sla_slider = gr.Slider(label="SLA %", minimum=99.0, maximum=100.0, step=0.01, value=99.5)
    
    with gr.Row():
        with gr.Column(scale=1):
            support_dropdown = gr.Dropdown(
                label="Support Tier",
                choices=["standard", "business", "premium"],
                value="standard"
            )
        with gr.Column(scale=1):
            payment_dropdown = gr.Dropdown(
                label="Payment Terms",
                choices=["net-30", "net-45", "net-60", "net-90"],
                value="net-30"
            )
        with gr.Column(scale=2):
            justification_textbox = gr.Textbox(
                label="Justification (Optional)",
                lines=1,
                placeholder="Explain your reasoning..."
            )
    
    submit_button = gr.Button("📨 Submit Offer", variant="primary", size="lg")
    
    with gr.Row():
        chatbot = gr.Chatbot(label="Negotiation History", height=250)
    
    with gr.Row():
        deal_slider = gr.Slider(
            label="Deal Value (Score)",
            minimum=0.0,
            maximum=1.0,
            interactive=False,
            value=0.0
        )
        round_textbox = gr.Textbox(label="Round", interactive=False, scale=1)
    
    # Event handlers
    def on_task_change(task):
        task_state.value = task
        return task
    
    task_dropdown.change(on_task_change, inputs=[task_dropdown], outputs=[task_state])
    
    start_button.click(
        start_negotiation,
        inputs=[task_dropdown],
        outputs=[status_textbox, session_id_state, offer_dataframe, chatbot, deal_slider, round_textbox, chat_history_state]
    )
    
    submit_button.click(
        submit_offer,
        inputs=[
            session_id_state, chat_history_state, move_dropdown, price_number,
            sla_slider, support_dropdown, payment_dropdown, justification_textbox, task_dropdown
        ],
        outputs=[status_textbox, offer_dataframe, chatbot, deal_slider, round_textbox, chat_history_state]
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)