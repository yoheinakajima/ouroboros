# ActiveGraph 1.10 Pack API used by this benchmark

The benchmark image contains `activegraph==1.10.0`. Candidate code must use the
pack-aware API so importing it does not mutate the global behavior registry.

```python
from pydantic import BaseModel
from activegraph.packs import Pack, ObjectType, RelationType, behavior

class Task(BaseModel):
    task_id: str
    status: str

@behavior(name="handle_request", on=["ouro.benchmark.requested"])
def handle_request(event, graph, ctx):
    # Reads use the immutable behavior view.
    tasks = ctx.view.objects(type="task")
    edges = ctx.view.relations(type="depends_on")

    # Mutations use the behavior-scoped graph capability.
    created = graph.add_object("task", {"task_id": "t1", "status": "open"})
    graph.patch_object(created.id, {"status": "done"})
    graph.add_relation(created.id, other.id, "depends_on", {})
    graph.emit(
        "ouro.benchmark.completed",
        {"request_id": event.payload["request_id"], "output": {"ok": True}},
    )

PACK = Pack(
    name="lowercase_identifier",
    version="1.0.0",
    object_types=(ObjectType(name="task", schema=Task),),
    relation_types=(
        RelationType(name="depends_on", source_types=("task",), target_types=("task",)),
    ),
    behaviors=(handle_request,),
)
```

Important contracts:

- A behavior receives `(event, graph, ctx)`. Read current state through
  `ctx.view.objects(type=...)` and `ctx.view.relations(type=...)`.
- `graph.add_object`, `graph.patch_object`, `graph.add_relation`, and
  `graph.emit` append events; they do not mutate Python dictionaries in place.
- Object versions begin at 1 and increase once per effective patch call.
- The Pack must declare every object and relation type it owns. Loaded object
  schemas and relation endpoint rules are enforced by the runtime.
- Pack-aware decorators come from `activegraph.packs`, not `activegraph`.
- Behavior reads are a snapshot from the beginning of that behavior call. A
  newly created object is available from the handle returned by
  `graph.add_object`; it does not appear in `ctx.view` until a later event.
- Emit one result for each request. Returning a Python value from a behavior
  does not emit an event.
- SQLite persistence and replay are handled by the runtime. Durable business
  state and idempotency receipts must live in graph objects/relations, never
  module globals.
