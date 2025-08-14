# Event Flow Diagram

```mermaid
sequenceDiagram
    participant P as Asset Producer
    participant V as VisionService
    participant M as MainAPI
    participant R as Redis

    P->>V: image.embedding.ready (event1)
    V->>R: Check event1 existence
    R-->>V: Not found
    V->>V: Process asset
    V->>R: Store event1, update counters
    V->>V: Check completion
    alt All assets processed
        V->>M: image.embeddings.completed
    else Timeout reached
        V->>M: image.embeddings.completed (partial)
    end
    M->>M: Handle phase transition