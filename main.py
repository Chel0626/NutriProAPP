import flet as ft
from calculadoras import *
import os

def main(page: ft.Page):
    page.title = "Ferramenta de Planejamento de Dieta"
    page.vertical_alignment = ft.CrossAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.window_width = 650
    page.window_height = 750
    page.padding = 10
    page.theme_mode = ft.ThemeMode.LIGHT

    # --- Estado da Aplicação ---
    app_state = {
        "ultimo_resultado": {},
        "widgets_refeicoes": {'grandes': [], 'pequenas': []},
        "entry_old_values": {}
    }

    # --- Referência para o Checkbox ---
    redistribuicao_automatica_ref = ft.Ref[ft.Checkbox]()

    # Notificações
    page.snack_bar = ft.SnackBar(ft.Text(""))

    def show_message(message: str, error=False):
        page.snack_bar.content = ft.Text(message)
        page.snack_bar.open = True
        page.snack_bar.bgcolor = "red500" if error else "green700"
        page.update()

    # --- FUNÇÕES DE LÓGICA (Redistribuição, etc.) ---

    def _store_old_value(e: ft.ControlEvent):
        widget = e.control
        try:
            app_state["entry_old_values"][widget] = int(widget.value or 0)
        except (ValueError, TypeError):
            app_state["entry_old_values"][widget] = 0

    def _on_macro_field_change(e: ft.ControlEvent, meal_type: str, changed_index: int, macro_key: str):
        if not redistribuicao_automatica_ref.current.value:
            recalcular_totais_manuais()
            return

        changed_widget = e.control
        old_value = app_state["entry_old_values"].get(changed_widget, 0)

        try:
            new_value = int(changed_widget.value or 0)
        except ValueError:
            changed_widget.value = str(old_value)
            changed_widget.update()
            return

        delta = old_value - new_value
        if delta == 0: return

        peer_widgets = [
            widget_info[macro_key]
            for i, widget_info in enumerate(app_state["widgets_refeicoes"][meal_type])
            if i != changed_index
        ]
        
        if not peer_widgets:
            recalcular_totais_manuais()
            return

        base_redistribution = delta // len(peer_widgets)
        remainder = delta % len(peer_widgets)

        for i, widget in enumerate(peer_widgets):
            try:
                current_peer_value = int(widget.value or 0)
                amount_to_add = base_redistribution + (1 if i < remainder else 0)
                widget.value = str(current_peer_value + amount_to_add)
                widget.update()
            except ValueError:
                continue
        
        recalcular_totais_manuais()

    def criar_linha_refeicao(data, meal_type, index_in_type):
        campos = {}
        macro_map = {'carb': 'carboidrato', 'prot': 'proteina', 'gord': 'gordura'}
        for short_name, long_name in macro_map.items():
            entry = ft.TextField(
                expand=1,
                text_align=ft.TextAlign.CENTER,
                value=str(data.get(long_name, 0)),
                on_focus=_store_old_value,
                on_blur=lambda e, mt=meal_type, idx=index_in_type, mk=short_name: _on_macro_field_change(e, mt, idx, mk),
                input_filter=ft.InputFilter(allow=True, regex_string=r"[0-9]"),
            )
            campos[short_name] = entry
        return campos

    def executar_calculo_calorias(e):
        try:
            peso = float(entry_peso.value)
            altura = float(entry_altura.value)
            idade = int(entry_idade.value)
            sexo = combo_sexo.value.lower()
            map_nivel_atividade = {'Sedentário (pouco ou nenhum exercício)': 'sedentario', 'Levemente Ativo (exercício 1-3 dias/semana)': 'leve', 'Moderadamente Ativo (exercício 3-5 dias/semana)': 'moderado', 'Muito Ativo (exercício 6-7 dias/semana)': 'ativo', 'Extremamente Ativo (exercício muito pesado/trabalho físico)': 'extremo'}
            nivel_atividade = map_nivel_atividade.get(combo_nivel_atividade.value)
            map_objetivo = {'Perder Peso': 'perder', 'Manter Peso': 'manter', 'Ganhar Peso': 'ganhar'}
            objetivo = map_objetivo.get(combo_objetivo.value)
            resultado_calorias = calcular_necessidade_calorica(peso_kg=peso, altura_cm=altura, idade_anos=idade, sexo=sexo, nivel_atividade=nivel_atividade, objetivo=objetivo)
            if resultado_calorias:
                app_state["ultimo_resultado"] = {'resultado_calorias': resultado_calorias, 'peso': peso}
                label_resultado_tmb_cal.value = f"Taxa Metabólica Basal (TMB): {resultado_calorias['tmb']} kcal/dia"
                label_resultado_fator_cal.value = f"Fator de Atividade (NAF): x {resultado_calorias['fator_atividade']}"
                label_resultado_manutencao_cal.value = f"Calorias para Manutenção: {resultado_calorias['calorias_manutencao']} kcal/dia"
                label_resultado_objetivo_cal.value = f"Meta para Objetivo: {resultado_calorias['calorias_objetivo']} kcal/dia"
                label_resultado_objetivo_cal.color = "blue500"
                show_message("Cálculo de calorias realizado com sucesso!")
            else:
                show_message("Não foi possível calcular. Verifique os campos.", error=True)
        except (ValueError, TypeError):
            show_message("Por favor, insira valores numéricos válidos.", error=True)
        page.update()

    def copiar_resultados_calorias(e):
        ultimo_resultado = app_state["ultimo_resultado"]
        if 'resultado_calorias' in ultimo_resultado:
            res = ultimo_resultado['resultado_calorias']
            texto_para_copiar = (f"Resultados do Cálculo:\nTaxa Metabólica Basal (TMB): {res['tmb']} kcal/dia\nFator de Atividade (NAF): x {res['fator_atividade']}\nCalorias para Manutenção: {res['calorias_manutencao']} kcal/dia\nMeta para Objetivo: {res['calorias_objetivo']} kcal/dia\n")
            page.set_clipboard(texto_para_copiar)
            show_message("Resultados copiados.")
        else:
            show_message("Calcule a necessidade calórica primeiro.", error=True)

    def ir_para_distribuicao(e):
        ultimo_resultado = app_state["ultimo_resultado"]
        if 'resultado_calorias' in ultimo_resultado and 'peso' in ultimo_resultado:
            resultado_calorias = ultimo_resultado['resultado_calorias']
            peso = ultimo_resultado['peso']
            entry_total_kcal_macro.value = str(resultado_calorias['calorias_objetivo'])
            entry_peso_paciente_macro.value = str(peso)
            tabs.selected_index = 1
            page.update()
        else:
            show_message("Calcule a necessidade calórica primeiro.", error=True)

    def executar_calculo_macros(e=None, macros_ajustados=None):
        try:
            peso_paciente = float(entry_peso_paciente_macro.value)
            if macros_ajustados is None:
                total_kcal = int(entry_total_kcal_macro.value)
                perc_prot = float(entry_perc_prot.value)
                perc_carb = float(entry_perc_carb.value)
                perc_gord = float(entry_perc_gord.value)
                macros_totais = calcular_macros_por_porcentagem(total_kcal, perc_carb, perc_prot, perc_gord)
                if not macros_totais:
                    show_message("A soma das porcentagens deve ser 100%.", error=True)
                    return
            else:
                macros_totais = macros_ajustados
            app_state['ultimo_resultado']['macros_totais'] = macros_totais
            app_state['ultimo_resultado']['peso'] = peso_paciente
            atualizar_interface_completa(macros_iniciais=(macros_ajustados is None))
            show_message("Distribuição de macros calculada!")
        except (ValueError, TypeError):
            show_message("Insira valores numéricos válidos.", error=True)
        page.update()

    def _ler_macros_da_interface():
        widgets_refeicoes = app_state["widgets_refeicoes"]
        grandes = [{'proteina': int(c['prot'].value or 0), 'carboidrato': int(c['carb'].value or 0), 'gordura': int(c['gord'].value or 0)} for c in widgets_refeicoes['grandes']]
        pequenas = [{'proteina': int(c['prot'].value or 0), 'carboidrato': int(c['carb'].value or 0), 'gordura': int(c['gord'].value or 0)} for c in widgets_refeicoes['pequenas']]
        return grandes, pequenas

    def recalcular_totais_manuais(e=None):
        try:
            grandes, pequenas = _ler_macros_da_interface()
            novos_macros_em_gramas = somar_macros_refeicoes(grandes, pequenas)
            if novos_macros_em_gramas:
                executar_calculo_macros(macros_ajustados=novos_macros_em_gramas)
            else:
                show_message("Erro ao somar macros.", error=True)
        except ValueError:
            show_message("Valores nas refeições devem ser números.", error=True)
        page.update()

    def atualizar_interface_completa(macros_iniciais=False):
        ultimo_resultado = app_state["ultimo_resultado"]
        macros_totais, peso_paciente = ultimo_resultado.get('macros_totais', {}), ultimo_resultado.get('peso')
        if not all([macros_totais, peso_paciente]):
            frame_resultados.visible = False
            page.update()
            return
        prot_gkg, carb_gkg, gord_gkg = (round(macros_totais[m] / peso_paciente, 2) if peso_paciente > 0 else 0 for m in ['proteina', 'carboidrato', 'gordura'])
        total_kcal_ajustado = (macros_totais['proteina'] * 4) + (macros_totais['carboidrato'] * 4) + (macros_totais['gordura'] * 9)
        label_resultado_prot_total.value, label_resultado_carb_total.value, label_resultado_gord_total.value, label_kcal_ajustado.value = f"Proteína: {macros_totais['proteina']} g ({prot_gkg} g/kg)", f"Carboidrato: {macros_totais['carboidrato']} g ({carb_gkg} g/kg)", f"Gordura: {macros_totais['gordura']} g ({gord_gkg} g/kg)", f"Total Ajustado: {total_kcal_ajustado} kcal"
        frame_resultados.visible = True
        if macros_iniciais:
            num_grandes, num_pequenas, perc_dist_grandes = int(entry_num_grandes.value), int(entry_num_pequenas.value), int(entry_perc_dist_grandes.value)
            distribuicao = distribuir_macros_nas_refeicoes(macros_totais, num_grandes, num_pequenas, perc_dist_grandes)
            frame_ajuste_manual.controls.clear()
            app_state["widgets_refeicoes"] = {'grandes': [], 'pequenas': []}
            frame_ajuste_manual.controls.append(ft.Checkbox(ref=redistribuicao_automatica_ref, label="Ativar redistribuição automática", value=True))
            frame_ajuste_manual.controls.append(ft.Row([ft.Text("Refeição", weight=ft.FontWeight.BOLD, expand=2), ft.Text("Carb(g)", weight=ft.FontWeight.BOLD, expand=1), ft.Text("Prot(g)", weight=ft.FontWeight.BOLD, expand=1), ft.Text("Gord(g)", weight=ft.FontWeight.BOLD, expand=1)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
            if distribuicao and num_grandes > 0:
                frame_ajuste_manual.controls.append(ft.Text("Refeições Grandes:", weight=ft.FontWeight.BOLD))
                for i in range(num_grandes):
                    campos = criar_linha_refeicao(distribuicao['por_refeicao_grande'], 'grandes', i)
                    app_state["widgets_refeicoes"]['grandes'].append(campos)
                    frame_ajuste_manual.controls.append(ft.Row([ft.Text(f"Grande {i + 1}:", expand=2), campos['carb'], campos['prot'], campos['gord']], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
            if distribuicao and num_pequenas > 0:
                frame_ajuste_manual.controls.append(ft.Text("Refeições Pequenas:", weight=ft.FontWeight.BOLD))
                for i in range(num_pequenas):
                    campos = criar_linha_refeicao(distribuicao['por_refeicao_pequena'], 'pequenas', i)
                    app_state["widgets_refeicoes"]['pequenas'].append(campos)
                    frame_ajuste_manual.controls.append(ft.Row([ft.Text(f"Pequena {i + 1}:", expand=2), campos['carb'], campos['prot'], campos['gord']], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
            frame_ajuste_manual.controls.append(ft.Row([ft.FilledButton("Recalcular Totais", on_click=recalcular_totais_manuais, icon="calculate"), ft.FilledButton("Copiar Plano", on_click=copiar_plano_completo, icon="copy"), ft.FilledButton("Salvar .txt", on_click=salvar_plano_em_arquivo, icon="save")], alignment=ft.MainAxisAlignment.CENTER))
        page.update()

    def gerar_texto_plano_completo():
        ultimo_resultado = app_state["ultimo_resultado"]
        if 'resultado_calorias' not in ultimo_resultado or 'macros_totais' not in ultimo_resultado:
            show_message("Calcule tudo primeiro.", error=True)
            return None
        res_cal, peso = ultimo_resultado['resultado_calorias'], ultimo_resultado.get('peso', 0)
        try:
            refeicoes_grandes_data, refeicoes_pequenas_data = _ler_macros_da_interface()
            macros_ajustados = somar_macros_refeicoes(refeicoes_grandes_data, refeicoes_pequenas_data)
        except (ValueError, TypeError):
            show_message("Valores inválidos nas refeições.", error=True)
            return None
        prot_g, carb_g, gord_g = macros_ajustados['proteina'], macros_ajustados['carboidrato'], macros_ajustados['gordura']
        prot_gkg, carb_gkg, gord_gkg = (round(macros_ajustados[m] / peso, 2) if peso > 0 else 0 for m in ['proteina', 'carboidrato', 'gordura'])
        total_kcal_final = (prot_g * 4) + (carb_g * 4) + (gord_g * 9)
        texto = f"PLANO ALIMENTAR COMPLETO\n================================\n\n1. NECESSIDADE CALÓRICA INICIAL\n--------------------------------\nTMB: {res_cal['tmb']} kcal\nMeta Calórica: {res_cal['calorias_objetivo']} kcal\n\n2. TOTAIS DE MACROS (AJUSTADO)\n--------------------------------\nCalorias Totais: {total_kcal_final} kcal\nProteína: {prot_g} g ({prot_gkg} g/kg)\nCarboidrato: {carb_g} g ({carb_gkg} g/kg)\nGordura: {gord_g} g ({gord_gkg} g/kg)\n\n3. DISTRIBUIÇÃO POR REFEIÇÃO\n--------------------------------\n"
        if app_state["widgets_refeicoes"]['grandes']:
            texto += "Refeições Grandes:\n"
            for i, c in enumerate(app_state["widgets_refeicoes"]['grandes']): texto += f"  - Refeição {i + 1}: Carb: {c['carb'].value}g, Prot: {c['prot'].value}g, Gord: {c['gord'].value}g\n"
        if app_state["widgets_refeicoes"]['pequenas']:
            texto += "Refeições Pequenas:\n"
            for i, c in enumerate(app_state["widgets_refeicoes"]['pequenas']): texto += f"  - Refeição {i + 1}: Carb: {c['carb'].value}g, Prot: {c['prot'].value}g, Gord: {c['gord'].value}g\n"
        return texto

    def copiar_plano_completo(e):
        texto = gerar_texto_plano_completo()
        if texto:
            page.set_clipboard(texto)
            show_message("Plano completo copiado.")

    def on_dialog_result(e: ft.FilePickerResultEvent):
        if e.path:
            texto = gerar_texto_plano_completo()
            if texto:
                try:
                    with open(e.path, 'w', encoding='utf-8') as f: f.write(texto)
                    show_message(f"Plano salvo em: {e.path}")
                except Exception as ex:
                    show_message(f"Erro ao salvar: {ex}", error=True)
        page.update()

    file_picker = ft.FilePicker(on_result=on_dialog_result)
    page.overlay.append(file_picker)

    def salvar_plano_em_arquivo(e):
        texto = gerar_texto_plano_completo()
        if texto:
            file_picker.save_file("Salvar Plano", file_name="plano_alimentar.txt", file_type=ft.FilePickerFileType.ANY)

    def calcular_regra_de_3(e):
        try:
            a, b, c = float(entry_r3_a.value), float(entry_r3_b.value), float(entry_r3_c.value)
            if a == 0:
                show_message("O 'Valor A' não pode ser zero.", error=True)
                return
            resultado = (b * c) / a
            label_r3_resultado_valor.value = f"{resultado:.2f}"
            show_message("Cálculo da regra de 3 realizado!")
        except ValueError:
            show_message("Insira números válidos.", error=True)
        page.update()

    def limpar_regra_de_3(e):
        entry_r3_a.value, entry_r3_b.value, entry_r3_c.value, label_r3_resultado_valor.value = "", "", "", "---"
        page.update()

    entry_peso = ft.TextField(label="Peso (kg)", input_filter=ft.InputFilter(allow=True, regex_string=r"[0-9\.]"))
    entry_altura = ft.TextField(label="Altura (cm)", input_filter=ft.InputFilter(allow=True, regex_string=r"[0-9\.]"))
    entry_idade = ft.TextField(label="Idade (anos)", input_filter=ft.InputFilter(allow=True, regex_string=r"[0-9]"))
    combo_sexo = ft.Dropdown(label="Sexo", options=[ft.dropdown.Option(s) for s in ["Masculino", "Feminino", "Criança"]], value="Feminino")
    combo_nivel_atividade = ft.Dropdown(label="Nível de Atividade", options=[ft.dropdown.Option(o) for o in ['Sedentário (pouco ou nenhum exercício)', 'Levemente Ativo (exercício 1-3 dias/semana)', 'Moderadamente Ativo (exercício 3-5 dias/semana)', 'Muito Ativo (exercício 6-7 dias/semana)', 'Extremamente Ativo (exercício muito pesado/trabalho físico)']], value='Levemente Ativo (exercício 1-3 dias/semana)')
    combo_objetivo = ft.Dropdown(label="Objetivo", options=[ft.dropdown.Option(o) for o in ['Perder Peso', 'Manter Peso', 'Ganhar Peso']], value='Manter Peso')
    label_resultado_tmb_cal, label_resultado_fator_cal, label_resultado_manutencao_cal, label_resultado_objetivo_cal = ft.Text("-"), ft.Text("-"), ft.Text("-"), ft.Text("-", size=16, weight=ft.FontWeight.BOLD)
    
    tab_calorias_content = ft.Column([
        ft.Text("Dados do Paciente", size=16, weight=ft.FontWeight.BOLD),
        ft.ResponsiveRow([
            ft.Column(col={"sm": 12, "md": 4}, controls=[entry_peso]),
            ft.Column(col={"sm": 12, "md": 4}, controls=[entry_altura]),
            ft.Column(col={"sm": 12, "md": 4}, controls=[entry_idade]),
            ft.Column(col={"sm": 12, "md": 12}, controls=[combo_sexo]),
            ft.Column(col={"sm": 12}, controls=[combo_nivel_atividade]),
            ft.Column(col={"sm": 12}, controls=[combo_objetivo]),
        ]),
        ft.Row([ft.FilledButton("Calcular", on_click=executar_calculo_calorias, icon="calculate_outlined", expand=True), ft.FilledButton("Copiar", on_click=copiar_resultados_calorias, icon="copy")]),
        ft.Row([ft.FilledButton("Avançar para Distribuição →", on_click=ir_para_distribuicao, icon="arrow_forward", expand=True)]),
        ft.Divider(),
        ft.Container(content=ft.Column([ft.Text("Resultados", size=14, weight=ft.FontWeight.BOLD), label_resultado_tmb_cal, label_resultado_fator_cal, label_resultado_manutencao_cal, label_resultado_objetivo_cal]), padding=10, border=ft.border.all(1, "blue_grey_100"), border_radius=5)
    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10, scroll=ft.ScrollMode.ADAPTIVE)

    entry_total_kcal_macro, entry_peso_paciente_macro, entry_perc_prot, entry_perc_carb, entry_perc_gord, entry_num_grandes, entry_num_pequenas, entry_perc_dist_grandes = (ft.TextField(label=l, value=v, width=150, input_filter=ft.InputFilter(allow=True, regex_string=r"[0-9\.]")) for l, v in [("Meta Calórica (kcal)", None), ("Peso (kg)", None), ("Prot (%)", "20.0"), ("Carb (%)", "45.0"), ("Gord (%)", "35.0"), ("Nº Grandes", "3"), ("Nº Pequenas", "3"), ("% Cal. Grandes", "70")])
    label_resultado_prot_total, label_resultado_carb_total, label_resultado_gord_total, label_kcal_ajustado = ft.Text("-"), ft.Text("-"), ft.Text("-"), ft.Text("-", weight=ft.FontWeight.BOLD)
    frame_totais = ft.Column([ft.Text("Totais Diários:", weight=ft.FontWeight.BOLD), label_resultado_prot_total, label_resultado_carb_total, label_resultado_gord_total, label_kcal_ajustado])
    frame_ajuste_manual = ft.Column(controls=[], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
    frame_resultados = ft.Container(content=ft.Column([ft.Text("Resultados e Ajustes", size=14, weight=ft.FontWeight.BOLD), frame_totais, ft.Divider(), frame_ajuste_manual]), padding=10, border=ft.border.all(1, "blue_grey_100"), border_radius=5, visible=False)
    tab_macros_content = ft.Column([ft.Container(content=ft.Column([ft.Text("Configuração Inicial", size=14, weight=ft.FontWeight.BOLD), ft.Row([ft.Column([entry_total_kcal_macro, entry_peso_paciente_macro, entry_perc_prot]), ft.Column([entry_perc_carb, entry_perc_gord, entry_num_grandes]), ft.Column([entry_num_pequenas, entry_perc_dist_grandes])], alignment=ft.MainAxisAlignment.CENTER, wrap=True)]), padding=10, border=ft.border.all(1, "blue_grey_100"), border_radius=5), ft.FilledButton("Calcular Distribuição", on_click=executar_calculo_macros, icon="playlist_add_check_circle_rounded"), frame_resultados], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15, scroll=ft.ScrollMode.ADAPTIVE)
    
    entry_r3_a = ft.TextField(label="Valor A", text_align=ft.TextAlign.CENTER, input_filter=ft.InputFilter(allow=True, regex_string=r"[0-9\.]"))
    entry_r3_b = ft.TextField(label="Valor B", text_align=ft.TextAlign.CENTER, input_filter=ft.InputFilter(allow=True, regex_string=r"[0-9\.]"))
    entry_r3_c = ft.TextField(label="Valor C", text_align=ft.TextAlign.CENTER, input_filter=ft.InputFilter(allow=True, regex_string=r"[0-9\.]"))
    label_r3_resultado_valor = ft.Text("---", size=24, weight=ft.FontWeight.BOLD, color="blue_500", text_align=ft.TextAlign.CENTER)
    
    tab_regra3_content = ft.Column([
        ft.Row([
            ft.Column([entry_r3_a], expand=2),
            ft.Column([ft.Text("está para", text_align=ft.TextAlign.CENTER)], expand=1),
            ft.Column([entry_r3_b], expand=2),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ft.Text("assim como", weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
        ft.Row([
            ft.Column([entry_r3_c], expand=2),
            ft.Column([ft.Text("está para", text_align=ft.TextAlign.CENTER)], expand=1),
            ft.Column([ft.Text("Resultado (X)", weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER), label_r3_resultado_valor], expand=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ft.Row([
            ft.FilledButton("Calcular", on_click=calcular_regra_de_3, icon="calculate", expand=True),
            ft.FilledButton("Limpar", on_click=limpar_regra_de_3, icon="clear", expand=True),
        ])
    ], spacing=15, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    tabs = ft.Tabs(selected_index=0, animation_duration=300, tabs=[ft.Tab(text="1. Caloria", content=tab_calorias_content, icon="flash_on"), ft.Tab(text="2. Dieta", content=tab_macros_content, icon="pie_chart"), ft.Tab(text="Regra de 3", content=tab_regra3_content, icon="percent")], expand=1)
    page.add(tabs)

if __name__ == "__main__":
    ft.app(target=main)