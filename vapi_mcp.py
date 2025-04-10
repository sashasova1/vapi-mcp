from typing import Dict, Any, Optional, List
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
    description="Make an outbound call using VAPI. Args: phone_number (E.164 format), task (call prompt), assistant_name (optional, if not provided a custom assistant will be created)"
)
async def make_call(phone_number: str, task: str, assistant_name: Optional[str] = None) -> Dict[str, Any]:
    """Make an outbound call using VAPI.

    Args:
        phone_number: The phone number to call in E.164 format
        task: The task or prompt for the call
        assistant_name: Optional name of a predefined assistant to use

    Returns:
        Dictionary containing the call status and details
    """
    logger.info("Making call to %s with task: %s", phone_number, task)
    
    try:
        # Prepare the call payload
        call_payload = {
            "phoneNumberId": phone_number_id,
            "customer": {
                "number": phone_number
            }
        }

        if assistant_name:
            # Look up assistant ID by name using list_assistants MCP tool
            logger.info("Looking up assistant with name: %s", assistant_name)
            assistants_response = await list_assistants()
            
            if assistants_response["status"] != "success":
                return {
                    "status": "error",
                    "message": f"Failed to fetch assistants: {assistants_response.get('message')}"
                }
            
            assistant = next(
                (a for a in assistants_response["assistants"] if a.get("name") == assistant_name), 
                None
            )
            
            if not assistant:
                logger.error("Assistant with name '%s' not found", assistant_name)
                return {
                    "status": "error",
                    "message": f"Assistant with name '{assistant_name}' not found"
                }
            
            assistant_id = assistant.get("id")
            logger.info("Found assistant ID: %s", assistant_id)
            
            # Use predefined assistant
            call_payload["assistantId"] = assistant_id
            # Add task as a user message that the assistant will see
            call_payload["assistantOverrides"] = {
                "model": {
                    "provider": "openai",
                    "model": "gpt-4o",
                    "messages": [
                        {
                            "role": "user",
                            "content": f"Please help with this task: {task}"
                        }
                    ]
                }
            }
        else:
            # Create a custom assistant for this call
            logger.info("Creating custom assistant for the call")
            call_payload["assistant"] = {
                "model": {
                    "provider": "openai",
                    "model": "gpt-4o",
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
            }

        # Create the call using VAPI
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.vapi.ai/call",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json=call_payload
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
            logger.error("Response details: %s", response_data)  # Added detailed error logging
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

def calculate_cost_per_minute(assistant: Dict[str, Any]) -> float:
    """Calculate estimated cost per minute for an assistant.
    
    Args:
        assistant: Assistant configuration dictionary
        
    Returns:
        Estimated cost per minute in USD
    """
    # Base VAPI cost per minute
    cost = 0.05
    
    # Add STT cost
    transcriber = assistant.get("transcriber", {})
    stt_provider = transcriber.get("provider", "").lower()
    if stt_provider == "deepgram":
        cost += 0.01
    elif stt_provider == "assembly-ai":
        cost += 0.008
        
    # Add TTS cost
    voice = assistant.get("voice", {})
    tts_provider = voice.get("provider", "").lower()
    if tts_provider == "cartesia":
        cost += 0.022
        
    return cost

@mcp.tool(
    name="get_phone_number",
    description="Get details of a VAPI phone number by ID."
)
async def get_phone_number(phone_number_id: str) -> Dict[str, Any]:
    """Get details of a VAPI phone number.

    Args:
        phone_number_id: ID of the phone number to fetch

    Returns:
        Dictionary containing the phone number details
    """
    logger.info("Fetching phone number details for ID: %s", phone_number_id)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"https://api.vapi.ai/phone-number/{phone_number_id}",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
            )

            response_data = response.json()
            
            if response.status_code == 200:
                return {
                    "status": "success",
                    "phone_number": response_data
                }
            
            logger.error("Failed to fetch phone number details: %s", response.text)
            return {
                "status": "error",
                "message": f"Failed to fetch phone number details: {response.text}"
            }
    except Exception as e:
        logger.error("Error fetching phone number details: %s", str(e))
        return {
            "status": "error",
            "message": f"Error fetching phone number details: {str(e)}"
        }

@mcp.tool(
    name="list_assistants",
    description="List all VAPI assistants. Returns a list of assistants with their details, associated phone numbers, and estimated cost per minute."
)
async def list_assistants() -> Dict[str, Any]:
    """List all VAPI assistants.

    Returns:
        Dictionary containing the list of assistants and their details including estimated cost per minute
    """
    logger.info("Fetching list of VAPI assistants")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://api.vapi.ai/assistant",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
            )

            response_data = response.json()
            
            if response.status_code == 200:
                # Add cost estimation and fetch phone numbers for each assistant
                for assistant in response_data:
                    assistant["estimated_cost_per_minute"] = calculate_cost_per_minute(assistant)
                    
                    # Get associated phone numbers
                    phone_numbers_response = await client.get(
                        "https://api.vapi.ai/phone-number",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json"
                        }
                    )
                    
                    if phone_numbers_response.status_code == 200:
                        phone_numbers = phone_numbers_response.json()
                        # Filter phone numbers associated with this assistant
                        assistant["phone_numbers"] = [
                            pn for pn in phone_numbers 
                            if pn.get("assistantId") == assistant.get("id")
                        ]
                    else:
                        logger.warning("Failed to fetch phone numbers for assistant %s", assistant.get("id"))
                        assistant["phone_numbers"] = []
                
                logger.info("Successfully retrieved %d assistants", len(response_data))
                return {
                    "status": "success",
                    "message": f"Found {len(response_data)} assistants",
                    "assistants": response_data
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