# Agentic TODO Application

An intelligent TODO list application built with AG2 agentic framework that features smart time estimation and reminders.

## Features

- Create, read, update, and delete tasks
- Intelligent time estimation using Claude API
- Smart reminder system based on task duration and due date
- Simple, modern UI built with Streamlit

## Setup and Installation

1. Install dependencies:
```
pip install -r requirements.txt
```

2. Set your Anthropic API key as an environment variable:
```
export ANTHROPIC_API_KEY="your_api_key_here"
```

3. Run the Streamlit application:
```
streamlit run streamlit_app.py
```
Or use the provided script:
```
bash run_streamlit.sh
```

## How It Works

- **Task Creation**: Just enter a task description - Claude API automatically estimates how long it will take
- **Smart Due Dates**: Due dates are calculated based on estimated completion time
- **Intelligent Reminders**: The app sends reminders when it's time to start a task
- **Task Management**: Edit, complete, or delete tasks with intuitive controls

## Project Structure

- `streamlit_app.py`: Streamlit UI implementation
- `todo_agent.py`: AG2 agent implementation for task management
- `task_model.py`: Data models for tasks
- `claude_service.py`: Service for interacting with Claude API
- `reminder_service.py`: Service for handling task reminders (integrated into Streamlit) 