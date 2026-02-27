# Technical Spec: Polymorphic Audit & Revision History

## 1. Overview

The objective is to implement a robust revision history system for `FormSubmission` records. However, given the likelihood of needing similar audit capabilities for `Chat`, `Message`, or `User` models in the future, a rigid, single-table solution (e.g., `FormSubmissionHistory`) creates unnecessary schema debt.

Instead, I propose a **Polymorphic Audit Log** architecture. This design decouples the history tracking from the specific entity being tracked, allowing the system to scale to new data models without requiring database migrations for every new feature.

## 2. Database Schema Design

We will introduce a single, append-only table named `audit_logs`. This table utilizes a **Discriminator Column** (`entity_type`) to allow dynamic association with any parent table.

### Table Definition (`audit_logs`)

| Column Name | Data Type | Purpose |
| :--- | :--- | :--- |
| `id` | `BigInteger` (PK) | Unique identifier for the log entry. |
| `entity_type` | `String` (Index) | The class name of the modified object (e.g., `"form_submission"`, `"chat"`). |
| `entity_id` | `Integer` (Index) | The Primary Key of the specific row being modified. |
| `actor_id` | `String` | Identifier of the user or AI agent performing the change. |
| `operation` | `Enum` | The type of change: `CREATE`, `UPDATE`, `DELETE`. |
| `state_delta` | `JSON/JSONB` | A serialized object capturing **only** the fields that changed. |
| `timestamp` | `DateTime` | UTC timestamp of when the change occurred. |

### The `state_delta` Structure

To optimize storage efficiency, we will store the **delta** (difference) rather than a full snapshot of the row.

**Example Payload (Status Update):**

```json
{
  "status": {
    "old": 1,
    "new": 2
  },
  "updated_at": {
    "old": "2023-10-27T10:00:00Z",
    "new": "2023-10-27T12:05:00Z"
  }
}
```

## 3. Engineering Decisions & Trade-offs

### Why Polymorphic vs. Shadow Tables?

* **Shadow Tables (1:1 Mapping):** A common approach is creating `form_history`, `chat_history`, etc.
  * *Trade-off:* This creates schema bloat. Every time we add a column to `FormSubmission`, we must remember to migrate `form_history`. It doubles the maintenance burden.
* **Polymorphic (Selected Approach):**
  * *Benefit:* **Zero-config scalability.** When we want to track `Chat` history later, we simply start writing to `audit_logs` with `entity_type="chat"`. No schema migration is required.
  * *Benefit:* Centralized auditing allows for global queries (e.g., "Show me all changes made by User X today across the entire platform").

### Why JSON Deltas vs. Full Snapshots?

* *Storage Efficiency:* A `FormSubmission` might eventually have 50 columns. If a user only updates the `status`, storing the other 49 unchanged columns is wasteful.
* *Context:* Storing `{ old: X, new: Y }` explicitly answers "What changed?" without requiring the application to fetch the previous row and compute the diff at read-time.

## 4. Edge Cases & Future Considerations

* **Schema Evolution:** Since the payload is stored as JSON, changes to the parent schema (e.g., renaming a column) do not break historical logs. The logs remain an immutable record of what the data *was* at that point in time.
* **High-Volume Writes:** In a high-throughput environment (e.g., thousands of updates per second), this table could grow rapidly.
  * *Mitigation:* This table is a prime candidate for **Partitioning by Time** (e.g., creating a new partition every month). This ensures that querying recent history remains fast even as the table grows to millions of rows.

## 5. Implementation Strategy (Python/SQLAlchemy)

In the application layer, this can be implemented using an SQLAlchemy **Event Listener** (`@event.listens_for(Session, 'before_flush')`). This hook can automatically inspect the session's dirty list, compute the diffs, and inject the `audit_logs` record within the same atomic transaction, ensuring data integrity without cluttering the API endpoint logic.
