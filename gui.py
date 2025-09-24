import gradio as gr
from chefPersonal import (
    detect_ingredients_with_quantities,
    generate_plan_and_required,
    create_shopping_list,
    regenerate_meal
)

def process_and_generate(image, preference):
    """Activates ingredient detection and meal plan generation."""
    if image is None:
        return "Error: Please upload an image first.", [], "", "", [], None, None, ""

    try:
        available_ingredients = detect_ingredients_with_quantities(image)
        if not available_ingredients:
            return "Error: No ingredients detected. Try with another image.", [], "", "", [], None, None, ""

        ingredients_table = [
            [item.get('ingredient', '').capitalize(), f"{item['amount'].get('value', '')} {item['amount'].get('unit', '')}".strip()]
            for item in available_ingredients
        ]

        ai_result = generate_plan_and_required(available_ingredients, preference)
        plan_md = ai_result["plan_markdown"]
        required_ingredients = ai_result["required_ingredients"]
        
        shopping_list_md = create_shopping_list(available_ingredients, required_ingredients)
        
        return "Plan generated successfully.", ingredients_table, plan_md, shopping_list_md, available_ingredients, plan_md, preference, shopping_list_md

    except Exception as e:
        error_message = f"An error has occurred: {e}"
        return error_message, [], "", "", [], None, None, ""

def handle_regeneration(current_plan, meal_to_change, available_ingredients, preference):
    """Takes the current plan and regenerates a single selected meal."""
    if not all([current_plan, meal_to_change, available_ingredients, preference]):
        gr.Warning("Cannot regenerate. Make sure you have generated a plan first.")
        return current_plan, current_plan

    try:
        new_plan = regenerate_meal(current_plan, meal_to_change, available_ingredients, preference)
        gr.Info(f"The recipe for {meal_to_change} has been regenerated.")
        return new_plan, new_plan
    except Exception as e:
        gr.Error(f"Error regenerating: {e}")
        return current_plan, current_plan

days_and_meals = [f"{day} {meal}" 
                      for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"] 
                      for meal in ["Breakfast", "Lunch", "Dinner"]]

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    ingredients_state = gr.State([])
    plan_state = gr.State("")
    preference_state = gr.State("equilibrada")
    shopping_list_state = gr.State("")

    gr.Markdown("# Personal AI Chef")
    gr.Markdown("Upload a photo of your ingredients to get a weekly meal plan, nutritional information, and your shopping list.")

    with gr.Row():
        with gr.Column(scale=1):
            input_image = gr.Image(label="Upload a photo of your ingredients", type="filepath")
            input_preference = gr.Textbox(label="Dietary preference (optional)", value="balanced")
            btn_generate = gr.Button("Generate Weekly Plan", variant="primary")
            
            with gr.Accordion("Regenerate a Meal", open=False):
                dropdown_regenerate = gr.Dropdown(days_and_meals, label="Select the meal to change")
                btn_regenerate = gr.Button("Regenerate Selected Meal", variant="secondary")

        with gr.Column(scale=2):
            output_status = gr.Textbox(label="Status", interactive=False)
            with gr.Tabs():
                with gr.TabItem("Weekly Plan"):
                    output_plan = gr.Markdown()
                with gr.TabItem("Detected Ingredients"):
                    output_ingredients = gr.DataFrame(headers=["Ingredient", "Quantity"], datatype=["str", "str"], row_count=(5, "dynamic"))
                with gr.TabItem("Shopping List"):
                    output_shopping_list = gr.Markdown()
                    
    
    btn_generate.click(
        fn=process_and_generate,
        inputs=[input_image, input_preference],
        outputs=[output_status, output_ingredients, output_plan, output_shopping_list, ingredients_state, plan_state, preference_state, shopping_list_state]
    )

    btn_regenerate.click(
        fn=handle_regeneration,
        inputs=[plan_state, dropdown_regenerate, ingredients_state, preference_state],
        outputs=[output_plan, plan_state]
    )


if __name__ == "__main__":
    demo.launch()
