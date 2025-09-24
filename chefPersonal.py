import os
import json
import re
import time
from typing import List, Dict, Any

from dotenv import load_dotenv
from PIL import Image
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
modelVersion = "gemini-2.0-flash"

def _parse_json_from_markdown(text: str) -> Any:
    """Extracts and parses JSON from markdown text."""
    try:
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1).strip()
            return json.loads(json_str)
        
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        
        return None
    except (json.JSONDecodeError, AttributeError):
        return None

def retry_with_backoff(api_call_func, *args, **kwargs):
    """
    Tries an API call with indefinite exponential retries.
    """
    delay = 2
    while True:
        try:
            return api_call_func(*args, **kwargs)
        except ResourceExhausted as e:
            print(f"Service is busy. Retrying in {delay} seconds...")
            time.sleep(delay)
        except Exception as e:
            raise e

def setup_ia():
    """Loads the API key and sets up the Google GenAI client."""
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError("The GOOGLE_API_KEY environment variable was not found.")

    genai.configure(api_key=api_key)


def detect_ingredients_with_quantities(image_path: str) -> List[Dict[str, Any]]:
    """Analyzes a food image and returns a list of detected ingredients."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"The image file was not found at: {image_path}")

    setup_ia()
    img = Image.open(image_path)
    
    system_prompt = (
        "You are a food expert. Analyze the image to identify all ingredients. "
        "Estimate the amount of each one. "
        "Return the response only as a JSON list of objects. "
        "Each object must have a key 'ingredient' (string) and a key 'amount' (an object with 'value' and 'unit'). "
        "Example: [{\"ingredient\": \"tomato\", \"amount\": {\"value\": 2, \"unit\": \"piece\"}}]"
    )
    
    model = genai.GenerativeModel(modelVersion)
    
    try:
        response = retry_with_backoff(
            model.generate_content,
            [system_prompt, img]
        )
        parsed_response = _parse_json_from_markdown(response.text)
        return parsed_response if isinstance(parsed_response, list) else []
    except ResourceExhausted:
        raise RuntimeError("The service is temporarily busy. Please try again later.")
    except Exception as e:
        raise RuntimeError(f"An error occurred while detecting ingredients: {e}")

def generate_plan_and_required(available_ingredients: List[Dict[str, Any]], dietary_preference: str) -> Dict[str, Any]:
    """Generates a meal plan and a list of all required ingredients."""
    setup_ia()
    ingredients_str = ", ".join([item.get("ingredient", "") for item in available_ingredients])

    prompt = (
        f"Dietary preference: {dietary_preference}\n"
        f"Available ingredients: {ingredients_str}\n\n"
        "**Main Task: Generate a COMPLETE and VARIED Meal Plan**\n"
        "You can summarize each meal to make it shorter but it must include 3 meals for each day of the week, without summarizing the days by repeating phrases."
        "1. **Master Rule**: You must create a detailed, creative, and varied meal plan for the **7 full days** of the week (Monday to Sunday).\n"
        "2. **KEY PROHIBITIONS:**\n"
        "    - **DO NOT REPEAT MEALS:** Each of the 21 meals must be a unique and different recipe. It is strictly forbidden to repeat a meal from a previous day or use phrases like '(Repetition of...)'.\n"
        "    - **DO NOT SUMMARIZE OR OMIT DAYS:** You must generate the complete response from Monday to Sunday without interruptions.\n"
        "3. **MANDATORY FORMAT FOR EACH MEAL:**\n"
        "    For **each of the 21 meals**, without exception, you must provide the complete recipe with all these details:\n"
        "    - **Dish Name**\n"
        "    - **Servings**\n"
        "    - **Nutritional Information (Estimated)**: Calories, Proteins, Carbohydrates, Fats.\n"
        "    - **Ingredients**: List with amounts.\n"
        "**Secondary Task (At the end of EVERYTHING):**\n"
        "After generating the COMPLETE and VARIED 7-day plan, add a JSON code block with the list of ALL necessary ingredients. The format is: \n"
        "```json\n"
        "{\"required_ingredients\": [{\"ingredient\": \"name\", \"amount\": \"e.g., 2 units\"}, ...]}\n"
        "```"
    )

    model = genai.GenerativeModel(modelVersion)
    try:
        response = retry_with_backoff(
            model.generate_content,
            prompt
        )
        full_text = response.text
        
        plan_markdown = full_text.split("```json")[0].strip()
        parsed_json = _parse_json_from_markdown(full_text)
        required_ingredients = parsed_json.get("required_ingredients", []) if isinstance(parsed_json, dict) else []

        return {
            "plan_markdown": plan_markdown,
            "required_ingredients": required_ingredients
        }
    except ResourceExhausted:
        raise RuntimeError("The service is temporarily busy.")
    except Exception as e:
        raise RuntimeError(f"Error generating the meal plan: {e}")

def create_shopping_list(available_ingredients: List[Dict[str, Any]], required_ingredients: List[Dict[str, Any]]) -> str:
    """Compares available ingredients with required ones to generate a shopping list."""
    available_set = {item['ingredient'].lower().strip() for item in available_ingredients}
    shopping_list = []

    for required in required_ingredients:
        required_name = required.get('ingredient', '').lower().strip()
        if required_name and required_name not in available_set:
            amount = required.get('amount', 'Amount not specified')
            shopping_list.append(f"- {required_name.capitalize()} ({amount})")

    if not shopping_list:
        return "It seems you have all the necessary ingredients."
    
    return "### Shopping List\n\n" + "\n".join(shopping_list)

def regenerate_meal(current_plan: str, meal_to_change: str, available_ingredients: List[Dict[str, Any]], preference: str) -> str:
    """Regenerates a single meal within an existing meal plan."""
    setup_ia()
    ingredients_str = ", ".join([item.get("ingredient", "") for item in available_ingredients])

    prompt = (
        f"Your task is to regenerate a single meal in an existing meal plan.\n"
        f"Here is the current full meal plan:\n"
        f"```\n{current_plan}\n```\n\n"
        f"The meal you must change is: '{meal_to_change}'.\n"
        f"Use these ingredients: {ingredients_str}\n"
        f"And consider this preference: {preference}\n\n"
        f"Final instruction: Return only the complete and updated meal plan in the same original text format. Make sure all the plan's content stays the same, except for the '{meal_to_change}' recipe, which must be a new creative recipe.\n"
        f"Do not add any additional text, headers, or JSON format. Just return the complete, updated meal plan."
    )
    
    model = genai.GenerativeModel(modelVersion)
    try:
        response = retry_with_backoff(
            model.generate_content,
            prompt
        )
        return response.text
    except Exception as e:
        raise RuntimeError(f"Error regenerating the meal: {e}")