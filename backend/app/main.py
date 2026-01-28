"""
FastAPI backend for Azure AI Voice Live assistant.
Provides WebSocket endpoints for real-time audio streaming and speech-to-speech interaction.
"""

import os
import asyncio
import json
import base64
import datetime
import logging
from typing import Dict, Any, Mapping, Optional, Union, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.ai.voicelive.aio import connect
from azure.ai.voicelive.models import (
    RequestSession,
    ServerEventType,
    ServerVad,
    AudioEchoCancellation,
    AzureStandardVoice,
    Modality,
    InputAudioFormat,
    OutputAudioFormat,
    FunctionTool,
    FunctionCallOutputItem,
    ItemType,
    ToolChoiceLiteral,
    # AudioInputTranscriptionSettings,
    ResponseFunctionCallItem,
    ServerEventConversationItemCreated,
    ServerEventResponseFunctionCallArgumentsDone,
    Tool,
)

from dotenv import load_dotenv
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    logger.info("Starting Voice Live Assistant Backend")
    yield
    logger.info("Shutting down Voice Live Assistant Backend")


# Initialize FastAPI app
app = FastAPI(
    title="Azure AI Voice Live Assistant API",
    description="Real-time speech-to-speech assistant with function calling",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Models
class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str


# Helper functions for function calling
def get_current_time(arguments: Optional[Union[str, Mapping[str, Any]]] = None) -> Dict[str, Any]:
    """Get the current time."""
    if isinstance(arguments, str):
        try:
            args = json.loads(arguments)
        except json.JSONDecodeError:
            args = {}
    elif isinstance(arguments, dict):
        args = arguments
    else:
        args = {}

    timezone = args.get("timezone", "local")
    now = datetime.datetime.now()

    if timezone.lower() == "utc":
        now = datetime.datetime.now(datetime.timezone.utc)
        timezone_name = "UTC"
    else:
        timezone_name = "local"

    formatted_time = now.strftime("%I:%M:%S %p")
    formatted_date = now.strftime("%A, %B %d, %Y")

    return {
        "time": formatted_time,
        "date": formatted_date,
        "timezone": timezone_name
    }


def get_current_weather(arguments: Union[str, Mapping[str, Any]]) -> Dict[str, Any]:
    """Get the current weather for a location."""
    if isinstance(arguments, str):
        try:
            args = json.loads(arguments)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse weather arguments: {arguments}")
            return {"error": "Invalid arguments"}
    elif isinstance(arguments, dict):
        args = arguments
    else:
        return {"error": "No arguments provided"}

    location = args.get("location", "Unknown")
    unit = args.get("unit", "celsius")

    # sleep for 4 seconds to simulate API call
    import time
    print("Entering sleep to simulate weather API call...")
    time.sleep(3)
    print("Exiting sleep...")

    # Mock weather data (in production, call a real weather API)
    weather_data = {
        "location": location,
        "temperature": 22 if unit == "celsius" else 72,
        "unit": unit,
        "condition": "Partly Cloudy",
        "humidity": 65,
        "wind_speed": 10,
    }

    return weather_data


def get_mpsv_info(arguments: Optional[Union[str, Mapping[str, Any]]] = None) -> Dict[str, Any]:
    """Get information about social benefits from MPSV (Ministry of Labour and Social Affairs)."""
    if isinstance(arguments, str):
        try:
            args = json.loads(arguments)
        except json.JSONDecodeError:
            args = {}
    elif isinstance(arguments, dict):
        args = arguments
    else:
        args = {}

    query = args.get("query", "")
    
    # TODO: Implement actual MPSV info retrieval

    # Read info from knowledge base file
    kb_file_path = os.path.join(os.path.dirname(__file__), "test-kb.txt")
    try:
        with open(kb_file_path, "r", encoding="utf-8") as f:
            info = f.read()
    except FileNotFoundError:
        logger.error(f"Knowledge base file not found: {kb_file_path}")
        info = ""

    import time
    print("Entering sleep to simulate weather API call...")
    time.sleep(6)
    print("Exiting sleep...")
    
    return {
        "info": info,
        "query": query  
    }

# Available functions for the assistant
AVAILABLE_FUNCTIONS: Dict[str, Callable[[Union[str, Mapping[str, Any]]], Mapping[str, Any]]] = {
    "get_current_time": get_current_time,
    "get_current_weather": get_current_weather,
    "get_mpsv_info": get_mpsv_info,
}

# Available locales for the assistant
AVAILABLE_LOCALES: Dict[str, Dict[str, str]] = {
    "en-US": {
        "id": "en-US",
        "name": "English",
        "flag": "🇺🇸",
        "description": "English (US)"
    },
    "cs-CZ": {
        "id": "cs-CZ",
        "name": "Čeština",
        "flag": "🇨🇿",
        "description": "Czech"
    },
}

DEFAULT_LOCALE_ID = "cs-CZ"

# Available voices for the assistant (grouped by locale)
AVAILABLE_VOICES: Dict[str, Dict[str, str]] = {
    # English voices
    "ava": {
        "id": "ava",
        "name": "Ava",
        "voice": "en-US-Ava:DragonHDLatestNeural",
        "locale": "en-US",
        "description": "Warm & friendly"
    },
    "andrew": {
        "id": "andrew",
        "name": "Andrew",
        "voice": "en-US-Andrew3:DragonHDLatestNeural",
        "locale": "en-US",
        "description": "Professional & calm"
    },
    # Czech voices
    "antonin": {
        "id": "antonin",
        "name": "Antonín",
        "voice": "en-US-Andrew3:DragonHDLatestNeural",
        "locale": "cs-CZ",
        "description": "Profesionální"
    },
    "vlasta": {
        "id": "vlasta",
        "name": "Ava-Omni",
        # "voice": "en-US-Ava3:DragonHDLatestNeural",
        "voice": "en-US-Ava:DragonHDOmniLatestNeural",
        "locale": "cs-CZ",
        "description": "Přátelská"
    },
}

DEFAULT_VOICE_ID = "vlasta"
DEFAULT_VOICE_BY_LOCALE: Dict[str, str] = {
    "en-US": "andrew",
    "cs-CZ": "vlasta",
}


async def wait_for_event(conn, wanted_types: set, timeout_s: float = 10.0, on_unhandled=None):
    """Wait until we receive any event whose type is in wanted_types."""
    async def _next():
        while True:
            evt = await conn.recv()
            if evt.type in wanted_types:
                return evt
            if on_unhandled:
                await on_unhandled(evt)

    return await asyncio.wait_for(_next(), timeout=timeout_s)


# API Routes
@app.get("/", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="healthy", version="1.0.0")


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse(status="healthy", version="1.0.0")


@app.get("/locales")
async def get_locales():
    """Get available locales/languages for the assistant."""
    return {
        "locales": list(AVAILABLE_LOCALES.values()),
        "default": DEFAULT_LOCALE_ID
    }


@app.get("/voices")
async def get_voices(locale: str = None):
    """Get available voices for the assistant, optionally filtered by locale."""
    if locale and locale in AVAILABLE_LOCALES:
        voices = [v for v in AVAILABLE_VOICES.values() if v["locale"] == locale]
        default = DEFAULT_VOICE_BY_LOCALE.get(locale, DEFAULT_VOICE_ID)
    else:
        voices = list(AVAILABLE_VOICES.values())
        default = DEFAULT_VOICE_ID
    
    return {
        "voices": voices,
        "default": default
    }


@app.websocket("/ws/voice")
async def websocket_voice_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time voice interaction.
    
    Handles:
    - Audio streaming from client
    - Azure VoiceLive connection
    - Function calling
    - Audio response streaming back to client
    """
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    # Get Azure configuration
    endpoint = os.environ.get("AZURE_VOICELIVE_ENDPOINT", "")
    model = os.environ.get("AZURE_VOICELIVE_MODEL", "")
    show_transcriptions = os.environ.get("AZURE_VOICELIVE_SHOW_TRANSCRIPTIONS", "True").lower() == "true"
    
    # Check for API key (optional - for local development fallback)
    api_key = os.environ.get("AZURE_VOICELIVE_API_KEY", "")
    
    if not endpoint:
        await websocket.send_json({
            "type": "error",
            "message": "Server configuration error: Missing endpoint"
        })
        await websocket.close()
        return
    if not model:
        await websocket.send_json({
            "type": "error",
            "message": "Server configuration error: Missing model"
        })
        await websocket.close()
        return

    # Use DefaultAzureCredential (supports managed identity, Azure CLI, environment variables, etc.)
    # Falls back to API key if explicitly provided
    if api_key:
        credential = AzureKeyCredential(api_key)
        logger.info("Using API key credential")
    else:
        credential = DefaultAzureCredential()
        logger.info("Using DefaultAzureCredential (managed identity)")

    logger.info(f"Connecting to endpoint {endpoint} with model {model}")
    
    # Wait for initial configuration from client (voice selection, proactive greeting)
    selected_voice_id = DEFAULT_VOICE_ID
    enable_proactive_greeting = False
    try:
        init_data = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
        init_message = json.loads(init_data)
        if init_message.get("type") == "init":
            # Voice selection
            if init_message.get("voice_id"):
                voice_id = init_message["voice_id"]
                if voice_id in AVAILABLE_VOICES:
                    selected_voice_id = voice_id
                    logger.info(f"Client selected voice: {selected_voice_id}")
                else:
                    logger.warning(f"Unknown voice ID: {voice_id}, using default")
            # Proactive greeting option
            enable_proactive_greeting = init_message.get("proactive_greeting", False)
            logger.info(f"Proactive greeting enabled: {enable_proactive_greeting}")
    except asyncio.TimeoutError:
        logger.info("No init message received, using default settings")
    except json.JSONDecodeError:
        logger.warning("Invalid init message, using default settings")
    
    try:
        # Connect to Azure VoiceLive
        async with connect(
            endpoint=endpoint,
            credential=credential,
            model=model,
        ) as voicelive_conn:
            
            # Setup session with selected voice
            await setup_session(voicelive_conn, selected_voice_id)
            
            # Send ready signal to client
            await websocket.send_json({
                "type": "ready",
                "message": "Voice assistant ready"
            })
            
            # Create tasks for bidirectional communication
            async def receive_from_client():
                """Receive audio from client and forward to VoiceLive."""
                try:
                    while True:
                        data = await websocket.receive_text()
                        message = json.loads(data)
                        
                        if message["type"] == "audio":
                            # Forward audio to VoiceLive
                            audio_base64 = message["data"]
                            await voicelive_conn.input_audio_buffer.append(audio=audio_base64)
                            
                        elif message["type"] == "stop_audio":
                            # Client stopped speaking
                            logger.info("Client stopped speaking")
                            
                except WebSocketDisconnect:
                    logger.info("Client disconnected")
                except Exception as e:
                    logger.error(f"Error receiving from client: {e}")
            
            # Track if proactive greeting has been sent
            proactive_greeting_sent = False
            
            async def send_to_client():
                """Receive events from VoiceLive and send to client."""
                nonlocal proactive_greeting_sent
                try:
                    async for event in voicelive_conn:
                        await handle_voicelive_event(event, voicelive_conn, websocket, show_transcriptions)
                        
                        # Trigger proactive greeting after session is ready
                        if (event.type == ServerEventType.SESSION_UPDATED 
                            and enable_proactive_greeting 
                            and not proactive_greeting_sent):
                            proactive_greeting_sent = True
                            logger.info("Triggering proactive greeting...")
                            try:
                                await voicelive_conn.response.create(
                                    additional_instructions="You say your greeting line."
                                )
                            except Exception as e:
                                logger.error(f"Failed to send proactive greeting: {e}")
                        
                except Exception as e:
                    logger.error(f"Error in VoiceLive event loop: {e}")
            
            # Run both tasks concurrently
            await asyncio.gather(
                receive_from_client(),
                send_to_client(),
                return_exceptions=True
            )
            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass


async def setup_session(connection, voice_id: str = DEFAULT_VOICE_ID):
    """Configure the VoiceLive session with function tools."""
    logger.info(f"Setting up VoiceLive session with voice: {voice_id}")
    
    # Get voice configuration
    voice_data = AVAILABLE_VOICES.get(voice_id, AVAILABLE_VOICES[DEFAULT_VOICE_ID])
    voice_config = AzureStandardVoice(name=voice_data["voice"], locale=voice_data["locale"], rate="1.0")
    
    # Turn detection configuration
    turn_detection_config = ServerVad(
        threshold=0.5,
        prefix_padding_ms=300,
        silence_duration_ms=500
    )
    
    # Define function tools
    function_tools: list[Tool] = [
        FunctionTool(
            name="get_current_time",
            description="Get the current time",
            parameters={
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "The timezone to get the current time for, e.g., 'UTC', 'local'",
                    }
                },
                "required": [],
            },
        ),
        FunctionTool(
            name="get_current_weather",
            description="Get the current weather in a given location",
            parameters={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g., 'San Francisco, CA'",
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "The unit of temperature to use",
                    },
                },
                "required": ["location"],
            },
        ),
        FunctionTool(
            name="get_mpsv_info",
            description="Get information about social benefits from MPSV (Ministry of Labour and Social Affairs of Czech Republic)",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The query about social benefits, e.g., 'příspěvek na bydlení', 'podpora v nezaměstnanosti'",
                    }
                },
                "required": [],
            },
        ),
    ]
    
    # Session configuration
    session_config = RequestSession(
        modalities=[Modality.AUDIO],

        instructions="""
            Jseš Eva, užitečná AI asistentka s přístupem k funkcím.
            Vždy používej funkce, když je to vhodné, abys poskytl přesné a aktuální informace.

            Vždy uvítej volajícího tímto textem na začátku konverzace:
                'Dobrý den, dovolali jste se na úřad práce k agendě sociálních dávek. V rámci zkvalitňování našich služeb bude tento hovor monitorován. Jsem Eva, virtuální asistentka. Snažím se být co nejpřesnější, ale i já se můžu zmýlit. Jaký je váš dotaz?'
            
            ## Odpovědi:
             - Když se tě zeptá na počasí, odpověž 'Hmm... musím se podívat.' nebo podobným výrokem a poté volej funkci get_current_weather.
             - Když se tě zeptá na čas, odpověž 'Zjištím to!' nebo podobným výrokem a poté volej funkci get_current_time.
             - Když se tě zeptá něco kolem sociálních dávek, odpověz "Vteřinku podívám se po <hlavní téma dotazu>" a poté zavolej funkci get_mpsv_info a získej potřebné informace, ze kterých můžeš odpovědět. Odpovídej POUZE z poznatků získaných z této funkce.
            
            Zahrň výsledky do své odpovědi přirozeně.

            ## Výstup:
             - výstup je syntetizován TTS hlasovým modelem
             - pro nejlepší výsledek syntézy, vždy přepisuj foneticky správně slova, např.:
                    - 'dávka sociální pomoci' jako "dáfka státní sociální pomoci' 
                    - 'superdávka' jako 'superdáfka'
                    - normalizuj datumy: 1.10.2025 -> prvního desátý dva tisíce dvacetpět


            Mluvíš POUZE česky.
        """,
        # instructions="""
        #     You are a helpful AI assistant with access to functions.
        #     Use the functions when appropriate to provide accurate, real-time information. 
        #     If you are asked about the weather, please respond with 'Hmm... let me check the weather for you.' or similar filler and then call the get_current_weather function. 
        #     If you are asked about the time, please respond with 'I will get the time for you.' or similar filler and then call the get_current_time function. 
        #     Explain when you're using a function and include the results in your response naturally. You ONLY speak in Czech.
        # """,
        # instructions="""
        #     You are a helpful AI assistant with access to functions.
        #     Use the functions when appropriate to provide accurate, real-time information. 
        #     If you are asked about the weather, please respond with summarizing the question to check understanding or similar filler and then call the get_current_weather function. 
        #     If you are asked about the time, please respond with 'I will get the time for you.' or similar filler and then call the get_current_time function. 
        #     Explain when you're using a function and include the results in your response naturally.
        # """,
        voice=voice_config,
        input_audio_format=InputAudioFormat.PCM16,
        output_audio_format=OutputAudioFormat.PCM16,
        input_audio_echo_cancellation=AudioEchoCancellation(),
        turn_detection=turn_detection_config,
        tools=function_tools,
        tool_choice=ToolChoiceLiteral.AUTO,
        # input_audio_transcription=AudioInputTranscriptionSettings(model="gpt-4o-transcribe", language="en"),
        input_audio_transcription=None,
    )
    
    await connection.session.update(session=session_config)
    logger.info("VoiceLive session configured")


async def handle_voicelive_event(event, voicelive_conn, websocket: WebSocket, show_transcriptions: bool = True):
    """Handle events from VoiceLive and send appropriate messages to client."""
    
    if event.type == ServerEventType.SESSION_UPDATED:
        logger.info(f"Session ready: {event.session.id}")
        await websocket.send_json({
            "type": "session_ready",
            "session_id": event.session.id
        })
    
    elif event.type == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED:
        logger.info("User started speaking")
        await websocket.send_json({
            "type": "user_started_speaking"
        })
        # Cancel any ongoing response
        try:
            await voicelive_conn.response.cancel()
        except:
            pass
    
    elif event.type == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STOPPED:
        logger.info("User stopped speaking")
        await websocket.send_json({
            "type": "user_stopped_speaking"
        })
    
    elif event.type == ServerEventType.RESPONSE_CREATED:
        logger.info("Assistant response created")
        await websocket.send_json({
            "type": "assistant_response_started"
        })
    
    elif event.type == ServerEventType.RESPONSE_AUDIO_DELTA:
        # Stream audio back to client
        audio_base64 = base64.b64encode(event.delta).decode("utf-8")
        await websocket.send_json({
            "type": "audio",
            "data": audio_base64
        })
    
    elif event.type == ServerEventType.RESPONSE_AUDIO_DONE:
        logger.info("Assistant finished speaking")
        await websocket.send_json({
            "type": "assistant_response_ended"
        })

    elif event.type == ServerEventType.RESPONSE_DONE:
        logger.info("Response complete")
        await websocket.send_json({
            "type": "response_complete"
        })
    
    elif event.type == ServerEventType.CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_COMPLETED:
        transcript = getattr(event, "transcript", "")
        logger.info(f"User said: {transcript}")
        if show_transcriptions:
            await websocket.send_json({
                "type": "user_transcript",
                "text": transcript
            })
    
    elif event.type == ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DONE:
        transcript = getattr(event, "transcript", "")
        logger.info(f"Assistant said: {transcript}")
        if show_transcriptions:
            await websocket.send_json({
                "type": "assistant_transcript",
                "text": transcript
            })
    
    elif event.type == ServerEventType.CONVERSATION_ITEM_CREATED:
        # Handle function calls
        if event.item.type == ItemType.FUNCTION_CALL:
            await handle_function_call(event, voicelive_conn, websocket, show_transcriptions)
    
    elif event.type == ServerEventType.ERROR:
        logger.error(f"VoiceLive error: {event.error.message}")
        await websocket.send_json({
            "type": "error",
            "message": event.error.message
        })


async def handle_function_call(conversation_created_event, voicelive_conn, websocket: WebSocket, show_transcriptions: bool = True):
    """Handle function call from the assistant."""
    if not isinstance(conversation_created_event, ServerEventConversationItemCreated):
        return
    
    if not isinstance(conversation_created_event.item, ResponseFunctionCallItem):
        return
    
    function_call_item = conversation_created_event.item
    function_name = function_call_item.name
    call_id = function_call_item.call_id
    previous_item_id = function_call_item.id
    
    logger.info(f"Function call: {function_name} (call_id: {call_id})")
    
    await websocket.send_json({
        "type": "function_call",
        "function": function_name
    })
    
    try:
        # Wait for arguments to be complete
        async def forward_event(evt):
            await handle_voicelive_event(evt, voicelive_conn, websocket, show_transcriptions)
        
        function_done = await wait_for_event(
            voicelive_conn,
            {ServerEventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DONE},
            on_unhandled=forward_event,
        )
        
        if not isinstance(function_done, ServerEventResponseFunctionCallArgumentsDone):
            return
        
        if function_done.call_id != call_id:
            return
        
        arguments = function_done.arguments
        logger.info(f"Function arguments: {arguments}")
        
        # Wait for response to be done
        await wait_for_event(
            voicelive_conn,
            {ServerEventType.RESPONSE_DONE},
            on_unhandled=forward_event,
        )
        
        # Execute function if available
        if function_name in AVAILABLE_FUNCTIONS:
            result = AVAILABLE_FUNCTIONS[function_name](arguments)
            logger.info(f"Function result: {result}")
            
            # Send result back to VoiceLive
            function_output = FunctionCallOutputItem(
                call_id=call_id,
                output=json.dumps(result)
            )
            
            await voicelive_conn.conversation.item.create(
                previous_item_id=previous_item_id,
                item=function_output
            )
            
            # Create new response to process the function result
            await voicelive_conn.response.create()
            
            await websocket.send_json({
                "type": "function_result",
                "function": function_name,
                "result": result
            })
        else:
            logger.error(f"Unknown function: {function_name}")
    
    except asyncio.TimeoutError:
        logger.error(f"Timeout waiting for function {function_name}")
    except Exception as e:
        logger.error(f"Error executing function {function_name}: {e}")


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
