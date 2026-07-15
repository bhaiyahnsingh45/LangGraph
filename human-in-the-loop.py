from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver


agent = create_agent(
    model="gpt-5.4",
    tools=[write_file, execute_sql, read_data],
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={
                "write_file": True,  # All decisions (approve, edit, reject, respond) allowed
                "execute_sql": {"allowed_decisions": ["approve", "reject"]},  # No editing allowed
                "read_data": False,  # Safe operation, no approval needed
            },
            description_prefix="Tool execution pending approval",
        ),
    ],
    # HITL requires checkpointing to persist state across interrupts
    checkpointer=InMemorySaver(),  # In production, use AsyncPostgresSaver
)
