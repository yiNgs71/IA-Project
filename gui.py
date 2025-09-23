import gradio as gr
from chefPersonal import (
    detectar_ingredientes_con_cantidades,
    generar_plan_y_requeridos,
    crear_lista_de_compras,
    regenerar_comida
)

def procesar_y_generar(imagen, preferencia):
    """Activa la detección de ingredientes y la generación del plan de comidas."""
    if imagen is None:
        return "Error: Sube una imagen primero.", [], "", "", [], None, None, ""

    try:
        ingredientes_disponibles = detectar_ingredientes_con_cantidades(imagen)
        if not ingredientes_disponibles:
            return "Error: No se detectaron ingredientes. Intenta con otra imagen.", [], "", "", [], None, None, ""

        tabla_ingredientes = [
            [item.get('ingrediente', '').capitalize(), f"{item['cantidad'].get('valor', '')} {item['cantidad'].get('unidad', '')}".strip()]
            for item in ingredientes_disponibles
        ]

        resultado_ia = generar_plan_y_requeridos(ingredientes_disponibles, preferencia)
        plan_md = resultado_ia["plan_markdown"]
        ingredientes_requeridos = resultado_ia["ingredientes_requeridos"]
        
        lista_compras_md = crear_lista_de_compras(ingredientes_disponibles, ingredientes_requeridos)
        
        return "Plan generado con éxito.", tabla_ingredientes, plan_md, lista_compras_md, ingredientes_disponibles, plan_md, preferencia, lista_compras_md

    except Exception as e:
        error_message = f"Ha ocurrido un error: {e}"
        return error_message, [], "", "", [], None, None, ""

def manejar_regeneracion(plan_actual, comida_a_cambiar, ingredientes_disponibles, preferencia):
    """Toma el plan actual y regenera una única comida seleccionada."""
    if not all([plan_actual, comida_a_cambiar, ingredientes_disponibles, preferencia]):
        gr.Warning("No se puede regenerar. Asegúrate de haber generado un plan primero.")
        return plan_actual, plan_actual

    try:
        nuevo_plan = regenerar_comida(plan_actual, comida_a_cambiar, ingredientes_disponibles, preferencia)
        gr.Info(f"Se ha regenerado la receta para {comida_a_cambiar}.")
        return nuevo_plan, nuevo_plan
    except Exception as e:
        gr.Error(f"Error al regenerar: {e}")
        return plan_actual, plan_actual

dias_y_comidas = [f"{dia} {comida}" 
                  for dia in ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"] 
                  for comida in ["Desayuno", "Comida", "Cena"]]

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    estado_ingredientes = gr.State([])
    estado_plan = gr.State("")
    estado_preferencia = gr.State("equilibrada")
    estado_lista_compras = gr.State("")

    gr.Markdown("# IA Chef Personal")
    gr.Markdown("Sube una foto de tus ingredientes para obtener un plan de comidas semanal, información nutricional y tu lista de compras.")

    with gr.Row():
        with gr.Column(scale=1):
            input_imagen = gr.Image(label="Sube una foto de tus ingredientes", type="filepath")
            input_preferencia = gr.Textbox(label="Preferencia dietética (opcional)", value="equilibrada")
            btn_generar = gr.Button("Generar Plan Semanal", variant="primary")
            
            with gr.Accordion("Regenerar una Comida", open=False):
                dropdown_regenerar = gr.Dropdown(dias_y_comidas, label="Selecciona la comida a cambiar")
                btn_regenerar = gr.Button("Regenerar Comida Seleccionada", variant="secondary")

        with gr.Column(scale=2):
            output_estado = gr.Textbox(label="Estado", interactive=False)
            with gr.Tabs():
                with gr.TabItem("Plan Semanal"):
                    output_plan = gr.Markdown()
                with gr.TabItem("Ingredientes Detectados"):
                    output_ingredientes = gr.DataFrame(headers=["Ingrediente", "Cantidad"], datatype=["str", "str"], row_count=(5, "dynamic"))
                with gr.TabItem("Lista de Compras"):
                    output_lista_compras = gr.Markdown()
                    
    
    btn_generar.click(
        fn=procesar_y_generar,
        inputs=[input_imagen, input_preferencia],
        outputs=[output_estado, output_ingredientes, output_plan, output_lista_compras, estado_ingredientes, estado_plan, estado_preferencia, estado_lista_compras]
    )

    btn_regenerar.click(
        fn=manejar_regeneracion,
        inputs=[estado_plan, dropdown_regenerar, estado_ingredientes, estado_preferencia],
        outputs=[output_plan, estado_plan]
    )


if __name__ == "__main__":
    demo.launch()