import os
import json
import logging
import google.generativeai as genai
from app.config import settings

logger = logging.getLogger(__name__)

# Configure Google Gemini
genai.configure(api_key=settings.google_cloud_api_key)

def run_chatbot_agent(user_message: str, flights_summary: str) -> dict:
    """
    Invokes the Gemini 3.5 Flash model to answer user flight query
    based on the current active flight options in the database,
    and returns a structured JSON payload containing a friendly response
    and the extracted filter parameters.
    """
    logger.info(f"Invoking Gemini chatbot for message: {user_message}")
    
    prompt = f"""
You are an expert flight assistant for "Anywhere Flights" departing from SFO (San Francisco).
Below is the list of active flight options currently available in the database:
---
{flights_summary}
---

Your task:
1. Respond to the user's message in a friendly, conversational manner. Highlight flight options from the database that match their search criteria if applicable.
2. Extract the filter criteria they described:
   - "max_price": a float/int representing the maximum price limit (null if not specified).
   - "airlines": a list of strings of specific airline names mentioned (null if not specified).
   - "destination": a 3-letter IATA airport code (e.g. JFK, LHR, CDG) if they asked for a specific destination (null if not specified).

You MUST output your response strictly as a JSON object with the following structure:
{{
  "response_text": "Your markdown-formatted message answering the user.",
  "filters": {{
    "max_price": 800.0, // float or null
    "airlines": ["United Airlines", "Delta Air Lines"], // list of strings or null
    "destination": "LHR" // string of 3-letter code or null
  }}
}}

User message: "{user_message}"
"""

    try:
        model = genai.GenerativeModel('gemini-3.1-flash-lite')
        response = model.generate_content(prompt)
        
        # Clean up response text in case it is wrapped in markdown JSON blocks
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        # Parse the JSON response
        result = json.loads(text)
        logger.info(f"Gemini response parsed successfully: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}")
        # Fallback response in case of API failure
        return {
            "response_text": f"Sorry, I encountered an error while processing your request: {str(e)}",
            "filters": {
                "max_price": None,
                "airlines": None,
                "destination": None
            }
        }
