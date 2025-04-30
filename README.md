# 🧠 Intelligent To-Do App

An intelligent, Claude-powered To-Do list app that estimates task time, audits instruction compliance with **AIMon**, and helps you manage your day — all through a clean, interactive Streamlit interface.

## ✨ Features

- ⏱️ **Automatic Time Estimation**: Claude AI estimates how long each task might take.
- ✅ **Task Status Management**: Track tasks as In Progress, Completed, or Past Due.
- 🔔 **Daily Summaries**: Get an intelligent overview of your day.
- 🧪 **Instruction Compliance Auditing** with **AIMon**.
- 🌐 **Timezone-Aware Scheduling** (default: Pacific Time).

---

## 🛠️ Try It Yourself

First, make sure you have:
- **Python 3.8+**
- **Anthropic** API key (for Claude)
- **AIMon** API key (for instruction compliance)

### 🔧 Step 1: Setup the project

```bash
# 1: Clone the repository and enter it
git clone https://github.com/aimonlabs/intelligent-todo-app.git
cd intelligent-todo-app

# 2: Create & activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3: Upgrade pip and install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 🚀 Step 2: Export the API keys and run the application

```bash
export AIMON_API_KEY="your-aimon-key-here" \
ANTHROPIC_API_KEY="your-anthropic-key-here" && \
python -m streamlit run streamlit_app.py
```
