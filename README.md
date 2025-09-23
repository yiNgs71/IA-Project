# IA-Project

Este proyecto es un agente de IA que optimiza la planificación de comidas . Solo sube una foto de tus ingredientes y la aplicación, impulsada por Google Gemini, te dará un plan de comidas personalizado, una lista de compras y recetas.

Requisitos
Asegúrate de tener instalado Python 3.7 o superior y las siguientes bibliotecas. Puedes instalarlas con pip:

Bash

pip install gradio
pip install python-dotenv
pip install Pillow
pip install google-generativeai

Lo que necesitas para que el proyecto funcione, necesitas una clave de API de Google Gemini.

Obtén tu clave de API en Google AI Studio.

Crea un archivo llamado .env en la carpeta principal del proyecto.

Dentro del archivo .env, agrega tu clave de API de esta forma:
GOOGLE_API_KEY='tu_clave_de_api'

Cómo ejecutar el proyecto
Guarda los archivos gui.py y chefPersonal.py en la misma carpeta.

Ejecuta el siguiente comando para iniciar la aplicación:
python gui.py
