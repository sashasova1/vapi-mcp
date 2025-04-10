# VAPI MCP Server

This is an MCP server that provides a tool for making outbound calls using the VAPI platform.

## Prerequisites

- Python 3.10 or higher
- Claude for Desktop installed

## Setup

1. Create and activate a virtual environment:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Unix or MacOS:
source venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create and configure `.env` file:

```bash
# Copy the template
cp .env.template .env

# Edit .env and add your credentials
VAPI_API_KEY=your_api_key_here
VAPI_PHONE_NUMBER_ID=your_phone_number_id_here
```

4. Configure MCP in Claude for Desktop (or other client that supports MCP):

Create or edit the configuration file at `AppData\Roaming\Claude\claude_desktop_config.json` (Windows) or the appropriate location for your OS:

```json
{
    "mcpServers": {
        "vapi_server": {
            "command": "\\ABSOLUTE\\PATH\\TO\\VENV\\FOLDER\\python.exe",
            "args": [
                "\\ABSOLUTE\\PATH\\TO\\PARENT\\FOLDER\\mcp_server.py"
            ]
        }
    }
}
```

Replace the paths with your actual paths:
- `\\ABSOLUTE\\PATH\\TO\\VENV\\FOLDER\\python.exe`: Path to your virtual environment's Python executable
- `\\ABSOLUTE\\PATH\\TO\\PARENT\\FOLDER\\mcp_server.py`: Path to your mcp_server.py file

## Usage

1. Start the server:

```bash
python mcp_server.py
```

2. In Claude for Desktop, you can now use the `make_call` tool with parameters:
   - `phone_number`: The phone number to call in E.164 format (e.g., +12345678900)
   - `task`: The task or prompt for the call (e.g., 'make an appointment for next Wednesday')

Example:
```json
{
    "phone_number": "+12345678900",
    "task": "Schedule a dental appointment for next Wednesday"
}
```