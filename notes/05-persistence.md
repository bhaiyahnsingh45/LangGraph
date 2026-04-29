# Persistence in LangGraph

## Why Persistence?

LangGraph workflows can be **long-running** and may need to:
- Survive failures and resume from where they left off
- Allow human intervention mid-execution
- Maintain conversation history across sessions
- Support multi-turn interactions
- Enable time travel debugging

**Persistence** = saving graph state at each **super-step** boundary so it can be restored later.

## Checkpointers

A **Checkpointer** automatically saves the state of your graph after each super-step (execution cycle where all scheduled nodes run).

```
[Node A] → [Save Checkpoint] → [Node B] → [Save Checkpoint] → [Node C] → [Save Checkpoint]
```

If the system crashes after Node B, you can resume from the last checkpoint instead of starting over.

### Built-in Checkpointers

| Checkpointer | Package | Storage | Use Case |
|--------------|---------|---------|----------|
| `InMemorySaver` | langgraph | RAM | Development, testing |
| `SqliteSaver` | langgraph-checkpoint-sqlite | SQLite file | Local persistence |
| `PostgresSaver` | langgraph-checkpoint-postgres | PostgreSQL | Production, multi-instance |
| `CosmosDBSaver` | langchain-azure-cosmosdb | Azure Cosmos DB | Enterprise production |

## InMemorySaver (Development)

Stores checkpoints in memory. Data is lost when the process ends.

```python
from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()
app = graph.compile(checkpointer=checkpointer)
```

## SqliteSaver (Local Persistence)

Stores checkpoints in a SQLite database file. Install: `pip install langgraph-checkpoint-sqlite`

```python
from langgraph.checkpoint.sqlite import SqliteSaver

# In-memory SQLite
with SqliteSaver.from_conn_string(":memory:") as checkpointer:
    app = graph.compile(checkpointer=checkpointer)

# File-based SQLite
with SqliteSaver.from_conn_string("checkpoints.db") as checkpointer:
    app = graph.compile(checkpointer=checkpointer)
```

## PostgresSaver (Production)

Stores checkpoints in PostgreSQL. Install: `pip install langgraph-checkpoint-postgres`

```python
from langgraph.checkpoint.postgres import PostgresSaver

DB_URI = "postgresql://user:pass@localhost:5432/dbname"

with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
    app = graph.compile(checkpointer=checkpointer)
```

## Thread ID and Checkpoint ID

### Thread ID
Each conversation/session needs a unique **thread_id** to keep states separate.

```python
config = {"configurable": {"thread_id": "user-123-session-1"}}
result = app.invoke({"messages": [...]}, config=config)
```

**Without thread_id, checkpointers cannot persist or resume execution.**

### Checkpoint ID
Each checkpoint within a thread has a unique **checkpoint_id**. Use it for time travel.

```python
config = {
    "configurable": {
        "thread_id": "user-123",
        "checkpoint_id": "1ef663ba-28fe-6528-8002-5a559208592c"
    }
}
```

### Checkpoint Namespaces
- `""` for parent graphs
- `"node_name:uuid"` for subgraphs
- Nested with `|` separators for deep subgraphs

## StateSnapshot Structure

Each checkpoint is represented as a `StateSnapshot` containing:

```python
StateSnapshot(
    values={...},           # State channel values at this checkpoint
    next=("node_b",),       # Node(s) executing next (empty = completed)
    config={                # Contains thread_id, checkpoint_ns, checkpoint_id
        "configurable": {
            "thread_id": "1",
            "checkpoint_ns": "",
            "checkpoint_id": "abc123"
        }
    },
    metadata={              # Execution info
        "source": "loop",   # "input", "loop", or "update"
        "step": 3,
        "writes": {...}
    },
    created_at="2026-04-29T10:30:00Z",
    parent_config={...},    # Previous checkpoint config
    tasks=(...)             # Pending tasks with interrupt info
)
```

## Working with State

### Get Current State

```python
config = {"configurable": {"thread_id": "1"}}
state = app.get_state(config)

print(state.values)  # Current state values
print(state.next)    # Next node(s) to execute
```

### Get Specific Checkpoint

```python
config = {
    "configurable": {
        "thread_id": "1",
        "checkpoint_id": "1ef663ba-28fe-6528-8002-5a559208592c"
    }
}
state = app.get_state(config)
```

### Get State History

```python
# Returns chronologically ordered, most recent first
history = list(app.get_state_history(config))

for state in history:
    print(f"Step: {state.metadata['step']}")
    print(f"Values: {state.values}")
    print(f"Next: {state.next}")
```

### Finding Specific Checkpoints

```python
history = list(app.get_state_history(config))

# Before a specific node execution
before_node_b = next(s for s in history if s.next == ("node_b",))

# By step number
step_2 = next(s for s in history if s.metadata["step"] == 2)

# From state updates (manual updates)
forks = [s for s in history if s.metadata["source"] == "update"]

# With interrupts
interrupted = next(
    s for s in history 
    if s.tasks and any(t.interrupts for t in s.tasks)
)
```

### Update State Manually

Creates a **new checkpoint** without modifying originals. Values flow through reducers.

```python
app.update_state(
    config,
    {"messages": [new_message]},
    as_node="human_input"  # Optional: controls which node "wrote" this
)

# Continue execution with updated state
result = app.invoke(None, config=config)
```

## Time Travel and Replay

### Replay from Past Checkpoint

Re-execute from a previous checkpoint. Nodes before that checkpoint use cached results.

```python
# Get history
history = list(app.get_state_history(config))

# Find past checkpoint
past_checkpoint = history[2]

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

### Branching

When you resume from a past checkpoint with different input, it creates a **new checkpoint chain** diverging from that point — like git branches.

## Serialization and Encryption

### Custom Serialization

Default `JsonPlusSerializer` handles LangChain primitives. For unsupported types:

```python
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

checkpointer = InMemorySaver(
    serde=JsonPlusSerializer(pickle_fallback=True)
)
```

### Encryption

Enable AES encryption for persisted state:

```python
from langgraph.checkpoint.serde.encrypted import EncryptedSerializer
from langgraph.checkpoint.sqlite import SqliteSaver

# Uses LANGGRAPH_AES_KEY environment variable
serde = EncryptedSerializer.from_pycryptodome_aes()
checkpointer = SqliteSaver(conn, serde=serde)
```

## Memory Stores (Cross-Thread Memory)

Beyond thread-specific checkpointing, **Memory Stores** enable information sharing **across threads**.

### Basic Memory Operations

```python
from langgraph.store.memory import InMemoryStore
import uuid

store = InMemoryStore()
user_id = "1"
namespace = (user_id, "memories")

# Save memory
memory_id = str(uuid.uuid4())
store.put(namespace, memory_id, {"preference": "pizza"})

# Retrieve memories
memories = store.search(namespace)
latest = memories[-1].dict()
```

### Semantic Search in Memory

```python
from langchain.embeddings import init_embeddings

store = InMemoryStore(
    index={
        "embed": init_embeddings("openai:text-embedding-3-small"),
        "dims": 1536,
        "fields": ["preference", "$"]
    }
)

# Natural language query
memories = store.search(
    namespace,
    query="What does user like to eat?",
    limit=3
)
```

### Using Store in Graph

```python
from dataclasses import dataclass
from langgraph.runtime import Runtime

@dataclass
class Context:
    user_id: str

# Access store in node
async def update_memory(state, runtime: Runtime[Context]):
    user_id = runtime.context.user_id
    namespace = (user_id, "memories")
    
    memory_id = str(uuid.uuid4())
    await runtime.store.aput(namespace, memory_id, {"data": "..."})

# Compile with both checkpointer and store
graph = builder.compile(checkpointer=checkpointer, store=store)

# Invoke with context
config = {"configurable": {"thread_id": "1"}}
graph.invoke(input, config, context=Context(user_id="1"))
```

## Complete Example: Persistent Chatbot

```python
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
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
memory = InMemorySaver()
app = graph.compile(checkpointer=memory)

# Configuration with thread_id
config = {"configurable": {"thread_id": "user-123"}}

# Conversation persists across invocations
app.invoke({"messages": [("user", "My name is Rahul")]}, config)
app.invoke({"messages": [("user", "What's my name?")]}, config)
# Bot remembers: "Your name is Rahul"
```

## Key Concepts Summary

| Concept | Description |
|---------|-------------|
| **Checkpointer** | Saves state at each super-step boundary |
| **Thread ID** | Unique identifier for a conversation/session |
| **Checkpoint ID** | Unique identifier for a specific state snapshot |
| **StateSnapshot** | Object containing values, next, config, metadata |
| **InMemorySaver** | In-memory storage (dev/testing) |
| **SqliteSaver** | File-based persistence (local) |
| **PostgresSaver** | Database persistence (production) |
| **get_state()** | Retrieve current or specific state |
| **get_state_history()** | Retrieve all past states |
| **update_state()** | Manually modify state (creates new checkpoint) |
| **Time Travel** | Resume from a past checkpoint |
| **Memory Store** | Cross-thread memory sharing |

---

## Interview Questions

### Conceptual

1. **Why does LangGraph need a separate thread_id for each conversation rather than just using the checkpointer?**
   > A single checkpointer can store states for many conversations simultaneously. The thread_id acts as a partition key — it tells the checkpointer which conversation's state to load or save. Without thread_id, all users would share the same state, which would be chaotic. The checkpointer is the storage mechanism; thread_id is the addressing scheme.

2. **Why does LangGraph save state at super-step boundaries rather than after every single operation?**
   > A super-step is an atomic unit where all scheduled nodes run concurrently. Saving at super-step boundaries ensures consistency — you capture a complete state where all parallel nodes have finished their writes. Saving mid-super-step could capture partial states where some parallel nodes have written but others haven't, leading to inconsistent recovery points.

3. **How does the checkpoint parent chain enable features like time travel and branching?**
   > Each checkpoint stores a `parent_config` pointing to the previous checkpoint, forming a linked list of states. Time travel works by loading a past checkpoint and resuming from there. Branching happens when you resume from a past checkpoint with different input — it creates a new checkpoint chain diverging from that point, like git branches. The old future still exists in history.

4. **How do Memory Stores differ from Checkpointers in purpose and scope?**
   > Checkpointers save state **within a thread** — each thread has isolated state history. Memory Stores share information **across threads** — any thread can read/write to a namespace. Use checkpointers for conversation history; use stores for user preferences, learned facts, or shared knowledge that should persist across different conversations.

### Critical Thinking

1. **When would you choose PostgresSaver over SqliteSaver, and what trade-offs are involved?**
   > Choose PostgresSaver when you need multi-instance support (multiple servers accessing the same checkpoints), durability guarantees, concurrent access, and integration with existing infrastructure. SqliteSaver is simpler, has no external dependencies, and works well for single-machine deployments. The trade-off is operational complexity vs. scalability — Postgres requires setup and maintenance but handles production loads; SQLite is zero-config but doesn't scale horizontally.

2. **A developer stores sensitive data in graph state and uses PostgresSaver. What security measures should they implement?**
   > (1) Use EncryptedSerializer with AES encryption for data at rest, (2) Encrypt database connections with SSL/TLS, (3) Implement access controls on who can query checkpoints, (4) Consider excluding sensitive fields from state or encrypting them separately, (5) Implement checkpoint retention policies to delete old data, (6) Audit checkpoint access. The checkpointer stores exactly what you put in state — it doesn't sanitize or filter.

3. **If get_state_history() returns thousands of checkpoints for a long conversation, how would you handle this efficiently?**
   > Don't load all history at once — use filtering predicates when searching history. Filter by step range, metadata source, or specific conditions. For display purposes, only load recent checkpoints. For debugging, jump directly to a specific checkpoint_id rather than iterating. Consider implementing checkpoint compaction — periodically consolidating old checkpoints into summaries. The state history is an audit log, not a data structure you should iterate fully in production.

### Scenario-Based

1. **You're building a customer support bot that needs to remember conversation history across browser sessions. How do you design the persistence?**
   > Use PostgresSaver for production persistence. Generate thread_id from user authentication (e.g., `user-{user_id}`) so it's stable across sessions. When a user returns, load their thread_id and the graph automatically resumes with full history via the checkpointer. Don't tie thread_id to browser session — tie it to user identity. Store the thread_id mapping in your user database if needed.

2. **A long-running workflow fails at step 15 of 20 due to an external API timeout. How do you resume without losing progress?**
   > With a checkpointer enabled, the state is saved after each super-step. Identify the thread_id of the failed run, then call `app.invoke(None, config)` — passing `None` as input tells LangGraph to resume from the last checkpoint rather than starting fresh. The graph will re-execute step 15 (the failed node) and continue. If the API is still down, implement retry logic in the node itself, or use `update_state()` to manually provide the missing data and skip the failed node.

3. **Your team wants to implement an "undo" feature in a document editing workflow. How would you use checkpoints to enable this?**
   > Use `get_state_history(config)` to retrieve past checkpoints. Display them to the user as "versions" (e.g., "Draft from 10:30 AM"). When the user clicks "undo," get the checkpoint_id of the desired version, create a new config with that checkpoint_id, and call `app.invoke()` with new input. This creates a new branch from that point — the old "future" states still exist in history but are no longer on the active branch. You're not deleting; you're branching from a past state.

---

*Studied: 2026-04-29*
