---
title: AI Procurement Negotiation Agent
emoji: 🤝
sdk: gradio
sdk_version: 4.44.1
app_file: gradio_ui.py
python_version: 3.11
---

# 🧠 AI Procurement Negotiation Agent

This agent uses a Hybrid AI Decision System to handle complex procurement negotiations.

## ⚙️ Project Structure
- `gradio_ui.py`: The main entry point for the Space.
- `requirements.txt`: Python dependencies.
- `server/app.py`: FastAPI backend logic.

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Motivation](#motivation)
3. [Quick Start](#quick-start)
4. [Performance Metrics](#performance-metrics)
5. [Scenarios](#scenarios)
6. [Architecture](#architecture)
7. [Setup & Installation](#setup--installation)
8. [Running the System](#running-the-system)
9. [Project Structure](#project-structure)
10. [Troubleshooting](#troubleshooting)

---

## 📌 Overview

This is a **deterministic procurement negotiation environment** for training and evaluating AI agents in structured business negotiation scenarios.

### Key Features:

✅ **3 Predefined Tasks** (Easy → Hard): SaaS renewal, Cloud infrastructure, Enterprise bundle  
✅ **Deterministic Vendor Simulator**: Rule-based, 30% concession logic per round  
✅ **Multi-Objective Negotiation**: Price, SLA, support tier, payment terms  
✅ **Realistic Long Trajectories**: 4–15 rounds per task  
✅ **Clean API**: FastAPI server + Gradio UI  
✅ **LLM-Ready**: Hybrid decision logic with Qwen2.5-72B integration  
✅ **Zero ML in Environment**: Pure Python dicts, <512MB memory footprint  

---

## 🎯 Motivation

**Procurement negotiation is a multi-billion dollar business challenge with no existing OpenEnv.**

Why this matters:
- Real agents must negotiate **across 4 dimensions** simultaneously (price, SLA, support, payment)
- Vendor makes **adaptive concessions** — natural adversarial dynamic
- Long trajectories (8–15 steps) test **planning and memory**
- Perfect benchmark for **frontier LLMs** and **RL agents**
- Judges will not have seen this before

---

## 🚀 Quick Start

### Installation

```bash
# Clone & setup
git clone <your-repo-url>
cd negotiation-env
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env and add your HF_TOKEN
```

### Run Baseline (Rule-Based)

```bash
python inference.py  # Uses rule-based agent
```

### Run LLM-Based Inference

```bash
export HF_TOKEN=your_token_here
python inference_llm.py  # Uses Qwen2.5-72B
```

### Launch Interactive UI

```bash
bash start.sh  # Starts FastAPI (8000) + Gradio (7860)
```

Then open browser: **http://localhost:7860**

---

## 📊 Performance Metrics

### Baseline Scores (Qwen2.5-72B with Hybrid Logic)

| Scenario | Score | Status | Strategy |
|----------|-------|--------|----------|
| **SaaS Renewal** | 0.583 | ✅ PASS | Balanced negotiation, ~5 rounds |
| **Cloud Infrastructure** | 0.744 | ✅ EXCELLENT | Multi-dimensional optimization |
| **Enterprise Bundle** | 1.000 | ✅ PERFECT | Correctly splits CRM from bundle |
| **Average** | 0.776 | ✅ EXCELLENT | Well-rounded agent |

**Scoring Range**: 0.0 → 1.0 (normalized)

**What These Scores Mean:**
- <0.2 = Agent fails to negotiate effectively
- 0.2–0.5 = Agent makes some progress but leaves value on table
- 0.5–0.8 = Agent negotiates well, meets most targets
- 0.8–1.0 = Agent optimizes across all dimensions

---

## 🧩 Scenarios

### 1. **SaaS Renewal** (Easy)

**Status**: Agent renews existing SaaS contract with single vendor

| Field | Initial | Target | Comment |
|-------|---------|--------|---------|
| Price | $120k | $108k | 10% discount target |
| Payment Terms | net-30 | net-60 | Better cash flow |
| SLA | 99.5% | 99.9% | Higher availability |
| Support | standard | standard | No change |

**Difficulty**: Easy  
**Rounds**: 4–6  
**Vendor Persona**: Cooperative (8 walkaway rounds)

---

### 2. **Cloud Infrastructure Deal** (Medium)

**Status**: Negotiate new 3-year cloud infrastructure contract

| Field | Initial | Target | Comment |
|-------|---------|--------|---------|
| Price | $280k | $240k | 14% discount |
| Contract Length | 3 years | 2 years | More flexibility |
| SLA | 99.9% | 99.95% | Higher uptime |
| Support | business | premium | Better support |

**Difficulty**: Medium  
**Rounds**: 8–10  
**Vendor Persona**: Firm (6 walkaway rounds)

---

### 3. **Enterprise Bundle** (Hard)

**Status**: Negotiate 3-product bundle (CRM + DataPlatform + Security)

**Products:**
- CRM: $150k → $130k (min)
- DataPlatform: $180k → $155k (min)
- Security: $95k → $80k (min)

**Bundle Trap**: 15% discount offered on all 3  
**Optimal Strategy**: Split CRM separately, negotiate only DP + Security as bundle  
**Difficulty**: Hard  
**Rounds**: 12–15  
**Vendor Persona**: Aggressive (5 walkaway rounds)

---

## 🏗️ Architecture

### Hybrid AI Decision System

```
┌─────────────────────────────────────────┐
│  LLM (Qwen2.5-72B via HF Router)        │
│  ┌───────────────────────────────────┐  │
│  │ Analyzes vendor response          │  │
│  │ Suggests reasoning (advisory)     │  │
│  │ NO final decision authority       │  │
│  └───────────────────────────────────┘  │
└──────────────┬──────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────┐
│  Deterministic Decision Logic           │
│  ┌───────────────────────────────────┐  │
│  │ 1. Check vendor response          │  │
│  │ 2. Evaluate vs. buyer targets     │  │
│  │ 3. Calculate smart concessions    │  │
│  │ 4. Final decision: accept/counter/reject │
│  └───────────────────────────────────┘  │
└──────────────┬──────────────────────────┘
               │
               ↓
         NegotiationAction
         (JSON)
```

**Why This Works:**
- LLM provides **reasoning & context awareness**
- Deterministic logic ensures **reproducible results** & **compliance**
- No stochasticity → judges can replicate scores

---

## ⚙️ Action Space

```python
class NegotiationAction(Action):
    move: str  # "propose" | "accept" | "reject" | "counter"
    offer: Dict[str, Any]  # { price, payment_terms, support_tier, sla }
    justification: str  # Agent's reasoning
    split_products: Optional[List[str]]  # For bundle scenarios
```

### Validation:
- `offer` must be **non-empty dict**
- `price` must be **positive**
- `payment_terms` must be in {net-30, net-45, net-60, net-90}
- `sla` must be ∈ [99.0, 100.0]

---

## 👁️ Observation Space

```python
class NegotiationObservation(Observation):
    vendor_response: str  # "accepted" | "rejected" | "countered" | "walkaway"
    current_offer: Dict[str, Any]
    vendor_message: str
    round_number: int
    concessions_won: List[str]
    deal_value_so_far: float
    available_moves: List[str]
```

---

## 📈 Reward System

**Per Step:**
- Valid move: +0.05
- Invalid move: -0.2
- Concession won: +0.05–0.15 (proportional)
- Vendor walkaway: -1.0

**Episode End:**
- Deal signed (all targets met): +0.40
- Deal signed (partial targets): +0.10–0.30
- No deal reached: 0.0

**Total Range**: [0.0, 1.0] (normalized)

---

## 📊 Grading (Evaluation)

### Standard Scenarios (SaaS, Cloud)

```
Final Score = 0.4 × price_grade + 
              0.2 × support_grade + 
              0.2 × payment_grade + 
              0.2 × sla_grade

where each grade ∈ [0.0, 1.0]
```

### Enterprise Bundle

```
Final Score = bundle_trap_grade
            = 1.0 if agent correctly splits CRM
            = 0.0 otherwise
```

---

## 🔧 Setup & Installation

### Prerequisites

- Python 3.10+
- HuggingFace API Token (for LLM inference)
- Git

### Step-by-Step

```bash
# 1. Clone repository
git clone <your-repo>
cd negotiation-env

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env and add HF_TOKEN from https://huggingface.co/settings/tokens

# 5. Verify setup
python -c "from environment import NegotiationEnvironment; print('✓ Setup complete')"
```

---

## 🚀 Running the System

### Option 1: Run LLM-Based Inference (Recommended)

```bash
export HF_TOKEN=your_token_here  # Or set in .env
python inference_llm.py
```

**Output:**
```
[START] task=saas_renewal env=procurement-negotiation-env model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action=propose(110000) reward=0.05 done=False error=null
[STEP] step=2 action=counter(105000) reward=0.08 done=False error=null
[STEP] step=3 action=accept(108000) reward=0.42 done=True error=null
[END] success=true steps=3 score=0.583 rewards=0.05,0.08,0.42
```

### Option 2: Launch Interactive Web UI

```bash
bash start.sh
```

Then open: **http://localhost:7860**

Features:
- Real-time negotiation table
- Manual offer input
- Vendor response visualization
- Deal value tracker

### Option 3: Run FastAPI Server (Development)

```bash
uvicorn server.app:app --reload --host 0.0.0.0 --port 8000
```

**Endpoints:**
- `POST /reset` — Start new negotiation
- `POST /step` — Execute one step
- `GET /state` — Get current state
- `GET /health` — Health check

---

## 🧱 Project Structure

```
.
├── inference.py              # Rule-based baseline agent
├── inference_llm.py          # LLM-based agent (Qwen2.5-72B)
├── models.py                 # Pydantic models
├── scenarios.py              # Scenario definitions
├── environment.py            # Negotiation simulator
├── graders.py                # Evaluation logic
├── gradio_ui.py              # Web UI
├── server/
│   └── app.py               # FastAPI server
├── openenv.yaml             # OpenEnv metadata
├── requirements.txt         # Dependencies
├── .env.example             # Environment variable template
├── .gitignore               # Git ignore rules
├── start.sh                 # Launch script
├── Dockerfile               # Container spec
└── README.md                # This file
```

---

## ✅ Key Files Explained

| File | Purpose |
|------|---------|
| **models.py** | Pydantic models for type-safe validation |
| **scenarios.py** | Hardcoded scenario dicts (ground truth) |
| **environment.py** | VendorSimulator + NegotiationEnvironment |
| **graders.py** | Deterministic scoring functions |
| **inference_llm.py** | LLM-based agent with hybrid logic |
| **server/app.py** | FastAPI REST API |
| **gradio_ui.py** | Interactive web interface |

---

## 🐳 Docker

### Build Image

```bash
docker build -t negotiation-env:latest .
```

### Run Container

```bash
docker run -p 8000:8000 -p 7860:7860 \
  -e HF_TOKEN=your_token_here \
  negotiation-env:latest
```

---

## ⚠️ Troubleshooting

### Issue: "No API key provided"

**Solution:** Set HF_TOKEN

```bash
export HF_TOKEN=your_token_here
# OR
cp .env.example .env
# Edit .env with your token
```

### Issue: "Connection refused" on /step

**Solution:** Start the FastAPI server first

```bash
bash start.sh
# OR
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

### Issue: Low scores (<0.2)

**Possible causes:**
- Agent not making valid offers (empty dict, invalid price)
- Early rejection (min_steps too high)
- Wrong task configuration

**Debug:**
```bash
# Run with verbose logging
python inference_llm.py 2>&1 | grep -E "\[START\]|\[STEP\]|\[END\]"
```

### Issue: "Request timeout"

**Solution:** Increase timeout or check LLM endpoint

```bash
# Check connectivity
curl -X GET http://localhost:8000/health
```

---

## 📚 References

### Key Concepts

- **Procurement Negotiation**: Multi-objective optimization across price, terms, SLA
- **Deterministic Vendor Simulator**: 30% concession logic, walkaway constraints
- **Hybrid AI**: LLM reasoning + deterministic decision-making
- **Bundle Trap**: Bundle discount trap in hard scenario (CRM: 25% off standalone vs. 15% in bundle)

### Scoring Formulas

**Price Grade:**
```
if achieved_price ≤ target_price:
    grade = 1.0
else:
    grade = (initial_price - achieved_price) / (initial_price - target_price)
```

**Support Grade:**
```
achieved_rank = SUPPORT_RANK[achieved_tier]
target_rank = SUPPORT_RANK[target_tier]
grade = (achieved_rank - min_rank) / (target_rank - min_rank)
```

---

## 📄 License

MIT License — See LICENSE file

---

## 👤 Author

**Sujat's Procurement Negotiation Agent**  
GitHub: [incognnitamood/AI-Procurement-Negotiation-Agent](https://github.com/incognnitamood/AI-Procurement-Negotiation-Agent)

---

## ✨ What Makes This Novel

1. **No existing OpenEnv for procurement** — Judges won't have seen this
2. **Realistic long trajectories** — 8–15 steps per task requires planning
3. **Multi-objective optimization** — 4 negotiable dimensions, trade-offs matter
4. **Deterministic yet challenging** — LLMs fail without strategy
5. **Production-ready** — Clean API, full validation, Dockerfile included

---

**Status**: ✅ Submission-Ready | 🎯 All Tasks Implemented | 🚀 Baseline Scores Validated
