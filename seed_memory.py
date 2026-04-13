from memory_seed import QA_PAIRS, preload_agent_memory_sync
from vanna_setup import get_agent


def seed():
    agent = get_agent()
    memory = agent.agent_memory
    before = len(getattr(memory, "_memories", []))

    preload_agent_memory_sync(
        memory, conversation_id="seed-memory", request_id="seed-memory"
    )

    after = len(getattr(memory, "_memories", []))
    seeded = after - before

    for pair in QA_PAIRS:
        print(f"  OK  {pair['question']}")

    print(f"\nSeeded {seeded}/{len(QA_PAIRS)} Q&A pairs into agent memory.")


if __name__ == "__main__":
    seed()
