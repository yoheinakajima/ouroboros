# Ouro-ActiveGraph-50

This directory defines the no-key container used by the five locally owned
ActiveGraph construction tasks. The task packages themselves are generated
deterministically from `research/activegraph_benchmark.py` so sealed cases are
never copied into an agent-visible workspace.

Build the image, record its local content ID, and materialize the tasks:

```bash
docker build -t ouroboros-activegraph-50:1 benchmarks/activegraph_50
IMAGE_ID="$(docker image inspect ouroboros-activegraph-50:1 --format '{{.Id}}')"
python -m research.activegraph_benchmark \
  --materialize .benchmark-cache/activegraph_50 \
  --image "$IMAGE_ID" \
  --verify
```

The deliberate seed must score 20/50 and the manager fixture oracle must score
50/50 on every task before a task version can be frozen.
