# Persistence in LangGraph

## Why Persistence?

LangGraph workflows can be **long-running** and may need to:
- Survive failures and resume from where they left off
- Allow human intervention mid-execution
- Maintain conversation history across sessions
- Support multi-turn interactions

**Persistence** = saving graph state at each step so it can be restored later.

## Checkpointers

A **Checkpointer** saves the state of your graph after each node execution.

```
[Node A] → [Save State] → [Node B] → [Save State] → [Node C] → [Save State]
```

If the system crashes after Node B, you can resume from the last checkpoint instead of starting over.

### Built-in Checkpointers

| Checkpointer | Storage | Use Case |
|--------------|---------|----------|
| `MemorySaver` | In-memory (RAM) | Development, testing |
| `SqliteSaver` | SQLite file | Single-machine persistence |
| `PostgresSaver` | PostgreSQL | Production, multi-instance |

## MemorySaver (Development)

Stores checkpoints in memory. Data is lost when the process ends.

```python
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
app = graph.compile(checkpointer=memory)
```

## SqliteSaver (Local Persistence)

Stores checkpoints in a SQLite database file.

```python
from langgraph.checkpoint.sqlite import SqliteSaver

# Sync version
with SqliteSaver.from_conn_string(":memory:") as checkpointer:
    app = graph.compile(checkpointer=checkpointer)

# Or with a file
with SqliteSaver.from_conn_string("checkpoints.db") as checkpointer:
    app = graph.compile(checkpointer=checkpointer)
```

## PostgresSaver (Production)

Stores checkpoints in PostgreSQL for production use.

```python
from langgraph.checkpoint.postgres import PostgresSaver

DB_URI = "postgresql://user:pass@localhost:5432/dbname"

with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
    app = graph.compile(checkpointer=checkpointer)
```

## Thread ID: Separating Conversations

Each conversation/session needs a unique **thread_id** to keep states separate.

```python
# User 1's conversation
config1 = {"configurable": {"thread_id": "user-123-session-1"}}
result1 = app.invoke({"messages": [...]}, config=config1)

# User 2's conversation (separate state)
config2 = {"configurable": {"thread_id": "user-456-session-1"}}
result2 = app.invoke({"messages": [...]}, config=config2)
```

### Thread ID Best Practices

```python
# For chatbots: user_id + session_id
thread_id = f"user-{user_id}-session-{session_id}"

# For workflows: workflow_id + run_id
thread_id = f"workflow-{workflow_id}-run-{run_id}"

# For testing: timestamp-based
thread_id = f"test-{datetime.now().isoformat()}"
```

## Resuming from Checkpoint

```python
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
app = graph.compile(checkpointer=memory)

config = {"configurable": {"thread_id": "conversation-1"}}

# First invocation
result1 = app.invoke({"messages": [HumanMessage("Hello")]}, config=config)

# Second invocation - continues from where it left off
result2 = app.invoke({"messages": [HumanMessage("What's my name?")]}, config=config)
# The graph remembers the previous conversation
```

## Getting State History

You can retrieve past states for debugging or auditing.

```python
# Get current state
current_state = app.get_state(config)
print(current_state.values)  # Current state values
print(current_state.next)    # Next node(s) to execute

# Get state history
for state in app.get_state_history(config):
    print(f"Step: {state.step}")
    print(f"Values: {state.values}")
    print(f"Next: {state.next}")
    print("---")
```

## Updating State Manually

You can modify state between executions.

```python
# Get current state
state = app.get_state(config)

# Update state
app.update_state(
    config,
    {"messages": state.values["messages"] + [new_message]},
    as_node="human_input"  # Pretend this came from a specific node
)

# Continue execution with updated state
result = app.invoke(None, config=config)
```

## Complete Example: Persistent Chatbot

```python
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_aws import ChatBedrockConverse

# State with message history
class ChatState(TypedDict):
    messages: Annotated[list, add_messages]

# LLM
llm = ChatBedrockConverse(model="us.anthropic.claude-sonnet-4-6")

# Chatbot node
def chatbot(state: ChatState):
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

# Build graph
graph = StateGraph(ChatState)
graph.add_node("chatbot", chatbot)
graph.add_edge(START, "chatbot")
graph.add_edge("chatbot", END)

# Compile with checkpointer
memory = MemorySaver()
app = graph.compile(checkpointer=memory)

# Configuration with thread_id
config = {"configurable": {"thread_id": "user-123"}}

# Conversation
app.invoke({"messages": [("user", "My name is Rahul")]}, config)
app.invoke({"messages": [("user", "What's my name?")]}, config)
# Bot remembers: "Your name is Rahul"
```

## Checkpoint Structure

Each checkpoint contains:

```python
{
    "thread_id": "user-123",
    "checkpoint_id": "abc123",
    "parent_checkpoint_id": "xyz789",  # Previous checkpoint
    "step": 3,                         # Execution step number
    "values": {...},                   # State values at this point
    "metadata": {...},                 # Additional info
    "created_at": "2026-04-29T...",
    "channel_values": {...}            # Internal channel data
}
```

## Time Travel: Replaying from Past State

You can "time travel" by specifying a past checkpoint.

```python
# Get history
history = list(app.get_state_history(config))

# Find a specific checkpoint
past_checkpoint = history[2]  # Go back 2 steps

# Create config pointing to that checkpoint
past_config = {
    "configurable": {
        "thread_id": config["configurable"]["thread_id"],
        "checkpoint_id": past_checkpoint.config["configurable"]["checkpoint_id"]
    }
}

# Resume from that point (creates a new branch)
result = app.invoke({"messages": [("user", "Different input")]}, past_config)
```

## Key Concepts Summary

| Concept | Description |
|---------|-------------|
| **Checkpointer** | Saves state after each node execution |
| **Thread ID** | Unique identifier for a conversation/session |
| **MemorySaver** | In-memory storage (dev/testing) |
| **SqliteSaver** | File-based persistence (local) |
| **PostgresSaver** | Database persistence (production) |
| **get_state()** | Retrieve current state |
| **get_state_history()** | Retrieve all past states |
| **update_state()** | Manually modify state |
| **Time Travel** | Resume from a past checkpoint |

---

## Interview Questions

### Conceptual

1. **Why does LangGraph need a separate thread_id for each conversation rather than just using the checkpointer?**
   > A single checkpointer can store states for many conversations simultaneously. The thread_id acts as a partition key — it tells the checkpointer which conversation's state to load or save. Without thread_id, all users would share the same state, which would be chaotic. The checkpointer is the storage mechanism; thread_id is the addressing scheme.

2. **Why does LangGraph save state after each node rather than only at the end of the graph?**
   > Per-node checkpointing enables fine-grained recovery. If a graph has 10 nodes and crashes at node 7, you can resume from node 6's checkpoint instead of restarting from scratch. This is critical for long-running workflows where re-executing early nodes may be expensive (API calls, computations) or have side effects (sending emails, database writes).

3. **How does the checkpoint parent chain enable features like time travel and branching?**
   > Each checkpoint stores a `parent_checkpoint_id` pointing to the previous checkpoint, forming a linked list of states. Time travel works by loading a past checkpoint and resuming from there. Branching happens when you resume from a past checkpoint with different input — it creates a new checkpoint chain diverging from that point, like git branches.

### Critical Thinking

1. **When would you choose PostgresSaver over SqliteSaver, and what trade-offs are involved?**
   > Choose PostgresSaver when you need multi-instance support (multiple servers accessing the same checkpoints), durability guarantees, concurrent access, and integration with existing infrastructure. SqliteSaver is simpler, has no external dependencies, and works well for single-machine deployments. The trade-off is operational complexity vs. scalability — Postgres requires setup and maintenance but handles production loads; SQLite is zero-config but doesn't scale horizontally.

2. **A developer stores sensitive data in graph state and uses PostgresSaver. What security concerns should they address?**
   > Checkpoints persist the entire state, including any sensitive data (PII, credentials, API responses). Concerns: (1) Encrypt the database connection and storage, (2) Implement access controls on who can query checkpoints, (3) Consider excluding sensitive fields from state or encrypting them before storage, (4) Implement checkpoint retention policies to delete old data, (5) Audit who accesses checkpoint history. The checkpointer doesn't sanitize data — it stores whatever you put in state.

3. **If get_state_history() returns thousands of checkpoints for a long conversation, how would you handle this efficiently?**
   > Don't load all history at once — use pagination or limit queries. Most checkpointers support filtering by step range or timestamp. For display purposes, only load recent checkpoints. For debugging, jump directly to a specific checkpoint_id rather than iterating. Consider implementing checkpoint compaction — periodically consolidating old checkpoints into summaries. The state history is an audit log, not a data structure you should iterate fully in production.

### Scenario-Based

1. **You're building a customer support bot that needs to remember conversation history across browser sessions. How do you design the persistence?**
   > Use PostgresSaver for production persistence. Generate thread_id from user authentication (e.g., `user-{user_id}`) so it's stable across sessions. When a user returns, load their thread_id and the graph automatically resumes with full history via the checkpointer. Don't tie thread_id to browser session — tie it to user identity. Store the thread_id mapping in your user database if needed.

2. **A long-running workflow fails at step 15 of 20 due to an external API timeout. How do you resume without losing progress?**
   > With a checkpointer enabled, the state is saved after each step. Identify the thread_id of the failed run, then call `app.invoke(None, config)` — passing `None` as input tells LangGraph to resume from the last checkpoint rather than starting fresh. The graph will re-execute step 15 (the failed node) and continue. If the API is still down, implement retry logic in the node itself, or use `update_state()` to manually provide the missing data and skip the failed node.

3. **Your team wants to implement an "undo" feature in a document editing workflow. How would you use checkpoints to enable this?**
   > Use `get_state_history(config)` to retrieve past checkpoints. Display them to the user as "versions" (e.g., "Draft from 10:30 AM"). When the user clicks "undo," get the checkpoint_id of the desired version, create a new config with that checkpoint_id, and call `app.invoke()` with new input. This creates a new branch from that point — the old "future" states still exist in history but are no longer on the active branch. You're not deleting; you're branching from a past state.

---

*Studied: 2026-04-29*
