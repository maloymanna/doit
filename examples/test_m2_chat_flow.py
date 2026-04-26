import asyncio
from pathlib import Path

from doit.orchestrator import Orchestrator


async def main():
    workspace = Path("~/app-workspace").expanduser().resolve()  # Use your actual workspace
    project = "m2"
    url = "https://chat.qwen.ai"
    prompt = "Hello, this is a Milestone 2 test."

    orch = Orchestrator(workspace)

    try:
        print("Opening chat session and waiting for SSO...")
        # Use the high-level method that handles SSO
        await orch.start_new_chat(project, url)
        
        # Wait for manual SSO login if needed
        print("\n" + "="*50)
        print("If SSO login page appears, please complete login in the browser.")
        print("Press Enter after you've successfully logged in and see the chat interface...")
        print("="*50)
        input()
        
        # Now send the prompt
        print("\nSending prompt...")
        await orch.send_prompt(project, url, prompt)
        
        print("Waiting for response generation...")
        # Wait for response to complete
        status = await orch.get_status()
        while status not in ("idle", "complete"):
            print(f"Status: {status}...")
            await asyncio.sleep(1)
            status = await orch.get_status()
        
        print("\n=== LAST ASSISTANT MESSAGE ===")
        response = await orch.get_last_response()
        print(response if response else "No response found")
        
        print("\n=== FULL CONVERSATION ===")
        conversation = await orch.get_conversation_history()
        if conversation:
            for msg in conversation:
                print(f"[{msg['role']}] {msg['text'][:200]}...")  # Truncate long messages
        else:
            print("No conversation history found")
        
        # Optional: Try copy method (might require permissions)
        try:
            print("\n=== TRYING COPY VIA UI ===")
            copied = await orch.get_last_response_via_copy()
            if copied:
                print(f"Copied to clipboard: {copied[:200]}...")
            else:
                print("Copy method failed (might need user permission)")
        except Exception as e:
            print(f"Copy method error: {e}")
            
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nClosing browser...")
        await orch.close_browser()


if __name__ == "__main__":
    asyncio.run(main())