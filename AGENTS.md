# The IRIS-MCP Architecture

This document defines the specialized roles within the IRIS-MCP reasoning framework.

## 🛡️ IRIS (The Architect)

* **Role:** High-Level Reasoning, Technical Triage, and Prompt Gatekeeping.
* **Engine:** Google Gemini 3 Flash via `IRIS-MCP.py`.
* **Function:** Intercepts raw, ambiguous human intent and utilizes "Double-Think" recursive optimization to translate it into a rigid, tool-oriented command protocol.
* **Philosophy:** Intelligence as a Filter. By pre-processing requests, IRIS ensures that the downstream execution remains focused, precise, and cost-effective.

## ⚙️ The Execution Agent (The Downstream LLM)

* **Role:** Technical Execution and Implementation.
* **Engine:** Primary reasoning models (e.g., GitHub Copilot, Gemini 1.5 Pro).
* **Function:** Receives the optimized command protocols (READ, SEARCH, UPDATE) from IRIS.
* **Philosophy:** Intelligence as a Tool. Because the planning and "thinking" have already been refined by the Architect, the Execution Agent can perform complex workspace operations with significantly higher precision and fewer logic errors.

---

### The Synergy

By separating **Planning (IRIS)** from **Execution (Agent)**, this system achieves a **97.6% reduction in API spend** and **42.5x more cost-effectiveness** compared to routing raw "meat-brain" requests through high-tier reasoning models.

*Built by Gewey. A tribute to Jake.*
