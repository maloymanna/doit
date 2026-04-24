import asyncio
from pathlib import Path

from doit.orchestrator import Orchestrator


async def main():
    workspace = Path(".")  # or pass explicit workspace path
    project = "m2-test"
    url = "https://www.usegpt.myorg"
    prompt = "Hello, this is a Milestone 2 test."

    orch = Orchestrator(workspace)

    print("Opening chat session...")
    await orch.open_chat_session(project)

    print("Navigating to UI...")
    await orch.navigate(url)

    print("Starting new chat...")
    await orch.browser.click_new_chat()

    print("Selecting model...")
    await orch.browser.select_model()

    print("Sending prompt...")
    await orch.browser.send_prompt(prompt)

    print("Waiting for completion...")
    while True:
        status = await orch.get_status()
        print("Status:", status)
        if status in ("idle", "complete"):
            break
        await asyncio.sleep(0.2)

    print("\n=== LAST ASSISTANT MESSAGE ===")
    print(await orch.get_last_response())

    print("\n=== LAST ASSISTANT TOKENS ===")
    print(await orch.get_last_response_tokens())

    print("\n=== FULL CONVERSATION ===")
    for msg in await orch.get_conversation_history():
        print(f"[{msg['role']}] {msg['text']}")

    print("\n=== COPY VIA UI ===")
    print(await orch.get_last_response_via_copy())


if __name__ == "__main__":
    asyncio.run(main())
