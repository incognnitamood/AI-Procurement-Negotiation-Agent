import gradio as gr
import traceback
from environment import NegotiationEnvironment
from models import NegotiationAction
from scenarios import SCENARIOS

print("[INFO] Gradio UI starting (single-process, direct environment calls)", flush=True)

def start_negotiation(task, session_state, chat_history):
    """Initialize a new negotiation environment."""
    if session_state:
        return "Session already active", session_state, [], chat_history or [], 0.0, "0", chat_history or []
    
    try:
        # Create environment and reset
        env = NegotiationEnvironment()
        obs = env.reset(task)
        
        # Store environment in session state
        session_data = {
            "env": env,
            "task": task,
        }
        
        # Get buyer targets from scenario
        scenario = SCENARIOS.get(task, {})
        buyer_targets = scenario.get("buyer_targets", {})
        
        # Build offer table
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
        
        return "Negotiation started successfully!", session_data, offer_table, chatbot_history, 0.0, str(obs.round_number), chatbot_history
    
    except Exception as e:
        error_msg = f"Error starting negotiation: {str(e)}"
        print(f"ERROR: {error_msg}\n{traceback.format_exc()}")
        return error_msg, None, [], [], 0.0, "0", []

def submit_offer(session_state, chat_history, move, price, sla, support, payment, justification, task):
    """Submit an offer and get vendor response."""
    if not session_state:
        return "Start negotiation first", [], chat_history or [], 0.0, "0", chat_history or []
    
    try:
        env = session_state["env"]
        
        # Create action
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
        
        # Execute step directly
        obs, reward, done, info = env.step(action)
        
        # Get buyer targets from scenario
        scenario = SCENARIOS.get(task, {})
        buyer_targets = scenario.get("buyer_targets", {})
        
        # Build offer table
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
        
        # Add user and vendor messages
        user_message = f"{move.capitalize()} | ${price} | SLA {sla}% | {support} | {payment}"
        vendor_msg = obs.vendor_message
        chatbot_history.append((user_message, vendor_msg))
        
        # Update deal value
        deal_value = obs.deal_value_so_far
        round_num = str(obs.round_number)
        
        # Determine status
        if done:
            vendor_response = obs.vendor_response
            if vendor_response == "accepted":
                status = "Deal signed successfully!"
            else:
                status = "Negotiation ended"
        else:
            status = "Offer submitted, waiting for vendor response..."
        
        return status, offer_table, chatbot_history, deal_value, round_num, chatbot_history
    
    except Exception as e:
        error_msg = f"Error submitting offer: {str(e)}"
        print(f"ERROR: {error_msg}\n{traceback.format_exc()}")
        return error_msg, [], chat_history or [], 0.0, "0", chat_history or []


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