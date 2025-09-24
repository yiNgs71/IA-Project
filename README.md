IA-Project
This project is an AI agent that optimizes meal planning. Simply upload a photo of your ingredients, and the application, powered by Google Gemini, will give you a personalized meal plan, a shopping list, and recipes.

Requirements
Make sure you have Python 3.7 or higher installed, along with the following libraries. You can install them with pip:

Bash

pip install gradio
pip install python-dotenv
pip install Pillow
pip install google-generativeai
Setup
To make the project work, you need a Google Gemini API key.

Get your API key from Google AI Studio.

Create a file named .env in the main project folder.

Inside the .env file, add your API key like this:

GOOGLE_API_KEY='your_api_key'
How to Run the Project
Save the gui.py and chefPersonal.py files in the same folder.

Run the following command to start the application:

Bash

python gui.py
