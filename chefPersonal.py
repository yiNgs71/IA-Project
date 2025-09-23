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

def retry_with_backoff(api_call_func, *args, **kwargs):
    """
    Intenta una llamada a la API con reintentos exponenciales indefinidos.
    """
    delay = 2
    while True:
        try:
            return api_call_func(*args, **kwargs)
        except ResourceExhausted as e:
            print(f"Servicio saturado. Reintentando en {delay} segundos...")
            time.sleep(delay)
        except Exception as e:
            raise e

def configurar_ia():
    """Carga la clave de API y configura el cliente de Google GenAI."""
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError("No se encontró la variable de entorno GOOGLE_API_KEY.")

    genai.configure(api_key=api_key)

def _parse_json_from_markdown(text: str) -> Any:
    """Extrae y decodifica un bloque de código JSON de una cadena de texto."""
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
    json_text = match.group(1) if match else text
    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        return {}

def detectar_ingredientes_con_cantidades(ruta_imagen: str) -> List[Dict[str, Any]]:
    """Analiza una imagen de alimentos y devuelve una lista de ingredientes detectados."""
    if not os.path.exists(ruta_imagen):
        raise FileNotFoundError(f"El archivo de imagen no se encontró en: {ruta_imagen}")

    configurar_ia()
    img = Image.open(ruta_imagen)
    
    system_prompt = (
        "Eres un experto en alimentos. Analiza la imagen para identificar todos los ingredientes. "
        "Estima la cantidad de cada uno. "
        "Devuelve la respuesta únicamente como una lista JSON de objetos. "
        "Cada objeto debe tener una clave 'ingrediente' (string) y una clave 'cantidad' (un objeto con 'valor' y 'unidad'). "
        "Ejemplo: [{\"ingrediente\": \"tomate\", \"cantidad\": {\"valor\": 2, \"unidad\": \"pieza\"}}]"
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
        raise RuntimeError("El servicio está temporalmente saturado. Inténtalo de nuevo más tarde.")
    except Exception as e:
        raise RuntimeError(f"Ocurrió un error al detectar ingredientes: {e}")

def generar_plan_y_requeridos(ingredientes_disponibles: List[Dict[str, Any]], preferencia_dietetica: str) -> Dict[str, Any]:
    """Genera un plan de comidas y una lista de todos los ingredientes necesarios."""
    configurar_ia()
    ingredientes_str = ", ".join([item.get("ingrediente", "") for item in ingredientes_disponibles])

    prompt = (
        f"Preferencia dietética: {preferencia_dietetica}\n"
        f"Ingredientes disponibles: {ingredientes_str}\n\n"
        "**Tarea Principal: Generar un Plan de Comidas COMPLETO y VARIADO**\n"
        "Puedes resumir cada comida para que sea mas corta pero que cumpla con 3 comidas para cada uno de los dias de la semana, sin resumir los dias repitiendo frases."
        "1. **REGLA Maestra**: Debes crear un plan de comidas detallado, creativo y variado para los **7 días completos** de la semana (Lunes a Domingo).\n"
        "2. **PROHIBICIONES CLAVE:**\n"
        "   - **NO REPITAS COMIDAS:** Cada una de las 21 comidas debe ser una receta única y diferente. Está estrictamente prohibido repetir una comida de un día anterior o usar frases como '(Repetición del...)'.\n"
        "   - **NO RESUMAS NI OMITAS DÍAS:** Debes generar la respuesta completa desde el Lunes hasta el Domingo sin interrupciones.\n"
        "3. **FORMATO OBLIGATORIO PARA CADA COMIDA:**\n"
        "   Para **cada una de las 21 comidas**, sin excepción, debes proporcionar la receta completa con todos estos detalles:\n"
        "   - **Nombre del Platillo**\n"
        "   - **Porciones**\n"
        "   - **Información Nutricional (Estimada)**: Calorías, Proteínas, Carbohidratos, Grasas.\n"
        "   - **Ingredientes**: Lista con cantidades.\n"
        "**Tarea Secundaria (Al final de TODO):**\n"
        "Después de generar el plan COMPLETO y VARIADO de 7 días, agrega un bloque de código JSON con la lista de TODOS los ingredientes necesarios. El formato es: \n"
        "```json\n"
        "{\"ingredientes_requeridos\": [{\"ingrediente\": \"nombre\", \"cantidad\": \"ej. 2 unidades\"}, ...]}\n"
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
        ingredientes_requeridos = parsed_json.get("ingredientes_requeridos", []) if isinstance(parsed_json, dict) else []

        return {
            "plan_markdown": plan_markdown,
            "ingredientes_requeridos": ingredientes_requeridos
        }
    except ResourceExhausted:
        raise RuntimeError("El servicio está temporalmente saturado.")
    except Exception as e:
        raise RuntimeError(f"Error al generar el plan de comidas: {e}")

def crear_lista_de_compras(ingredientes_disponibles: List[Dict[str, Any]], ingredientes_requeridos: List[Dict[str, Any]]) -> str:
    """Compara los ingredientes disponibles con los requeridos para generar una lista de compras."""
    disponibles_set = {item['ingrediente'].lower().strip() for item in ingredientes_disponibles}
    lista_compras = []

    for requerido in ingredientes_requeridos:
        nombre_requerido = requerido.get('ingrediente', '').lower().strip()
        if nombre_requerido and nombre_requerido not in disponibles_set:
            cantidad = requerido.get('cantidad', 'Cantidad no especificada')
            lista_compras.append(f"- {nombre_requerido.capitalize()} ({cantidad})")

    if not lista_compras:
        return "Parece que tienes todos los ingredientes necesarios."
    
    return "### Lista de Compras\n\n" + "\n".join(lista_compras)

def regenerar_comida(plan_actual: str, comida_a_cambiar: str, ingredientes_disponibles: List[Dict[str, Any]], preferencia: str) -> str:
    """Regenera una única comida dentro de un plan de comidas existente."""
    configurar_ia()
    ingredientes_str = ", ".join([item.get("ingrediente", "") for item in ingredientes_disponibles])

    prompt = (
        f"Tu tarea es regenerar una sola comida en un plan de comidas existente.\n"
        f"Aquí está el plan de comidas completo actual:\n"
        f"```\n{plan_actual}\n```\n\n"
        f"La comida que debes cambiar es: '{comida_a_cambiar}'.\n"
        f"Utiliza estos ingredientes: {ingredientes_str}\n"
        f"Y ten en cuenta esta preferencia: {preferencia}\n\n"
        f"Instrucción final: Devuelve únicamente el plan de comidas completo y actualizado en el mismo formato de texto original. Asegúrate de que todo el contenido del plan se mantenga igual, excepto por la receta de '{comida_a_cambiar}', que debe ser una nueva receta creativa.\n"
        f"No añadas ningún texto adicional, encabezados, ni formato JSON. Simplemente devuelve el plan de comidas completo y actualizado."
    )
    
    model = genai.GenerativeModel(modelVersion)
    try:
        response = retry_with_backoff(
            model.generate_content,
            prompt
        )
        return response.text
    except Exception as e:
        raise RuntimeError(f"Error al regenerar la comida: {e}")