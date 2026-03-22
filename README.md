![ezgif com-animated-gif-maker](https://github.com/user-attachments/assets/8fca0395-06d6-44de-8343-6827b7218ce1)

# Reachy Mini Cooking Assistant

An AI-driven cooking assistant for the Reachy Mini robot, leveraging on-device Ollama models running on Jetson Orin. The system combines OpenAI ASR, multimodal vision pipelines, automated food ordering via DoorDash, and accessibility-focused design, including deaf-accessible interaction capabilities.

![Reachy Mini Dance](docs/assets/reachy_mini_dance.gif)

## Table of contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the app](#running-the-app)
- [LLM tools](#llm-tools-exposed-to-the-assistant)
- [Advanced features](#advanced-features)
- [Contributing](#contributing)
- [License](#license)

## Overview

- Real-time audio conversation loop powered by the OpenAI realtime API and `fastrtc` for low-latency streaming.
- Vision processing Nvidia Cosmos v2 running on an Nvidia Brev Server
- Voice is associated with signs for deaf people

## Architecture

The app follows a layered architecture connecting the user, AI services, and robot hardware:

<p align="center">
  <img src="docs/assets/diagram.png" alt="Architecture Diagram" width="600"/>
</p>

## Installation

> [!IMPORTANT]
> Before using this app, you need to install [Reachy Mini's SDK](https://github.com/pollen-robotics/reachy_mini/).<br>
> Windows support is currently experimental and has not been extensively tested. Use with caution.

<details open>
<summary><b>Using uv (recommended)</b></summary>

Set up the project quickly using [uv](https://docs.astral.sh/uv/):

```bash
# macOS (Homebrew)
uv venv --python /opt/homebrew/bin/python3.12 .venv

# Linux / Windows (Python in PATH)
uv venv --python python3.12 .venv

source .venv/bin/activate
uv sync
```

## Running the app

Activate your virtual environment, then launch:

```bash
reachy-mini-conversation-app
```

> [!TIP]
> Make sure the Reachy Mini daemon is running before launching the app. If you see a `TimeoutError`, it means the daemon isn't started. See [Reachy Mini's SDK](https://github.com/pollen-robotics/reachy_mini/) for setup instructions.

## Acknowledgement

This repo was forked from the original [reach-mini-conversation-app](https://github.com/pollen-robotics/reachy_mini_conversation_app).

## License

Apache 2.0
