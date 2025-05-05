import os, json, re
from dotenv import load_dotenv
from datetime import datetime
from rich.console import Console
from rich.prompt import Prompt
import requests

load_dotenv()
console = Console()

API_KEY = os.getenv("OPENROUTER_API_KEY")
REQUIRED_FIELDS = ["name", "check_in", "check_out", "guests", "breakfast", "payment_method"]
BOT_NAME, HOTEL_NAME, LOCATION = "Felix", "Hotel Berlin International", "Berlin"
CURRENT_TIME = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def chat_api(messages):
    res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers={
        "Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"
    }, json={
        "model": "openai/gpt-3.5-turbo", "messages": messages, "temperature": 0.7
    })
    return res.json()["choices"][0]["message"]["content"]

def check_info_complete(messages):
    response = chat_api(messages + [{"role": "user", "content": "Have we collected all booking details? Reply only INFO_COLLECTED or NEED_MORE_INFO."}])
    return "INFO_COLLECTED" in response

def extract_booking_json(messages):
    response = chat_api(messages + [{"role": "user", "content": "Please return the final booking data in JSON only."}])
    match = re.search(r'{.*}', response.replace("\n", ""), re.DOTALL)
    if not match: return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None

def is_valid_booking(data):
    if not isinstance(data, dict): return False
    for key in REQUIRED_FIELDS:
        if key not in data or data[key] in [None, "", "unknown", "not specified", "provided"]:
            return False
    return True

def run_chatbot():
    if not API_KEY:
        console.print("[red]Missing OPENROUTER_API_KEY[/red]"); return

    messages = [{
        "role": "system",
        "content": f"You are {BOT_NAME}, a hotel assistant at {HOTEL_NAME} in {LOCATION}. Today is {CURRENT_TIME}. Ask one question at a time to collect: name (string), check_in (date), check_out (date), guests (int), breakfast (bool), payment_method (cash, card, paypal)."
    }]

    console.print(f"[cyan]Welcome to {HOTEL_NAME}![/cyan] I'm {BOT_NAME}, your assistant.\n")

    while True:
        user_input = Prompt.ask("[green]You[/green]")
        if user_input.lower() in ["exit", "quit"]: break
        messages.append({"role": "user", "content": user_input})

        reply = chat_api(messages)
        messages.append({"role": "assistant", "content": reply})
        console.print(f"[yellow]{BOT_NAME}[/yellow]: {reply.strip()}")

        if check_info_complete(messages):
            data = extract_booking_json(messages)
            if is_valid_booking(data):
                with open("booking.json", "w") as f: json.dump(data, f, indent=4)
                console.print("[green]\n✅ Booking complete[/green]")
                console.print(f"[blue]Hotel:[/blue] {HOTEL_NAME}")
                console.print(f"[blue]Name:[/blue] {data['name']}")
                console.print(f"[blue]Check-in:[/blue] {data['check_in']}")
                console.print(f"[blue]Check-out:[/blue] {data['check_out']}")
                console.print(f"[blue]Guests:[/blue] {data['guests']}")
                console.print(f"[blue]Breakfast:[/blue] {'Yes' if data['breakfast'] else 'No'}")
                console.print(f"[blue]Payment Method:[/blue] {data['payment_method']}")
                console.print("[green]Thank you for booking with us![/green]")
                break

if __name__ == "__main__":
    run_chatbot()
