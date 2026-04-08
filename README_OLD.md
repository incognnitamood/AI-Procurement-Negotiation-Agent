Here’s a clean, submission-ready **README.md** you can copy-paste:

---

# 🧠 Negotiation Environment (LLM / RL Compatible)

## 📌 Overview

This project implements a **deterministic negotiation simulation environment** designed for training and evaluating agents (rule-based, RL, or LLM-driven) in structured business negotiation scenarios.

The environment models realistic negotiations involving:

* Price bargaining
* Support tiers
* Payment terms
* SLA agreements
* Strategic behaviors (e.g., bundle splitting)

It provides:

* A **step-based interaction loop**
* Structured **action and observation spaces**
* A **grading system** for evaluating negotiation performance

---

## 🎯 Motivation

Negotiation is a **multi-objective decision-making problem** involving trade-offs across multiple variables.

This environment enables:

* Testing **automated negotiation agents**
* Evaluating **LLM reasoning strategies**
* Experimenting with **reinforcement learning policies**
* Studying **strategic behaviors** like concession planning and bundle splitting

---

## 🧩 Scenarios

The environment includes three predefined negotiation scenarios:

### 1. SaaS Renewal

* Focus: price reduction + improved terms
* Variables: price, support tier, payment terms, SLA

### 2. Cloud Infrastructure Deal

* Focus: long-term contract optimization
* Variables: price, SLA, payment flexibility

### 3. Enterprise Bundle

* Focus: strategic negotiation
* Special behavior: **bundle trap**
* Optimal strategy: splitting CRM from bundle

---

## ⚙️ Action Space

Each step, the agent produces a `NegotiationAction`:

```python
{
    "move": "counter" | "accept" | "walkaway",
    "offer": {
        "price": float,
        "support_tier": str,
        "payment_terms": str,
        "sla": float
    },
    "justification": str,
    "split_products": Optional[List[str]]
}
```

### Notes:

* `offer` must be a non-empty dictionary
* `price` must be **positive**
* `split_products` is used in bundle scenarios

---

## 👁️ Observation Space

The agent receives a `NegotiationObservation`:

```python
{
    "current_offer": Dict,
    "history": List[Dict],
    "round_number": int,
    "max_rounds": int,
    "done": bool
}
```

### Includes:

* Latest vendor offer
* Full negotiation history
* Current round info

---

## 🔄 Environment Dynamics

* Max rounds: **10**
* Vendor behavior:

  * Responds with **~30% concession toward midpoint**
  * Never goes below internal walkaway constraints
* Buyer actions:

  * `counter` → continue negotiation
  * `accept` → finalize deal
  * `walkaway` → terminate negotiation

---

## 🏆 Reward System

### Step Rewards:

* Valid move → `+0.05`
* Invalid move → `-0.2`
* Accept → final score
* Walkaway → `-1.0`

---

## 📊 Evaluation (Grading)

Final outcomes are scored in **[0, 1]** using weighted metrics:

### Standard Scenarios:

* Price → **0.4**
* Support → **0.2**
* Payment → **0.2**
* SLA → **0.2**

### Enterprise Bundle:

* Strategy-based:

  * Correct split (CRM) → **1.0**
  * Otherwise → **0.0**

---

## 🧪 Example Usage

```python
env = NegotiationEnv(scenario)

obs = env.reset()

done = False
while not done:
    action = agent(obs)
    obs, reward, done, info = env.step(action)
```

---

## 🧱 Project Structure

```
.
├── models.py        # Data models (Pydantic)
├── scenarios.py     # Scenario definitions
├── environment.py   # Negotiation simulator
├── graders.py       # Evaluation logic
├── README.md        # Documentation
```

---

## ⚠️ Assumptions

* Field names use:

  * `payment_terms` instead of `payment`
  * `support_tier` instead of `support`
* SLA range assumed: **99.0 – 100.0**
* Deterministic vendor behavior (no randomness)

---

## 📈 Baseline Performance

| Strategy            | Expected Score |
| ------------------- | -------------- |
| Random actions      | 0.2 – 0.4      |
| Greedy (price only) | 0.5 – 0.7      |
| Multi-objective     | 0.7 – 0.9      |
| Optimal strategy    | ~1.0           |

---

## 🚀 Extensions

* Plug in **LLM-based agents**
* Train **RL policies (PPO, DQN, etc.)**
* Add **stochastic vendor behavior**
* Expand to **multi-agent negotiations**

---

## ✅ Summary

This environment provides a:

* Structured
* Extensible
* Realistic

framework for experimenting with **automated negotiation strategies**.

---


