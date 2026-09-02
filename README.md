# ⚡ grepo (grep repositories)

An intelligent agentic application built with the **Google Agent Development Kit (ADK)** and **Gemini 2.5/3.6** that queries, explores, evaluates, and remembers embedded software driver repositories across **GitHub** and **Codeberg**.

Targeted at modern embedded software development (**C++20/C++23**, **Rust**, and **C**), the agent helps developers instantly locate reference driver implementations for hardware platforms like **STM32**, **ARM Cortex-M**, **RP2040**, **ESP32**, and **bare-metal/RTOS** systems.

---

## 🚀 Key Features

* **Multi-Platform Search**: Queries code repositories on **GitHub** and **Codeberg** for reference drivers and HAL implementations.
* **Language Filtering**: Native support for searching **Modern C++ (C++20/C++23)**, **Rust (embedded-hal)**, and **C**.
* **Direct Deep File Links**: Inspects git file trees recursively to provide direct GitHub/Codeberg links to specific driver headers, source files, and implementation files (`.hpp`, `.cpp`, `.rs`, `.h`, `.c`).
* **Repository Metadata & Quality Metrics**:
  * ⭐ **GitHub / Codeberg Stars**
  * 📅 **Last Commit / Push Date**
  * 🏷️ **Latest Release Version & Publication Date**
* **Confidence Scoring Algorithm**:
  * **90%+ Match (High Confidence)**: Modern C++20/23 concepts, `std::span`, zero-cost abstractions, RAII, DMA support, or idiomatic Rust `embedded-hal` implementations targeted specifically to the requested MCU.
  * **30%–50% Match (Partial Match)**: Legacy C++98/C++11, generic Arduino wrappers, or non-matching hardware targets.
* **Cross-Session Long-Term Memory (Vertex AI Memory Bank)**: Automatically registers discovered repositories into a managed **Vertex AI Memory Bank**. Previously found repositories are recalled and checked first on subsequent queries.
* **GitHub-Styled Web Chat UI**: Built with FastAPI, A2A protocol proxy, GitHub Octicon design aesthetics, markdown parsing, and interactive **Language & Site Dropdown Filters**.

---

## 🛠️ Architecture

```
embedded-driver-finder/
├── app/                        # Agent backend (ADK + Vertex AI Memory Bank)
│   ├── agent.py                # Core agent logic, tools (search_code_repositories), and Memory callback
│   ├── fast_api_app.py         # Agent Engine FastAPI entrypoint
│   └── app_utils/              # Services and Vertex AI Memory Bank wiring
├── frontend/                   # Web Chat UI & FastAPI Proxy
│   ├── main.py                 # FastAPI A2A client proxy with credentials refresher
│   ├── static/
│   │   └── index.html          # GitHub-styled UI with Language & Platform dropdowns & Marked.js
│   └── requirements.txt        # Frontend dependencies
├── pyproject.toml              # Agent dependencies (ADK, google-genai)
└── agents-cli-manifest.yaml   # Manifest for agents-cli deployment
```

---

## 🚦 Quick Start

### 1. Run the Frontend Locally

```bash
cd frontend
export AGENT_ENGINE_RESOURCE_NAME="projects/948085680099/locations/us-east1/reasoningEngines/7392007877445025792"
export AGENT_DIRECTORY="app"
python3 main.py
```

Open `http://localhost:8080` in your web browser.

### 2. Search For Drivers

Select your preferred **Language** (C++, Rust, C) and **Platform** (GitHub, Codeberg), then enter queries like:
* *"Find me a SPI NOR Flash driver for STM32"*
* *"I2C sensor driver for RP2040 using C++20 concepts"*
* *"CAN bus driver in Rust for STM32F4"*

---

## ☁️ Deployment & Memory Bank

Deployed to **Vertex AI Agent Runtime** using `agents-cli`:

```bash
agents-cli deploy
```

Integrated with **Vertex AI Memory Bank** for cross-session entity extraction and recall.
