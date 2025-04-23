import os
import tkinter as tk
import logging
import argparse
from todo_agent import TodoAgent
from ui import TodoAppUI

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Agentic TODO List Application")
    parser.add_argument('--storage', type=str, default='tasks.json', help='Path to task storage file')
    parser.add_argument('--api-key', type=str, help='Anthropic API key (can also be set with ANTHROPIC_API_KEY env var)')
    parser.add_argument('--aimon-key', type=str, help='AIMon API key (can also be set with AIMON_API_KEY env var)')
    args = parser.parse_args()
    
    # Get API keys from args or environment
    api_key = args.api_key or os.environ.get('ANTHROPIC_API_KEY')
    aimon_key = args.aimon_key or os.environ.get('AIMON_API_KEY')

    if not api_key:
        logger.warning( "Anthropic API key not provided. " \
                        "Please set ANTHROPIC_API_KEY environment variable or provide --api-key argument.")
    
    if not aimon_key:
        logger.warning( "AIMon API key not provided. " \
                        "Please set AIMON_API_KEY environment variable or provide ----aimon-key argument.")
        
    # Create the agent
    logger.info(f"Initializing TODO agent with storage at {args.storage}")
    todo_agent = TodoAgent(storage_path=args.storage, claude_api_key=api_key)
    
    # Create the UI
    root = tk.Tk()
    app = TodoAppUI(root, todo_agent)
    
    # Start the application
    logger.info("Starting TODO application")
    root.mainloop()

if __name__ == "__main__":
    main() 