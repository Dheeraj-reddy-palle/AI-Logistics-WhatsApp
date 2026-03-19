# Chapter 3: System Design

## 3.1 Architectural Overview
The system follows a highly modular, decoupled software architecture constructed on an asynchronous Application Programming Interface (API). It abandons the traditional monolithic data synchronization structures prevalent in enterprise logistics platforms in favor of a specialized webhook receiver tailored inherently for conversational interactions. 

The architecture is broadly classified into three critical horizontal layers:
1. **The Ingress API Layer:** Written in FastAPI, handling high-concurrency request routing.
2. **The Intelligence Layer (State Machine):** Written natively in Python, orchestrating contextual conversational retention spanning multiple unassociated HTTP requests across a transient Redis cache.
3. **The Data Persistence / Execution Layer:** Writing permanent transactional structures into an asynchronous PostgreSQL relational database using an Object-Relational Mapper (SQLAlchemy).

## 3.2 Diagrammatic Execution Flow 
The typical runtime environment of a single webhook can be modeled chronologically:

1. **Ingress:** A metadata JSON object containing the sender's phone number, a unique message identifier, and the raw text message enters via the `POST /webhook` endpoint.
2. **Idempotency Locking:** The agent immediately parses the `message_id` against a Redis `SETNX` (Set if Not Exists). If the key is already present, the system immediately drops the payload. This entirely resolves the known issue of Meta's webhook endpoints persistently re-transmitting dropped ACK packages.
3. **NLP Parsing:** The `mock_ai_parser` absorbs the text string and identifies conversational intent. It strips structural elements and classifies the response across heuristics identifying: *Bookings*, *Greetings*, *Tracking*, *Cancellations*, or *Coordinates*.
4. **State Machine Lookup:** Utilizing the sender's phone number as the root associative key, the `StateMachine` retrieves the active `context` array from Redis. 
5. **Route Handling:** The handler triggers the specific `_handle_*` function tied to the active state. If the active state is `idle`, the system routes to `_handle_idle` which then forces the context to advance to `collecting_pickup`.
6. **Execution Logic & Service Calls:** If the state resolves as `booking_confirmed`, the runtime injects the context variable dictionary natively into the `BookingService` mapping the schema across PostgreSQL. In tandem, the `DriverService` is invoked geographically resolving the nearest compatible fleet member.
7. **Egress:** The system collates a highly-stylized conversational string integrating dynamic variables (Pricing Estimates or Assigned Drivers) and pushes the JSON reply back terminating the original FastAPI thread.

## 3.3 Database Schema and Normalization
Relational mapping inside PostgreSQL ensures rigorous data normalization.

### The Booking Entity
- **ID:** UUID (Primary Key)
- **Customer Phone:** String
- **Pickup Latitude / Longitude:** Float Fields
- **Drop-off Latitude / Longitude:** Float Fields
- **Declared Weight:** Numeric/Float
- **Verified Weight:** Nullable Numeric
- **Status:** ENUM (`PENDING`, `ASSIGNED`, `IN_TRANSIT`, `COMPLETED`, `CANCELLED`)
- **Assigned Driver ID:** Foreign Key mapping to the `Drivers` table.

### The Fleet Entity
Unlike traditional driver tracking mechanisms dictating PostGIS (a heavy PostgreSQL spatial extension dependency), this architecture drastically curtails overhead by stripping geometry columns. Fleet drivers utilize:
- **ID:** UUID (Primary Key)
- **Last Known Latitude:** Float Field
- **Last Known Longitude:** Float Field
- **Capabilities Matrix:** ENUM mapping vehicle types (Motorcycle, Van, Truck).

Geographical selection functions rely strictly on application-side math logic executed against active queries, rather than forcing the database itself to handle spatial indexes. 

## 3.4 State Machine Theory
A state machine acts as a deterministic ledger governing allowable transitions between states. The defined conversational nodes are:
1. `idle`
2. `collecting_pickup`
3. `collecting_drop`
4. `collecting_weight`
5. `collecting_passenger`
6. `booking_confirmed`
7. `tracking`

At any boundary, the input is strictly evaluated against the current state constraint. For example, if a user replies "yes" inside the `collecting_weight` node, the system intelligently rejects it (recognizing "yes" is not a numerical value) and retains the state identically. Comparatively, if the user transmits "cancel," a global override hook is caught directly after idempotency parsing, tearing down the active Redis cache payload entirely and forcefully resetting the context to `idle`.

\newpage
