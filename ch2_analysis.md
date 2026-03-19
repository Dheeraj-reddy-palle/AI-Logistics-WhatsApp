# Chapter 2: System Analysis

## 2.1 Existing Systems and Limitations
Traditionally, logistics companies have relied upon centralized dispatch software operated by human agents or rigid mobile applications. The friction of adopting these systems is high:
1. **Human Dispatch:** Call centers are inherently unscalable. Adding order volume requires a linear increase in staffing, creating massive overhead margins. Additionally, human operators are prone to transcription errors, particularly when recording complex geographical metadata.
2. **Mobile Applications:** Building native applications for iOS and Android introduces immense development and maintenance costs. Furthermore, consumers in emerging markets often suffer from low internal storage and bandwidth constraints, leading to application fatigue and high uninstall rates.
3. **Conversational IVR:** Standard phone trees lack the graphical interface required to share maps links, track drivers visually, or verify cargo photography.

## 2.2 Proposed System
The proposed architecture abstracts the entire dispatch process into a single conversational agent accessible via WhatsApp. Instead of dialing a phone number or downloading a native application, a consumer simply sends a message to a business phone number. 

This interaction is managed by an enterprise backend utilizing the standard WhatsApp Cloud API (simulated via an internal webhook for local testing). The incoming message payload triggers a highly optimized internal processing pipeline conceptually broken into two distinct environments:
- **The Conversational Engine:** Responsible for extracting entities (Pickup, Drop, Cargo Weight), maintaining persistent engagement context, and confirming intent (e.g., booking vs tracking).
- **The Execution Layer:** Responsible for querying the PostgreSQL database, executing distance algorithms, verifying available fleets, and assigning jobs dynamically.

## 2.3 Feasibility Study

### 2.3.1 Technical Feasibility
The architecture relies entirely on battle-tested, open-source technology natively supported on virtually all operating systems. Python 3.11 provides the asynchronous foundation required to handle thousands of concurrent I/O operations. FastAPI was selected over Django or Flask for its native support of asynchronous endpoints and Pydantic validation, critical for enforcing data hygiene on incoming webhooks. Redis was deployed for low-latency, transient state management and spatial locking (idempotency keying). PostgreSQL was selected for its robust ACID compliance. PostGIS was initially considered for spatial querying but was explicitly eliminated in favor of internal application-layer Haversine indexing to guarantee local testing compatibility without heavy C-library dependencies.

### 2.3.2 Operational Feasibility
Operationally, substituting a traditional dispatch center for a WhatsApp webhook dramatically reduces the Time-To-resolution (TTR) for booking creation. Testing indicates standard bookings clear within 4.5 seconds under standard conversational delays. The use of rule-based Natural Language Processing over commercial Generative AI ensures deterministic behavior. Operational supervisors will not have to combat conversational hallucinations or unexpected deviations from standard operating procedures (SOP).

### 2.3.3 Economic Feasibility
The complete eradication of external LLM endpoints drastically improves the operational margin. Prior architectures relying on OpenAI's GPT-4 Turbo models incurred costs matching roughly $0.05 per standard conversational transaction (representing 4 context loops). In markets where the delivery profit margin averages $2.50 to $4.00, this fee is non-viable. The refactored system introduces zero external transactional costs. The entire project operates entirely offline, making it infinitely scalable for minimal server hosting fees.

## 2.4 Requirements Specification

### 2.4.1 Functional Requirements (FR)
- **FR 1:** The system MUST accept, parse, and validate webhook payloads formatted identically to standard WhatsApp business architecture.
- **FR 2:** The system MUST prevent duplicate message processing when network layers resend identical webhook POSTs within a 24-hour cycle.
- **FR 3:** The system MUST identify intent accurately between new shipment bookings, live location tracking queries, and generic greetings.
- **FR 4:** The Location Resolver MUST distinguish between high-precision inputs (exact GPS bounds) and low-precision inputs (area codes), enforcing clarification automatically.
- **FR 5:** The system MUST support Remote bookings, demanding third-party passenger phone verification before executing driver assignment.
- **FR 6:** The Driver assignment matrix MUST geographically match the active user payload to the closest available fleet member sorted ascending by distance.
- **FR 7:** The system MUST recalculate predicted pricing in real-time when the assigned driver submits a `verified_weight` conflicting with the consumer's `declared_weight`.

### 2.4.2 Non-Functional Requirements (NFR)
- **NFR 1: Reliability:** The system must degrade gracefully. Synthetic faults must be encapsulated within a strict exception boundary and report a safe "start over" parameter rather than crashing the primary event loop.
- **NFR 2: Maintainability:** Core functionality must be uncoupled from paid AI providers, utilizing strict regular expression heuristics.
- **NFR 3: Performance:** Response compilation must not exceed 2.0 seconds locally without explicit conversational simulation toggles enabled.

\newpage
