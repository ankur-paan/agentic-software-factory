# Wave Specification: Wave 01 (Core Kernel & Storage)

A wave is an ordered sequence of tickets that advance a system to an executable milestone.

---

## Wave Manifest

| Order | Ticket ID | Scope | Dependencies | Est. Rounds |
| :---: | :--- | :--- | :--- | :---: |
| 1 | `CORE-01` | Socket listener & protocol framing | None | 2 |
| 2 | `CORE-02` | In-memory bounded ring buffer | `CORE-01` | 1 |
| 3 | `CORE-03` | Disk persistence write-ahead log | `CORE-02` | 3 |
| 4 | `CORE-04` | End-to-end integration benchmark | `CORE-03` | 2 |

---

## Wave Rules & Thresholds

1. **Sequential Checkpoints**: Each ticket must achieve dual approval (`Reviewer A: accepted` AND `Reviewer B: accepted`) and be committed by the harness before the next ticket starts.
2. **Regression Floor**: The cumulative test suite from prior waves must pass 100% on every gate run.
3. **Marker Budget**: Maximum of 3 total `TODO(factory):` markers permitted across the entire wave.
