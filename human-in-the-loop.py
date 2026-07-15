from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command


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




config = {"configurable": {"thread_id": "some_id"}}

# Run until an interrupt is hit
result = agent.invoke(
    {"messages": [{"role": "user", "content": "Delete old records from the database"}]},
    config=config,
    version="v2",
)

print(result.interrupts)
# Interrupt(value={
#   'action_requests': [{'name': 'execute_sql', 'arguments': {...}, 'description': '...'}],
#   'review_configs': [{'action_name': 'execute_sql', 'allowed_decisions': ['approve', 'reject']}]
# })

# Resume with a human decision
agent.invoke(
    Command(resume={"decisions": [{"type": "approve"}]}),
    config=config,  # same thread_id to resume the paused execution
    version="v2",
)


# 1. Approve — run tool call unchanged
Command(resume={"decisions": [{"type": "approve"}]})

# 2. Edit — run tool call with modified args
Command(resume={"decisions": [{
    "type": "edit",
    "edited_action": {"name": "execute_sql", "args": {"query": "SELECT * FROM records LIMIT 10"}}
}]})

# 3. Reject — skip execution, feedback goes back to the model
Command(resume={"decisions": [{
    "type": "reject",
    "message": "No, this is wrong because ..., instead do this ..."
}]})

# 4. Respond — skip execution, human message becomes the tool result directly (for "ask_user"-style tools)
Command(resume={"decisions": [{"type": "respond", "message": "Blue."}]})
