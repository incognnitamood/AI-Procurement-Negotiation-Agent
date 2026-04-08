import gradio as gr
import requests
import uuid
import json
import traceback
import os
import time
from scenarios import SCENARIOS

# Configure connection details - allow override via environment variable
API_URL = os.getenv("API_URL", "http://localhost:8000")
MAX_RETRIES = 10
RETRY_DELAY = 0.5

print(f"[INFO] Gradio UI initialized. Using API_URL: {API_URL}")

def _retry_request(method, url, **kwargs):
    """Retry a request with exponential backoff."""
    for attempt in range(MAX_RETRIES):
        try:
            if method.lower() == "post":
                return requests.post(url, **kwargs)
            elif method.lower() == "get":
                return requests.get(url, **kwargs)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            if attempt == MAX_RETRIES - 1:
                # Last attempt failed, raise the error
                print(f"[ERROR] Final attempt failed after {MAX_RETRIES} retries: {str(e)}")
                raise
            
            wait_time = RETRY_DELAY * (2 ** attempt)  # Exponential backoff: 0.5s, 1s, 2s, 4s, 8s, etc.
            print(f"[RETRY] Attempt {attempt + 1}/{MAX_RETRIES} failed, retrying in {wait_time}s... (Error: {type(e).__name__})")
            time.sleep(wait_time)
    return None

def start_negotiation(task, session_id, chat_history):
    if session_id:
        return "Session already active", session_id, [], chat_history or [], 0.0, "0", chat_history or []
    
    try:
        new_session_id = str(uuid.uuid4())
        payload = {"task": task, "session_id": new_session_id}
        
        # Use retry logic
        response = _retry_request(
            "post",
            f"{API_URL}/reset",
            json=payload,
            timeout=10
        )
        
        if not response or response.status_code != 200:
            error_msg = f"Server error ({response.status_code if response else 'No response'}): {response.text if response else 'No response'}"
            print(f"ERROR in start_negotiation: {error_msg}")
            return error_msg, None, [], [], 0.0, "0", []
        
        data = response.json()
        obs = data.get("observation", {})
        
        # Get buyer targets from scenario
        scenario = SCENARIOS.get(task, {})
        buyer_targets = scenario.get("buyer_targets", {})
        
        # Prepopulate offer table with actual targets
        offer_table = []
        current_offer = obs.get("current_offer", {})
        
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
        
        vendor_msg = obs.get("vendor_message", "Negotiation started")
        # Gradio chatbot expects tuples: [(user_msg, assistant_msg), ...]
        chatbot_history = [(None, vendor_msg)]
        
        return "Negotiation started successfully!", new_session_id, offer_table, chatbot_history, 0.0, str(obs.get("round_number", 0)), chatbot_history
    
    except requests.exceptions.ConnectionError as e:
        error_msg = f"Cannot connect to server at {API_URL}. Is the FastAPI server running? Try waiting 5 seconds and refresh the page."
        print(f"ERROR: {error_msg}\n{traceback.format_exc()}")
        return error_msg, None, [], [], 0.0, "0", []
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"ERROR in start_negotiation: {error_msg}\n{traceback.format_exc()}")
        return error_msg, None, [], [], 0.0, "0", []

def submit_offer(session_id, chat_history, move, price, sla, support, payment, justification, task):
    if not session_id:
        return "Start negotiation first", [], chat_history or [], 0.0, "0", chat_history or []
    
    try:
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
        
        # Use retry logic
        response = _retry_request(
            "post",
            f"{API_URL}/step",
            json={"session_id": session_id, "action": action},
            timeout=10
        )
        
        if not response or response.status_code != 200:
            error_msg = f"Server error ({response.status_code if response else 'No response'}): {response.text if response else 'No response'}"
            print(f"ERROR in submit_offer: {error_msg}")
            return error_msg, [], chat_history or [], 0.0, "0", chat_history or []
        
        data = response.json()
        obs = data.get("observation", {})
        
        # Get buyer targets from scenario
        scenario = SCENARIOS.get(task, {})
        buyer_targets = scenario.get("buyer_targets", {})
        
        # Update offer table with actual targets
        offer_table = []
        current_offer = obs.get("current_offer", {})
        
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
        
        # Add user and vendor messages to chatbot (as tuples for Gradio)
        user_message = f"{move.capitalize()} | ${price} | SLA {sla}% | {support} | {payment}"
        vendor_msg = obs.get("vendor_message", "Offer received")
        chatbot_history.append((user_message, vendor_msg))
        
        # Update deal value and round
        deal_value = obs.get("deal_value_so_far", 0.0)
        round_num = str(obs.get("round_number", 0))
        
        # Check if done
        if data.get("done", False):
            vendor_response = obs.get("vendor_response", "")
            if vendor_response == "accepted":
                status = "Deal signed successfully!"
            else:
                status = "Negotiation ended"
        else:
            status = "Offer submitted, waiting for vendor response..."
        
        return status, offer_table, chatbot_history, deal_value, round_num, chatbot_history
    
    except requests.exceptions.ConnectionError as e:
        error_msg = f"Connection error: Cannot reach server at {API_URL}. The server may have crashed."
        print(f"ERROR: {error_msg}\n{traceback.format_exc()}")
        return error_msg, [], chat_history or [], 0.0, "0", chat_history or []
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"ERROR in submit_offer: {error_msg}\n{traceback.format_exc()}")
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