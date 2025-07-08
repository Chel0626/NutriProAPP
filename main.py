import flet as ft
from calculadoras import *
import os # Importar para salvar arquivo, assim como o filedialog do tkinter

# --- Variáveis globais para armazenar dados e widgets ---
ultimo_resultado = {}
widgets_refeicoes = {'grandes': [], 'pequenas': []}
entry_old_values = {}
redistribuicao_automatica_ativada = ft.Ref[ft.Checkbox]()

def main(page: ft.Page):
    page.title = "Ferramenta de Planejamento de Dieta"
    page.vertical_alignment = ft.CrossAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.window_width = 650
    page.window_height = 750
    page.padding = 10
    page.theme_mode = ft.ThemeMode.LIGHT # Ou DARK

    # Notificações
    page.snack_bar = ft.SnackBar(ft.Text(""))

    def show_message(message: str, error=False):
        page.snack_bar.content = ft.Text(message)
        page.snack_bar.open = True
        page.snack_bar.bgcolor = ft.colors.RED_500 if error else ft.colors.GREEN_700
        page.update()

    # --- FUNÇÕES DE CÁLCULO E AÇÕES DA INTERFACE ---

    def executar_calculo_calorias(e):
        """Calcula a necessidade calórica e exibe os resultados na primeira aba."""
        nonlocal ultimo_resultado
        try:
            peso = float(entry_peso.value)
            altura = float(entry_altura.value)
            idade = int(entry_idade.value)
            sexo = combo_sexo.value.lower()
            map_nivel_atividade = {'Sedentário (pouco ou nenhum exercício)': 'sedentario',
                                   'Levemente Ativo (exercício 1-3 dias/semana)': 'leve',
                                   'Moderadamente Ativo (exercício 3-5 dias/semana)': 'moderado',
                                   'Muito Ativo (exercício 6-7 dias/semana)': 'ativo',
                                   'Extremamente Ativo (exercício muito pesado/trabalho físico)': 'extremo'}
            nivel_atividade = map_nivel_atividade.get(combo_nivel_atividade.value)
            map_objetivo = {'Perder Peso': 'perder', 'Manter Peso': 'manter', 'Ganhar Peso': 'ganhar'}
            objetivo = map_objetivo.get(combo_objetivo.value)

            resultado_calorias = calcular_necessidade_calorica(
                peso_kg=peso, altura_cm=altura, idade_anos=idade, sexo=sexo,
                nivel_atividade=nivel_atividade, objetivo=objetivo
            )

            if resultado_calorias:
                ultimo_resultado['resultado_calorias'] = resultado_calorias
                ultimo_resultado['peso'] = peso
                label_resultado_tmb_cal.value = f"Taxa Metabólica Basal (TMB): {resultado_calorias['tmb']} kcal/dia"
                label_resultado_fator_cal.value = f"Fator de Atividade (NAF): x {resultado_calorias['fator_atividade']}"
                label_resultado_manutencao_cal.value = f"Calorias para Manutenção: {resultado_calorias['calorias_manutencao']} kcal/dia"
                label_resultado_objetivo_cal.value = f"Meta para Objetivo: {resultado_calorias['calorias_objetivo']} kcal/dia"
                label_resultado_objetivo_cal.color = ft.colors.BLUE_500
                show_message("Cálculo de calorias realizado com sucesso!")
            else:
                show_message("Não foi possível calcular. Verifique se todos os campos foram preenchidos corretamente.", error=True)

        except (ValueError, TypeError):
            show_message("Por favor, insira valores numéricos válidos para peso, altura e idade.", error=True)
        page.update()

    def copiar_resultados_calorias(e):
        """Copia os resultados da primeira aba para a área de transferência."""
        nonlocal ultimo_resultado
        if 'resultado_calorias' in ultimo_resultado:
            res = ultimo_resultado['resultado_calorias']
            texto_para_copiar = (
                f"Resultados do Cálculo de Necessidade Calórica:\n"
                f"---------------------------------------------\n"
                f"Taxa Metabólica Basal (TMB): {res['tmb']} kcal/dia\n"
                f"Fator de Atividade (NAF): x {res['fator_atividade']}\n"
                f"Calorias para Manutenção: {res['calorias_manutencao']} kcal/dia\n"
                f"Meta para Objetivo: {res['calorias_objetivo']} kcal/dia\n"
            )
            page.set_clipboard(texto_para_copiar)
            show_message("Os resultados foram copiados para a área de transferência.")
        else:
            show_message("Calcule a necessidade calórica primeiro antes de copiar.", error=True)

    def ir_para_distribuicao(e):
        """Muda para a segunda aba e preenche os campos com os resultados da primeira."""
        nonlocal ultimo_resultado
        if 'resultado_calorias' in ultimo_resultado and 'peso' in ultimo_resultado:
            resultado_calorias = ultimo_resultado['resultado_calorias']
            peso = ultimo_resultado['peso']
            entry_total_kcal_macro.value = str(resultado_calorias['calorias_objetivo'])
            entry_peso_paciente_macro.value = str(peso)
            tabs.selected_index = 1  # Seleciona a segunda aba
            entry_total_kcal_macro.update()
            entry_peso_paciente_macro.update()
            tabs.update()
        else:
            show_message("Por favor, calcule a necessidade calórica primeiro antes de avançar.", error=True)

    def executar_calculo_macros(e=None, macros_ajustados=None):
        """Calcula a distribuição de macros, usando dados do formulário ou macros ajustados."""
        nonlocal ultimo_resultado
        try:
            peso_paciente = float(entry_peso_paciente_macro.value)

            if macros_ajustados is None:
                total_kcal = int(entry_total_kcal_macro.value)
                perc_prot = float(entry_perc_prot.value)
                perc_carb = float(entry_perc_carb.value)
                perc_gord = float(entry_perc_gord.value)
                macros_totais = calcular_macros_por_porcentagem(total_kcal, perc_carb, perc_prot, perc_gord)
                if not macros_totais:
                    show_message("A soma das porcentagens de macronutrientes deve ser 100%.", error=True)
                    return
            else:
                macros_totais = macros_ajustados

            ultimo_resultado['macros_totais'] = macros_totais
            ultimo_resultado['peso'] = peso_paciente

            atualizar_interface_completa(macros_iniciais=macros_ajustados is None)
            show_message("Distribuição de macros calculada com sucesso!")

        except (ValueError, TypeError):
            show_message("Por favor, insira valores numéricos válidos para todos os campos.", error=True)
        page.update()

    def recalcular_totais_manuais(e=None):
        """Lê os valores manuais, soma e atualiza a interface."""
        nonlocal ultimo_resultado, widgets_refeicoes
        try:
            refeicoes_grandes_data = []
            for campos in widgets_refeicoes['grandes']:
                refeicoes_grandes_data.append({
                    'proteina': int(campos['prot'].value),
                    'carboidrato': int(campos['carb'].value),
                    'gordura': int(campos['gord'].value)
                })

            refeicoes_pequenas_data = []
            for campos in widgets_refeicoes['pequenas']:
                refeicoes_pequenas_data.append({
                    'proteina': int(campos['prot'].value),
                    'carboidrato': int(campos['carb'].value),
                    'gordura': int(campos['gord'].value)
                })

            novos_macros_em_gramas = somar_macros_refeicoes(refeicoes_grandes_data, refeicoes_pequenas_data)

            if novos_macros_em_gramas:
                executar_calculo_macros(macros_ajustados=novos_macros_em_gramas)
            else:
                show_message("Erro ao somar macros das refeições. Verifique os valores.", error=True)

        except ValueError:
            show_message("Valores nas refeições manuais devem ser números inteiros.", error=True)
        page.update()


    def atualizar_interface_completa(macros_iniciais=False):
        """Atualiza toda a seção de resultados (totais e refeições)."""
        nonlocal ultimo_resultado, widgets_refeicoes

        macros_totais = ultimo_resultado.get('macros_totais', {})
        peso_paciente = ultimo_resultado.get('peso')

        if not all([macros_totais, peso_paciente]):
            frame_resultados.visible = False
            page.update()
            return

        prot_gkg = round(macros_totais['proteina'] / peso_paciente, 2) if peso_paciente > 0 else 0
        carb_gkg = round(macros_totais['carboidrato'] / peso_paciente, 2) if peso_paciente > 0 else 0
        gord_gkg = round(macros_totais['gordura'] / peso_paciente, 2) if peso_paciente > 0 else 0

        total_kcal_ajustado = (macros_totais['proteina'] * 4) + \
                             (macros_totais['carboidrato'] * 4) + \
                             (macros_totais['gordura'] * 9)

        label_resultado_prot_total.value = f"Proteína: {macros_totais['proteina']} g ({prot_gkg} g/kg)"
        label_resultado_carb_total.value = f"Carboidrato: {macros_totais['carboidrato']} g ({carb_gkg} g/kg)"
        label_resultado_gord_total.value = f"Gordura: {macros_totais['gordura']} g ({gord_gkg} g/kg)"
        label_kcal_ajustado.value = f"Total Ajustado: {total_kcal_ajustado} kcal"

        frame_resultados.visible = True

        if macros_iniciais:
            num_grandes = int(entry_num_grandes.value)
            num_pequenas = int(entry_num_pequenas.value)
            perc_dist_grandes = int(entry_perc_dist_grandes.value)
            distribuicao = distribuir_macros_nas_refeicoes(macros_totais, num_grandes, num_pequenas, perc_dist_grandes)

            frame_ajuste_manual.controls.clear()
            widgets_refeicoes = {'grandes': [], 'pequenas': []}

            frame_ajuste_manual.controls.append(ft.Checkbox(
                ref=redistribuicao_automatica_ativada,
                label="Ativar redistribuição automática de macros",
                value=True # Padrão True
            ))
            frame_ajuste_manual.controls.append(
                ft.Row([
                    ft.Text("Refeição", weight=ft.FontWeight.BOLD),
                    ft.Text("Carboidrato (g)", weight=ft.FontWeight.BOLD),
                    ft.Text("Proteína (g)", weight=ft.FontWeight.BOLD),
                    ft.Text("Gordura (g)", weight=ft.FontWeight.BOLD),
                ], spacing=10)
            )

            if distribuicao and num_grandes > 0:
                frame_ajuste_manual.controls.append(
                    ft.Text("Refeições Grandes:", weight=ft.FontWeight.BOLD)
                )
                for i in range(num_grandes):
                    campos = criar_linha_refeicao(
                        "Grande", i,
                        distribuicao['por_refeicao_grande']
                    )
                    widgets_refeicoes['grandes'].append(campos)
                    frame_ajuste_manual.controls.append(
                        ft.Row([
                            ft.Text(f"Grande {i + 1}:"),
                            campos['carb'],
                            campos['prot'],
                            campos['gord'],
                        ], spacing=10)
                    )

            if distribuicao and num_pequenas > 0:
                frame_ajuste_manual.controls.append(
                    ft.Text("Refeições Pequenas:", weight=ft.FontWeight.BOLD)
                )
                for i in range(num_pequenas):
                    campos = criar_linha_refeicao(
                        "Pequena", i,
                        distribuicao['por_refeicao_pequena']
                    )
                    widgets_refeicoes['pequenas'].append(campos)
                    frame_ajuste_manual.controls.append(
                        ft.Row([
                            ft.Text(f"Pequena {i + 1}:"),
                            campos['carb'],
                            campos['prot'],
                            campos['gord'],
                        ], spacing=10)
                    )

            frame_ajuste_manual.controls.append(
                ft.Row([
                    ft.FilledButton("Recalcular Totais", on_click=recalcular_totais_manuais),
                    ft.FilledButton("Copiar Plano Completo", on_click=copiar_plano_completo),
                    ft.FilledButton("Salvar em Arquivo", on_click=salvar_plano_em_arquivo),
                ], alignment=ft.MainAxisAlignment.CENTER)
            )
        page.update()

    def gerar_texto_plano_completo():
        """Gera o texto formatado do plano alimentar final para copiar ou salvar."""
        nonlocal ultimo_resultado, widgets_refeicoes

        if 'resultado_calorias' not in ultimo_resultado or 'macros_totais' not in ultimo_resultado:
            show_message("Calcule a necessidade calórica e a distribuição de macros primeiro.", error=True)
            return None

        res_cal = ultimo_resultado['resultado_calorias']
        peso = ultimo_resultado.get('peso', 0)

        try:
            refeicoes_grandes_data = []
            for campos in widgets_refeicoes['grandes']:
                refeicoes_grandes_data.append({
                    'proteina': int(campos['prot'].value),
                    'carboidrato': int(campos['carb'].value),
                    'gordura': int(campos['gord'].value)
                })

            refeicoes_pequenas_data = []
            for campos in widgets_refeicoes['pequenas']:
                refeicoes_pequenas_data.append({
                    'proteina': int(campos['prot'].value),
                    'carboidrato': int(campos['carb'].value),
                    'gordura': int(campos['gord'].value)
                })
            
            macros_ajustados = somar_macros_refeicoes(refeicoes_grandes_data, refeicoes_pequenas_data)

        except (ValueError, TypeError):
            show_message("Valores inválidos nos campos de refeição. Por favor, corrija antes de exportar.", error=True)
            return None

        prot_g = macros_ajustados['proteina']
        carb_g = macros_ajustados['carboidrato']
        gord_g = macros_ajustados['gordura']

        prot_gkg = round(prot_g / peso, 2) if peso > 0 else 0
        carb_gkg = round(carb_g / peso, 2) if peso > 0 else 0
        gord_gkg = round(gord_g / peso, 2) if peso > 0 else 0
        total_kcal_final = (prot_g * 4) + (carb_g * 4) + (gord_g * 9)

        texto = (
            f"PLANO ALIMENTAR COMPLETO\n"
            f"================================\n\n"
            f"1. NECESSIDADE CALÓRICA INICIAL\n"
            f"--------------------------------\n"
            f"TMB: {res_cal['tmb']} kcal\n"
            f"Calorias para Manutenção: {res_cal['calorias_manutencao']} kcal\n"
            f"Meta Calórica Inicial: {res_cal['calorias_objetivo']} kcal\n\n"
            f"2. TOTAIS DE MACRONUTRIENTES (AJUSTADO)\n"
            f"--------------------------------\n"
            f"Calorias Totais Ajustadas: {total_kcal_final} kcal\n"
            f"Proteína: {prot_g} g ({prot_gkg} g/kg)\n"
            f"Carboidrato: {carb_g} g ({carb_gkg} g/kg)\n"
            f"Gordura: {gord_g} g ({gord_gkg} g/kg)\n\n"
            f"3. DISTRIBUIÇÃO POR REFEIÇÃO\n"
            f"--------------------------------\n"
        )

        if widgets_refeicoes['grandes']:
            texto += "Refeições Grandes:\n"
            for i, campos in enumerate(widgets_refeicoes['grandes']):
                c = campos['carb'].value
                p = campos['prot'].value
                g = campos['gord'].value
                texto += f"  - Refeição {i+1}: Carb: {c}g, Prot: {p}g, Gord: {g}g\n"
            texto += "\n"

        if widgets_refeicoes['pequenas']:
            texto += "Refeições Pequenas:\n"
            for i, campos in enumerate(widgets_refeicoes['pequenas']):
                c = campos['carb'].value
                p = campos['prot'].value
                g = campos['gord'].value
                texto += f"  - Refeição {i+1}: Carb: {c}g, Prot: {p}g, Gord: {g}g\n"

        return texto

    def copiar_plano_completo(e):
        """Copia o plano alimentar final e detalhado para a área de transferência."""
        texto_para_copiar = gerar_texto_plano_completo()
        if texto_para_copiar:
            page.set_clipboard(texto_para_copiar)
            show_message("O plano alimentar completo foi copiado para a área de transferência.")

    def on_dialog_result(e: ft.FilePickerResultEvent):
        if e.path:
            text_to_save = gerar_texto_plano_completo()
            if text_to_save:
                try:
                    with open(e.path, 'w', encoding='utf-8') as file:
                        file.write(text_to_save)
                    show_message(f"Plano salvo com sucesso em:\n{e.path}")
                except Exception as ex:
                    show_message(f"Não foi possível salvar o arquivo.\nErro: {ex}", error=True)
        page.update()

    file_picker = ft.FilePicker(on_result=on_dialog_result)
    page.overlay.append(file_picker)

    def salvar_plano_em_arquivo(e):
        """Abre uma janela para salvar o plano em um arquivo de texto."""
        text_to_save = gerar_texto_plano_completo()
        if text_to_save:
            file_picker.save_file(
                "Salvar Plano Alimentar Como...",
                file_type=ft.FilePickerFileType.TEXT,
                allowed_extensions=["txt"],
            )

    def store_old_value(e):
        """Guarda o valor de um campo quando ele ganha foco."""
        global entry_old_values
        widget = e.control
        try:
            entry_old_values[widget] = int(widget.value)
        except (ValueError, TypeError):
            entry_old_values[widget] = 0

    def on_macro_field_change(e, meal_type, changed_index, macro_key):
        """
        Acionado quando um campo de macro perde o foco.
        Calcula a diferença e redistribui entre os outros campos do mesmo tipo.
        """
        if not redistribuicao_automatica_ativada.current.value:
            recalcular_totais_manuais()
            return

        nonlocal widgets_refeicoes, entry_old_values
        changed_widget = e.control

        old_value = entry_old_values.get(changed_widget, 0)

        try:
            new_value = int(changed_widget.value)
        except ValueError:
            changed_widget.value = str(old_value)
            changed_widget.update()
            return

        delta = old_value - new_value
        if delta == 0:
            return

        peer_widgets = []
        for i, widget_info in enumerate(widgets_refeicoes[meal_type]):
            if i != changed_index:
                peer_widgets.append(widget_info[macro_key])

        if not peer_widgets:
            recalcular_totais_manuais()
            return

        base_redistribution = delta // len(peer_widgets)
        remainder = delta % len(peer_widgets)

        for i, widget in enumerate(peer_widgets):
            try:
                current_peer_value = int(widget.value)
                amount_to_add = base_redistribution
                if i < remainder:
                    amount_to_add += 1

                new_peer_value = current_peer_value + amount_to_add
                widget.value = str(new_peer_value)
                widget.update()
            except ValueError:
                continue

        recalcular_totais_manuais()


    def criar_linha_refeicao(label_prefix, index_in_type, data):
        """Cria e retorna uma linha de widgets para uma refeição."""
        meal_type = 'grandes' if 'Grande' in label_prefix else 'pequenas'

        campos = {}
        macro_map = {'carb': 'carboidrato', 'prot': 'proteina', 'gord': 'gordura'}

        for short_name, long_name in macro_map.items():
            entry = ft.TextField(
                width=80,
                text_align=ft.TextAlign.CENTER,
                value=str(data.get(long_name, 0)),
                on_focus=store_old_value,
                on_blur=lambda e, mt=meal_type, idx=index_in_type, mk=short_name: on_macro_field_change(e, mt, idx, mk),
                input_filter=ft.InputFilter(allow=True, regex_string=r"[0-9]", replacement_string=""), # Apenas números
            )
            campos[short_name] = entry

        return campos


    def calcular_regra_de_3(e):
        """Calcula o valor X na regra de três e exibe na interface."""
        try:
            valor_a = float(entry_r3_a.value)
            valor_b = float(entry_r3_b.value)
            valor_c = float(entry_r3_c.value)

            if valor_a == 0:
                show_message("O 'Valor A' não pode ser zero (divisão por zero).", error=True)
                return

            resultado = (valor_b * valor_c) / valor_a
            label_r3_resultado_valor.value = f"{resultado:.4f}"
            show_message("Cálculo da regra de 3 realizado com sucesso!")

        except ValueError:
            show_message("Por favor, insira apenas números válidos nos campos.", error=True)
        except Exception as ex:
            show_message(f"Ocorreu um erro: {ex}", error=True)
        page.update()


    def limpar_regra_de_3(e):
        """Limpa todos os campos e o resultado da calculadora de regra de três."""
        entry_r3_a.value = ""
        entry_r3_b.value = ""
        entry_r3_c.value = ""
        label_r3_resultado_valor.value = "---"
        entry_r3_a.update()
        entry_r3_b.update()
        entry_r3_c.update()
        label_r3_resultado_valor.update()
        show_message("Campos da Regra de 3 limpos.")


    # =========================================================
    # ===== ABA 1: CALCULADORA DE CALORIAS ====================
    # =========================================================

    entry_peso = ft.TextField(label="Peso (kg)", width=200, input_filter=ft.InputFilter(allow=True, regex_string=r"[0-9\.]", replacement_string=""))
    entry_altura = ft.TextField(label="Altura (cm)", width=200, input_filter=ft.InputFilter(allow=True, regex_string=r"[0-9\.]", replacement_string=""))
    entry_idade = ft.TextField(label="Idade (anos)", width=200, input_filter=ft.InputFilter(allow=True, regex_string=r"[0-9]", replacement_string=""))
    combo_sexo = ft.Dropdown(
        label="Sexo",
        options=[
            ft.dropdown.Option("Masculino"),
            ft.dropdown.Option("Feminino"),
            ft.dropdown.Option("Criança"),
        ],
        value="Feminino",
        width=200
    )
    combo_nivel_atividade = ft.Dropdown(
        label="Nível de Atividade",
        options=[
            ft.dropdown.Option('Sedentário (pouco ou nenhum exercício)'),
            ft.dropdown.Option('Levemente Ativo (exercício 1-3 dias/semana)'),
            ft.dropdown.Option('Moderadamente Ativo (exercício 3-5 dias/semana)'),
            ft.dropdown.Option('Muito Ativo (exercício 6-7 dias/semana)'),
            ft.dropdown.Option('Extremamente Ativo (exercício muito pesado/trabalho físico)'),
        ],
        value='Levemente Ativo (exercício 1-3 dias/semana)',
        width=350
    )
    combo_objetivo = ft.Dropdown(
        label="Objetivo",
        options=[
            ft.dropdown.Option('Perder Peso'),
            ft.dropdown.Option('Manter Peso'),
            ft.dropdown.Option('Ganhar Peso'),
        ],
        value='Manter Peso',
        width=200
    )

    label_resultado_tmb_cal = ft.Text("Taxa Metabólica Basal (TMB): - kcal/dia")
    label_resultado_fator_cal = ft.Text("Fator de Atividade (NAF): -")
    label_resultado_manutencao_cal = ft.Text("Calorias para Manutenção: - kcal/dia")
    label_resultado_objetivo_cal = ft.Text("Meta para Objetivo: - kcal/dia", size=16, weight=ft.FontWeight.BOLD)

    tab_calorias_content = ft.Column(
        [
            ft.Text("Dados do Paciente", size=16, weight=ft.FontWeight.BOLD),
            ft.Row([ft.Column([entry_peso, entry_altura, entry_idade]),
                    ft.Column([combo_sexo, combo_nivel_atividade, combo_objetivo])]),
            ft.Row(
                [
                    ft.FilledButton("Calcular Necessidade", on_click=executar_calculo_calorias),
                    ft.FilledButton("Copiar Resultados", on_click=copiar_resultados_calorias),
                    ft.FilledButton("Avançar para Distribuição →", on_click=ir_para_distribuicao),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            ft.Divider(),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Resultados do Cálculo Calórico", size=14, weight=ft.FontWeight.BOLD),
                        label_resultado_tmb_cal,
                        label_resultado_fator_cal,
                        label_resultado_manutencao_cal,
                        label_resultado_objetivo_cal,
                    ]
                ),
                padding=10,
                border=ft.border.all(1, ft.colors.BLUE_GREY_100),
                border_radius=5,
            )
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=15
    )

    # ==========================================================
    # ===== ABA 2: DISTRIBUIÇÃO DE DIETA =======================
    # ==========================================================

    entry_total_kcal_macro = ft.TextField(label="Meta Calórica (kcal)", width=150, input_filter=ft.InputFilter(allow=True, regex_string=r"[0-9]", replacement_string=""))
    entry_peso_paciente_macro = ft.TextField(label="Peso do Paciente (kg)", width=150, input_filter=ft.InputFilter(allow=True, regex_string=r"[0-9\.]", replacement_string=""))
    entry_perc_prot = ft.TextField(label="Proteínas (%)", value="20.0", width=150, input_filter=ft.InputFilter(allow=True, regex_string=r"[0-9\.]", replacement_string=""))
    entry_perc_carb = ft.TextField(label="Carboidratos (%)", value="45.0", width=150, input_filter=ft.InputFilter(allow=True, regex_string=r"[0-9\.]", replacement_string=""))
    entry_perc_gord = ft.TextField(label="Gorduras (%)", value="35.0", width=150, input_filter=ft.InputFilter(allow=True, regex_string=r"[0-9\.]", replacement_string=""))
    entry_num_grandes = ft.TextField(label="Nº Refeições Grandes", value="3", width=150, input_filter=ft.InputFilter(allow=True, regex_string=r"[0-9]", replacement_string=""))
    entry_num_pequenas = ft.TextField(label="Nº Refeições Pequenas", value="3", width=150, input_filter=ft.InputFilter(allow=True, regex_string=r"[0-9]", replacement_string=""))
    entry_perc_dist_grandes = ft.TextField(label="% Cal. nas Grandes", value="70", width=150, input_filter=ft.InputFilter(allow=True, regex_string=r"[0-9]", replacement_string=""))

    label_resultado_prot_total = ft.Text("Proteína: - g (- g/kg)")
    label_resultado_carb_total = ft.Text("Carboidrato: - g (- g/kg)")
    label_resultado_gord_total = ft.Text("Gordura: - g (- g/kg)")
    label_kcal_ajustado = ft.Text("Total Ajustado: - kcal", weight=ft.FontWeight.BOLD)

    frame_totais = ft.Column(
        [
            ft.Text("Totais Diários:", weight=ft.FontWeight.BOLD),
            label_resultado_prot_total,
            label_resultado_carb_total,
            label_resultado_gord_total,
            label_kcal_ajustado,
        ]
    )

    frame_ajuste_manual = ft.Column(
        controls=[],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=10
    )

    frame_resultados = ft.Container(
        content=ft.Column(
            [
                ft.Text("Resultados e Ajustes", size=14, weight=ft.FontWeight.BOLD),
                frame_totais,
                ft.Divider(),
                frame_ajuste_manual
            ]
        ),
        padding=10,
        border=ft.border.all(1, ft.colors.BLUE_GREY_100),
        border_radius=5,
        visible=False
    )

    tab_macros_content = ft.Column(
        [
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Configuração Inicial", size=14, weight=ft.FontWeight.BOLD),
                        ft.Row([
                            ft.Column([entry_total_kcal_macro, entry_peso_paciente_macro, entry_perc_prot]),
                            ft.Column([entry_perc_carb, entry_perc_gord, entry_num_grandes]),
                            ft.Column([entry_num_pequenas, entry_perc_dist_grandes]),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        wrap=True
                        )
                    ]
                ),
                padding=10,
                border=ft.border.all(1, ft.colors.BLUE_GREY_100),
                border_radius=5,
            ),
            ft.FilledButton("Calcular Distribuição", on_click=executar_calculo_macros),
            frame_resultados
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=15,
        scroll=ft.ScrollMode.ADAPTIVE # Adiciona scroll caso o conteúdo exceda a altura
    )


    # =========================================================
    # ===== ABA 3: REGRA DE TRÊS ==============================
    # =========================================================

    entry_r3_a = ft.TextField(label="Valor A", width=150, text_align=ft.TextAlign.CENTER, input_filter=ft.InputFilter(allow=True, regex_string=r"[0-9\.]", replacement_string=""))
    entry_r3_b = ft.TextField(label="Valor B", width=150, text_align=ft.TextAlign.CENTER, input_filter=ft.InputFilter(allow=True, regex_string=r"[0-9\.]", replacement_string=""))
    entry_r3_c = ft.TextField(label="Valor C", width=150, text_align=ft.TextAlign.CENTER, input_filter=ft.InputFilter(allow=True, regex_string=r"[0-9\.]", replacement_string=""))
    label_r3_resultado_valor = ft.Text("---", size=20, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE_500, width=150, text_align=ft.TextAlign.CENTER)

    tab_regra3_content = ft.Column(
        [
            ft.Row(
                [
                    entry_r3_a,
                    ft.Text("está para"),
                    entry_r3_b,
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=10
            ),
            ft.Text("assim como", weight=ft.FontWeight.BOLD),
            ft.Row(
                [
                    entry_r3_c,
                    ft.Text("está para"),
                    ft.Column([ft.Text("Resultado (X):", weight=ft.FontWeight.BOLD), label_r3_resultado_valor],
                              horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=10
            ),
            ft.Row(
                [
                    ft.FilledButton("Calcular", on_click=calcular_regra_de_3),
                    ft.FilledButton("Limpar Campos", on_click=limpar_regra_de_3),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=20
            )
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=20
    )


    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            ft.Tab(text="1. Necessidade Calórica", content=tab_calorias_content),
            ft.Tab(text="2. Distribuição de Dieta", content=tab_macros_content),
            ft.Tab(text="Calculadora de Regra de 3", content=tab_regra3_content),
        ],
        expand=1,
    )

    page.add(tabs)

if __name__ == "__main__":
    ft.app(target=main)