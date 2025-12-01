# Agent Module

This module is the core of the backend, providing a powerful and flexible interface for managing the entire machine learning workflow, from data ingestion to model training and inference. It is designed to be interacted with via natural language, using an AI agent to translate user requests into function calls.

## Overview

The `agent` module exposes a comprehensive set of tools for:

*   **Data Management**: Ingesting raw sensor data, creating labeled datasets, and generating AI-powered metadata and quality analysis.
*   **Model Training**: Training custom CNN and ResNet models on the prepared datasets, complete with progress tracking and report generation.
*   **Inference**: Running trained models on new data to get predictions.
*   **Analysis**: Comparing models, explaining results, and providing workflow guidance.

## Key Components

### `damage_lab_agent.py`

This is the heart of the module. It defines all the functions (tools) available to the AI agent. These tools are direct Python function calls that interact with other parts of the application, such as the `database`, `training`, and `testing` modules. It also contains the main system prompt (`SYSTEM_INSTRUCTION`) that instructs the AI on how to behave, what its capabilities are, and how to interact with the user.

### `chat_runner.py`

This script provides a standalone, command-line chat interface for interacting with the `damage_lab_agent`. It uses the OpenAI API to create a chat experience where the user can type commands in natural language (e.g., "train a model on the crushcore data"), and the agent will execute the appropriate tools. It dynamically generates the tool specifications for the OpenAI API based on the functions and docstrings in `damage_lab_agent.py`.

### `adk_runner.py`

This is a runner script for launching the `damage_lab_agent` with the Google Agent Development Kit (ADK) web interface. This provides a web-based UI for interacting with the agent, as an alternative to the command-line `chat_runner.py`.

## How It Works

The primary workflow is centered around an AI agent (powered by a large language model like GPT) that is given access to the tools defined in `damage_lab_agent.py`. When a user provides a prompt, the agent decides which tool to use, extracts the necessary parameters, and executes the function. This allows for a very flexible and user-friendly way to control the application without needing to write any code.