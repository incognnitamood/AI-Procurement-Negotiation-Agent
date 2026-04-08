import gradio as gr
import requests
import uuid
import json
from scenarios import SCENARIOS

def start_negotiation(task, session_id, chat_history):
    if session_id:
        return "Already started", session_id, [], chat_history or [], 0.0, "0", chat_history or []
    
    new_session_id = str(uuid.uuid4())
    response = requests.post("http://localhost:8000/reset", json={"task": task, "session_id": new_session_id})
    if response.status_code != 200:
        return f"Error: {response.text}", None, [], [], 0.0, "0", []
    
    data = response.json()
    obs = data["observation"]
    
    # Get buyer targets from scenario
    scenario = SCENARIOS.get(task, {})
    buyer_targets = scenario.get("buyer_targets", {})
    
    # Prepopulate offer table with actual targets
    offer_table = []
    current_offer = obs["current_offer"]
    if "price" in current_offer:
        target_price = buyer_targets.get("price", "N/A")
        if target_price != "N/A":
            target_str = f"${target_price}"
        else:
            target_str = str(target_price)
        offer_table.append(["Price", f"${current_offer['price']}", target_str])
    if "sla" in current_offer:
        target_sla = buyer_targets.get("sla", "N/A")
        if target_sla != "N/A":
            target_str = f"{target_sla}%"
        else:
            target_str = str(target_sla)
        offer_table.append(["SLA", f"{current_offer['sla']}%", target_str])
    if "support_tier" in current_offer:
        target_support = buyer_targets.get("support_tier", "N/A")
        offer_table.append(["Support", current_offer["support_tier"], str(target_support)])
    if "payment_terms" in current_offer:
        target_payment = buyer_targets.get("payment_terms", "N/A")
        offer_table.append(["Payment", current_offer["payment_terms"], str(target_payment)])
    
    chatbot_history = [{"role": "assistant", "content": obs["vendor_message"]}]
    return "Negotiation started", new_session_id, offer_table, chatbot_history, 0.0, str(obs["round_number"]), chatbot_history

def submit_offer(session_id, chat_history, move, price, sla, support, payment, justification, task):
    if not session_id:
        return "Start negotiation first", [], chat_history or [], 0.0, "0", chat_history or []
    
    action = {
        "move": move,
        "offer": {
            "price": price,
            "sla": sla,
            "support_tier": support,
            "payment_terms": payment
        },
        "justification": justification
    }
    
    response = requests.post("http://localhost:8000/step", json={"session_id": session_id, "action": action})
    if response.status_code != 200:
        return f"Error: {response.text}", [], chat_history or [], 0.0, "0", chat_history or []
    
    data = response.json()
    obs = data["observation"]
    
    # Get buyer targets from scenario
    scenario = SCENARIOS.get(task, {})
    buyer_targets = scenario.get("buyer_targets", {})
    
    # Update offer table with actual targets
    offer_table = []
    current_offer = obs["current_offer"]
    if "price" in current_offer:
        target_price = buyer_targets.get("price", "N/A")
        if target_price != "N/A":
            target_str = f"${target_price}"
        else:
            target_str = str(target_price)
        offer_table.append(["Price", f"${current_offer['price']}", target_str])
    if "sla" in current_offer:
        target_sla = buyer_targets.get("sla", "N/A")
        if target_sla != "N/A":
            target_str = f"{target_sla}%"
        else:
            target_str = str(target_sla)
        offer_table.append(["SLA", f"{current_offer['sla']}%", target_str])
    if "support_tier" in current_offer:
        target_support = buyer_targets.get("support_tier", "N/A")
        offer_table.append(["Support", current_offer["support_tier"], str(target_support)])
    if "payment_terms" in current_offer:
        target_payment = buyer_targets.get("payment_terms", "N/A")
        offer_table.append(["Payment", current_offer["payment_terms"], str(target_payment)])
    
    chatbot_history = chat_history or []
    user_message = f"{move.capitalize()} | ${price} | SLA {sla}% | {support} | {payment}"
    chatbot_history.append({"role": "user", "content": user_message})
    chatbot_history.append({"role": "assistant", "content": obs["vendor_message"]})

    
    # Update deal value and round
    deal_value = obs["deal_value_so_far"]
    round_num = str(obs["round_number"])
    
    # Check if done
    if data["done"]:
        if obs["vendor_response"] == "accepted":
            status = "✅ DEAL SIGNED!"
        else:
            status = "❌ NEGOTIATION COLLAPSED"
    else:
        status = "Continue negotiating"
    
    return status, offer_table, chatbot_history, deal_value, round_num, chatbot_history

with gr.Blocks(title="🤝 Procurement Negotiation Simulator") as demo:
    gr.Markdown("# 🤝 Procurement Negotiation Simulator")
    
    with gr.Row():
        task_dropdown = gr.Dropdown(label="Select Task", choices=["saas_renewal", "cloud_infra_deal", "enterprise_bundle"], value="saas_renewal")
        start_button = gr.Button("🚀 Start Negotiation")
        status_textbox = gr.Textbox(label="Status", interactive=False)
        session_state = gr.State()
        chatbot_history_state = gr.State([])
    
    with gr.Row():
        offer_dataframe = gr.DataFrame(label="Current Offer", headers=["Dimension", "Vendor Offer", "Your Target"], interactive=False)
    
    with gr.Row():
        move_dropdown = gr.Dropdown(label="Move Type", choices=["propose", "counter", "accept", "reject"], value="propose")
        price_number = gr.Number(label="Price ($)", value=115000)
        sla_slider = gr.Slider(label="SLA %", minimum=99.0, maximum=100.0, step=0.01, value=99.5)
        support_dropdown = gr.Dropdown(label="Support Tier", choices=["standard", "business", "premium"], value="standard")
        payment_dropdown = gr.Dropdown(label="Payment Terms", choices=["net-30", "net-60", "net-90"], value="net-30")
        justification_textbox = gr.Textbox(label="Justification — explain your reasoning")
        submit_button = gr.Button("📨 Submit Offer")
    
    with gr.Row():
        chatbot = gr.Chatbot(label="Negotiation Log", height=300)
    
    with gr.Row():
        deal_slider = gr.Slider(label="Deal Value", minimum=0.0, maximum=1.0, interactive=False, value=0.0)
        round_textbox = gr.Textbox(label="Round", interactive=False)

    start_button.click(
        start_negotiation,
        inputs=[task_dropdown, session_state, chatbot_history_state],
        outputs=[status_textbox, session_state, offer_dataframe, chatbot, deal_slider, round_textbox, chatbot_history_state]
    )
    
    submit_button.click(
        submit_offer,
        inputs=[session_state, chatbot_history_state, move_dropdown, price_number, sla_slider, support_dropdown, payment_dropdown, justification_textbox, task_dropdown],
        outputs=[status_textbox, offer_dataframe, chatbot, deal_slider, round_textbox, chatbot_history_state]
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)