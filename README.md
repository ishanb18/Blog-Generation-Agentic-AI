<div align="center">

<img src="https://img.shields.io/badge/LangGraph-Powered-6C63FF?style=for-the-badge&logo=python&logoColor=white" />
<img src="https://img.shields.io/badge/Mistral%20AI-LLM-FF7043?style=for-the-badge&logo=openai&logoColor=white" />
<img src="https://img.shields.io/badge/Streamlit-UI-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" />
<img src="https://img.shields.io/badge/Gemini-Image%20Gen-4285F4?style=for-the-badge&logo=google&logoColor=white" />
<img src="https://img.shields.io/badge/Tavily-Web%20Search-00BFA5?style=for-the-badge" />

<br/><br/>

# 🤖 Blog Generation Agentic AI

### A production-grade, multi-agent blog writing pipeline powered by **LangGraph**, **Mistral AI**, and **Google Gemini**

<br/>

> _Enter a topic. Watch agents research, plan, write, and illustrate a complete blog — automatically._

<br/>

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/ishanb18/Blog-Generation-Agentic-AI/pulls)

</div>

---

## ✨ What This Does

This project implements a **fully autonomous, agentic blog writing system** that takes a single topic as input and produces a polished, illustrated technical blog post — end to end — without any manual intervention.

The system is built as a **LangGraph state graph** with specialized agents cooperating in a dynamic pipeline:

```
Topic Input
    │
    ▼
┌───────────┐     needs_research=true      ┌────────────┐
│  Router   │ ────────────────────────────► │  Research  │
│  Agent    │                               │  (Tavily)  │
└───────────┘                               └──────┬─────┘
    │ needs_research=false                         │
    │◄─────────────────────────────────────────────┘
    ▼
┌─────────────┐
│ Orchestrator│  Plans 5–9 structured sections
│   (Planner) │
└──────┬──────┘
       │ Fan-out (parallel)
       ▼
┌────────────────────────────────────────────┐
│  Worker  │  Worker  │  Worker  │  Worker   │  ← Parallel section writers
└──────────┴──────────┴──────────┴───────────┘
       │ Reduce
       ▼
┌──────────────────────────────────────────────────────────┐
│                   Reducer Subgraph                        │
│  merge_content → decide_images → generate_and_place_imgs  │
└──────────────────────────────────────────────────────────┘
       │
       ▼
  📄 Final Blog (.md) + 🖼️ AI-generated images
```

---

## 🚀 Key Features

| Feature | Description |
|---|---|
| 🧭 **Smart Router** | Automatically classifies topics as `closed_book`, `hybrid`, or `open_book` and decides if web research is needed |
| 🔍 **Web Research** | Searches the web via **Tavily** for up-to-date evidence, deduplicates and filters by recency |
| 🗂️ **Structured Planning** | Orchestrator produces a typed `Plan` with 5–9 tasks, audience/tone metadata, and per-section constraints |
| ⚡ **Parallel Writing** | Worker agents write all sections **in parallel** using LangGraph's `Send` fan-out pattern |
| 🖼️ **AI Image Generation** | Uses **Gemini 2.5 Flash** to generate technical diagrams and inserts them inline into the blog |
| 📰 **News Roundup Mode** | Detects breaking/volatile topics and switches to citation-only, event-driven writing |
| 💾 **Blog Library** | Saves all generated blogs as `.md` files; load and re-read them from the sidebar |
| 📦 **Export** | Download the blog as raw Markdown or a ZIP bundle with all images included |
| 🎛️ **Streamlit UI** | Tabbed interface: Plan · Evidence · Preview · Images · Logs — with live streaming progress |

---

## 🏗️ Architecture

```
blog-generation-agentic-ai/
├── bwa_backend.py      # LangGraph graph definition (all agents + subgraph)
├── bwa_frontend.py     # Streamlit UI (streaming, tabs, blog library, export)
├── requirements.txt    # Python dependencies
├── .env.example        # API key template
├── .gitignore
└── README.md
```

### Agent Roles

| Agent | File | Responsibility |
|---|---|---|
| **Router** | `bwa_backend.py` | Decides research mode & web queries |
| **Researcher** | `bwa_backend.py` | Fetches + filters Tavily results |
| **Orchestrator** | `bwa_backend.py` | Generates structured blog plan |
| **Worker** | `bwa_backend.py` | Writes individual sections (parallel) |
| **Merge** | `bwa_backend.py` | Assembles sections in order |
| **Image Planner** | `bwa_backend.py` | Decides where images go + writes prompts |
| **Image Generator** | `bwa_backend.py` | Calls Gemini API, saves PNGs |
| **Streamlit App** | `bwa_frontend.py` | Streams progress, renders tabs, handles export |

---

## ⚙️ Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/ishanb18/Blog-Generation-Agentic-AI.git
cd Blog-Generation-Agentic-AI
```

### 2. Create a virtual environment

```bash
python -m venv myenv
# Windows
myenv\Scripts\activate
# macOS / Linux
source myenv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure API keys

Create a `.env` file in the project root (use `.env.example` as a template):

```env
# Required — Mistral AI (LLM backbone)
MISTRAL_API_KEY=your_mistral_api_key_here

# Optional — Tavily Web Search (enables open_book / hybrid research modes)
TAVILY_API_KEY=your_tavily_api_key_here

# Optional — Google Gemini (enables AI image generation)
GOOGLE_API_KEY=your_google_api_key_here
```

> **Get API Keys:**
> - Mistral AI: [console.mistral.ai](https://console.mistral.ai)
> - Tavily: [tavily.com](https://tavily.com)
> - Google Gemini: [aistudio.google.com](https://aistudio.google.com)

### 5. Run the app

```bash
streamlit run bwa_frontend.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 🎮 Usage

1. **Enter a topic** in the sidebar text area  
   _Examples: "Transformer Self-Attention", "State of Multimodal LLMs in 2026", "Building RAG Pipelines"_

2. **Set the as-of date** (defaults to today) — used for recency filtering in research mode

3. Click **🚀 Generate Blog** and watch the agent pipeline execute live

4. Explore the **tabbed output:**
   - **🧩 Plan** — Structured outline with section details
   - **🔎 Evidence** — Web sources used (hybrid/open_book only)
   - **📝 Preview** — Rendered Markdown with embedded images
   - **🖼️ Images** — AI-generated diagrams
   - **🧾 Logs** — Raw streaming event log

5. **Download** your blog as `.md` or a full `.zip` bundle

---

## 🧠 Research Modes

The **Router agent** automatically selects the right mode:

| Mode | When Used | Research |
|---|---|---|
| `closed_book` | Timeless concepts (e.g. "What is LSTM?") | ❌ None |
| `hybrid` | Evergreen + needs current tools/examples | ✅ 45-day window |
| `open_book` | Breaking news / weekly roundups / "latest" | ✅ 7-day window only |

---

## 📦 Tech Stack

| Layer | Technology |
|---|---|
| **Orchestration** | [LangGraph](https://github.com/langchain-ai/langgraph) |
| **LLM** | [Mistral AI](https://mistral.ai) (`mistral-medium-latest`) |
| **Image Generation** | [Google Gemini](https://ai.google.dev) (`gemini-2.5-flash-image`) |
| **Web Search** | [Tavily](https://tavily.com) |
| **Data Validation** | [Pydantic v2](https://docs.pydantic.dev) |
| **Frontend** | [Streamlit](https://streamlit.io) |
| **Data Display** | [Pandas](https://pandas.pydata.org) |

---

## 🛣️ Roadmap

- [ ] Multi-model support (GPT-4o, Claude, Gemini Pro)
- [ ] Export to HTML / PDF
- [ ] Scheduled blog generation (cron)
- [ ] Vector store memory across blog sessions
- [ ] Custom tone / audience persona presets

---

## 🤝 Contributing

Contributions are welcome! Please open an issue first to discuss what you'd like to change.

```bash
# Fork → Clone → Branch → PR
git checkout -b feature/my-new-feature
git commit -m "feat: add my new feature"
git push origin feature/my-new-feature
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

<div align="center">

Made with ❤️ by **[Ishan Bansal](https://github.com/ishanb18)**

_If you found this useful, please ⭐ the repo!_

</div>
