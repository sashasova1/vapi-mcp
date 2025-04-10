from typing import Dict, Any, Optional
import os
import httpx
import logging
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize FastMCP server with proper configuration
mcp = FastMCP(
    name="vapi",
    version="1.0.0",
    description="VAPI integration for making AI-powered phone calls"
)

# Get VAPI credentials
api_key = os.getenv("VAPI_API_KEY")
phone_number_id = os.getenv("VAPI_PHONE_NUMBER_ID")

if not api_key or not phone_number_id:
    raise ValueError("VAPI_API_KEY and VAPI_PHONE_NUMBER_ID must be set in .env file")

logger.info("VAPI tool initialized with phone number ID: %s", phone_number_id)

@mcp.tool(
    name="make_call",
    description="Make an outbound call using VAPI. Args: phone_number (E.164 format), task (call prompt)"
)
async def make_call(phone_number: str, task: str) -> Dict[str, Any]:
    """Make an outbound call using VAPI.

    Args:
        phone_number: The phone number to call in E.164 format
        task: The task or prompt for the call

    Returns:
        Dictionary containing the call status and details
    """
    logger.info("Making call to %s with task: %s", phone_number, task)
    
    try:
        # Create the call using VAPI
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.vapi.ai/call",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "assistant": {
                        "model": {
                            "provider": "openai",
                            "model": "gpt-4",
                            "messages": [
                                {
                                    "role": "system",
                                    "content": f"You are an AI assistant making calls on behalf of a client. Your task is: {task}. Be friendly, professional, and natural during the call."
                                }
                            ],
                            "temperature": 0.7
                        },
                        "voice": {
                            "provider": "cartesia",
                            "voiceId": "c45bc5ec-dc68-4feb-8829-6e6b2748095d",
                            "model": "sonic-english"
                        },
                        "endCallMessage": "Thanks, take care!",
                        "name": "Assistant",
                        "transcriber": {
                            "provider": "deepgram",
                            "model": "nova-2",
                            "language": "en"
                        },
                        "clientMessages": [
                            "hang",
                            "transcript",
                            "function-call",
                            "conversation-update",
                            "speech-update",
                            "metadata"
                        ],
                        "serverMessages": [
                            "end-of-call-report",
                            "status-update",
                            "hang",
                            "function-call"
                        ],
                        "maxDurationSeconds": 120,
                        "backgroundDenoisingEnabled": False,
                        "startSpeakingPlan": {
                            "waitSeconds": 1.2,
                            "transcriptionEndpointingPlan": {
                                "onPunctuationSeconds": 0.4
                            }
                        },
                        "stopSpeakingPlan": {
                            "backoffSeconds": 2
                        }
                    },
                    "phoneNumberId": phone_number_id,
                    "customer": {
                        "number": phone_number
                    }
                }
            )

            response_data = response.json()
            
            if response.status_code in (200, 201):
                if response_data.get("status") == "queued":
                    logger.info("Call queued successfully with ID: %s", response_data.get("id"))
                    return {
                        "status": "success",
                        "message": "Call has been queued",
                        "call_id": response_data.get("id"),
                        "details": response_data
                    }
                else:
                    logger.error("Call failed with status: %s", response_data.get("status"))
                    return {
                        "status": "error",
                        "message": f"Call failed with status: {response_data.get('status')}",
                        "details": response_data
                    }
            
            logger.error("HTTP request failed with status: %d", response.status_code)
            return {
                "status": "error",
                "message": f"HTTP request failed with status: {response.status_code}",
                "details": response_data
            }
    except httpx.HTTPError as e:
        logger.error("HTTP error occurred: %s", str(e))
        return {
            "status": "error",
            "message": f"HTTP error occurred: {str(e)}"
        }
    except Exception as e:
        logger.error("Unexpected error occurred: %s", str(e))
        return {
            "status": "error",
            "message": f"Unexpected error occurred: {str(e)}"
        }

def main():
    """Start the MCP server."""
    logger.info("Starting VAPI MCP server...")
    try:
        mcp.run(transport='stdio')
    except Exception as e:
        logger.error("Failed to start MCP server: %s", str(e))
        raise

if __name__ == "__main__":
    main() 