#!/usr/bin/env python3
"""
Text-to-Speech Synthesis Script using Azure Speech Service.

Reads a text file where each line represents an utterance to synthesize.
Generates WAV files for each combination of voice model and speech rate.
Lines starting with '#' are skipped (comments).

Usage:
    python synthetize.py <input_file.txt>

Environment variables required:
    SPEECH_KEY - Azure Speech Service subscription key
    ENDPOINT - Azure Speech Service endpoint (e.g., https://YourServiceRegion.api.cognitive.microsoft.com)
"""

import os
import sys
import argparse
import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv
load_dotenv(override=True)

# Voice models to use for synthesis
VOICE_MODELS = [
    "en-US-Ava:DragonHDOmniLatestNeural",
    # "en-US-Andrew:DragonHDOmniLatestNeural",
    # "en-US-Ava3:DragonHDLatestNeural",
]

# Speech rates to use
# RATES = [1.0, 1.3]
RATES = [1.0]

# Output directory
OUTPUT_DIR = "tts-out"

# Locale for speech synthesis
LOCALE = "cs-CZ"


def sanitize_filename(name: str) -> str:
    """Sanitize a string to be used as a filename."""
    return name.replace(":", "_").replace("/", "_").replace("\\", "_")


def create_ssml(text: str, voice_name: str, rate: float) -> str:
    """
    Create SSML markup for speech synthesis with specified voice and rate.
    
    Args:
        text: The text to synthesize
        voice_name: The voice model name
        rate: The speech rate (1.0 = normal, 1.1 = 10% faster)
    
    Returns:
        SSML string
    """
    # Rate in SSML can be specified as percentage (e.g., "110%" for 1.1x)
    rate_percent = int(rate * 100)
    
    ssml = f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
    <voice name="{voice_name}">
        <lang xml:lang="{LOCALE}">
            <prosody rate="{rate}">
                {text}
            </prosody>
        </lang>
    </voice>
</speak>"""
#     ssml = f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{LOCALE}">
#     <voice name="{voice_name}">
#         <lang xml:lang="{LOCALE}">
#                 {text}
#         </lang>
#     </voice>
# </speak>"""
    return ssml


def synthesize_text(
    speech_config: speechsdk.SpeechConfig,
    text: str,
    voice_name: str,
    rate: float,
    output_path: str
) -> bool:
    """
    Synthesize text to speech and save as WAV file.
    
    Args:
        speech_config: Azure Speech configuration
        text: The text to synthesize
        voice_name: The voice model name
        rate: The speech rate
        output_path: Path to save the WAV file
    
    Returns:
        True if synthesis was successful, False otherwise
    """
    # Configure audio output to file
    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)
    
    # Create synthesizer
    speech_synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=audio_config
    )
    
    # Create SSML with rate
    ssml = create_ssml(text, voice_name, rate)
    
    # Synthesize using SSML
    result = speech_synthesizer.speak_ssml_async(ssml).get()
    
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print(f"  ✓ Saved: {output_path}")
        return True
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        print(f"  ✗ Synthesis canceled: {cancellation_details.reason}")
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            if cancellation_details.error_details:
                print(f"    Error details: {cancellation_details.error_details}")
        return False
    else:
        print(f"  ✗ Unknown result: {result.reason}")
        return False


def read_utterances(file_path: str) -> list[tuple[int, str]]:
    """
    Read utterances from a text file, skipping comment lines.
    
    Args:
        file_path: Path to the input text file
    
    Returns:
        List of tuples (line_number, text) for non-comment lines
    """
    utterances = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            # Skip empty lines and comments (lines starting with #)
            if line and not line.startswith('#'):
                utterances.append((line_num, line))
    return utterances


def main():
    parser = argparse.ArgumentParser(
        description='Synthesize text utterances to speech using Azure Speech Service.'
    )
    parser.add_argument(
        'input_file',
        help='Path to the input text file (one utterance per line, lines starting with # are skipped)'
    )
    args = parser.parse_args()
    
    # Check environment variables
    speech_key = os.environ.get('SPEECH_KEY')
    endpoint = os.environ.get('ENDPOINT')
    
    if not speech_key:
        print("Error: SPEECH_KEY environment variable is not set.")
        print("Set it with: export SPEECH_KEY=your-speech-key")
        sys.exit(1)
    
    if not endpoint:
        print("Error: ENDPOINT environment variable is not set.")
        print("Set it with: export ENDPOINT=https://YourServiceRegion.api.cognitive.microsoft.com")
        sys.exit(1)
    
    # Check input file exists
    if not os.path.exists(args.input_file):
        print(f"Error: Input file not found: {args.input_file}")
        sys.exit(1)
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Configure Speech SDK
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, endpoint=endpoint)
    speech_config.speech_synthesis_language = LOCALE
    
    # Read utterances from file
    utterances = read_utterances(args.input_file)
    
    if not utterances:
        print("No utterances found in the input file (all lines are empty or comments).")
        sys.exit(0)
    
    print(f"Found {len(utterances)} utterance(s) to synthesize.")
    print(f"Voice models: {len(VOICE_MODELS)}")
    print(f"Rates: {RATES}")
    print(f"Total files to generate: {len(utterances) * len(VOICE_MODELS) * len(RATES)}")
    print("-" * 60)
    
    success_count = 0
    error_count = 0
    
    for line_num, text in utterances:
        print(f"\nLine {line_num}: \"{text[:50]}{'...' if len(text) > 50 else ''}\"")
        
        for voice_name in VOICE_MODELS:
            for rate in RATES:
                # Create filename: line{N}_{voice}_{rate}.wav
                voice_sanitized = sanitize_filename(voice_name)
                rate_str = str(rate).replace(".", "_")
                filename = f"line{line_num}_{voice_sanitized}_rate{rate_str}.wav"
                output_path = os.path.join(OUTPUT_DIR, filename)
                
                print(f"  Synthesizing with {voice_name} at rate {rate}...")
                
                if synthesize_text(speech_config, text, voice_name, rate, output_path):
                    success_count += 1
                else:
                    error_count += 1
    
    print("-" * 60)
    print(f"\nSynthesis complete!")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {error_count}")
    print(f"  Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
