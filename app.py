import gradio as gr
from Model import predire_arrosage

with gr.Blocks(css="style.css") as demo:
    with gr.Tabs():
        with gr.TabItem("🏠 Accueil", elem_id="tab-accueil"):
            gr.Markdown("# 🌱 Bienvenue sur l'Application d'Irrigation Intelligente")
            gr.Markdown("### Système automatisé de supervision des cultures propulsé par un Réseau de Neurones Profond.")
            gr.Markdown("Utilisez l'onglet **'Supervision'** pour tester les prédictions d'arrosage en fonction de l'humidité du sol et de la température.")

        with gr.TabItem("💧 Supervision", elem_id="tab-supervision"):
            gr.Markdown("# 📊 Tableau de bord - Deep Learning")

            with gr.Row():
                with gr.Column():
                    hum_slider = gr.Slider(0, 100, step=1, label="💧 Humidité du sol (%)", value=20)
                    temp_slider = gr.Slider(0, 50, step=0.5, label="🌡️ Température de l'air (°C)", value=25)

                    with gr.Row():
                        btn_effacer = gr.Button("Effacer")
                        btn_soumettre = gr.Button("Soumettre", variant="primary")

                with gr.Column():
                    resultat_output = gr.Textbox(label="📊 Résultat de l'analyse IA", interactive=False)

            btn_soumettre.click(
                fn=predire_arrosage,
                inputs=[hum_slider, temp_slider],
                outputs=resultat_output
            )
            btn_effacer.click(
                fn=lambda: (20, 25, ""),
                outputs=[hum_slider, temp_slider, resultat_output]
            )

        with gr.TabItem("👋 Au revoir", elem_id="tab-au-revoir"):
            gr.Markdown("# 👋 Merci d'avoir utilisé notre application !")
            gr.Markdown("### L'optimisation de l'eau est la clé d'une agriculture durable.")
            gr.Markdown("Vous pouvez fermer cet onglet ou quitter le terminal en faisant **Ctrl + C**.")

if __name__ == "__main__":
    demo.launch(css="style.css")
