# calculadoras.py

def calcular_tmb(peso_kg, altura_cm, idade_anos, sexo):
    """
    Calcula a Taxa Metabólica Basal (TMB) usando a equação de Mifflin-St Jeor para adultos e Schofield para crianças.
    """
    if not all([peso_kg, altura_cm, idade_anos, sexo]):
        return None
    try:
        peso_kg = float(peso_kg)
        altura_cm = float(altura_cm)
        idade_anos = int(idade_anos)
        if peso_kg <= 0 or altura_cm <= 0 or idade_anos <= 0:
            return None
    except (ValueError, TypeError):
        return None

    sexo = sexo.strip().lower()

    if sexo == 'criança':
        if idade_anos >= 18:
            return None
        tmb = 0
        if 0 <= idade_anos <= 3:
            tmb = (59.512 * peso_kg) - 30.4
        elif 3 < idade_anos <= 10:
            tmb = (22.706 * peso_kg) + 504.3
        elif 10 < idade_anos < 18:
            tmb = (17.686 * peso_kg) + 658.2
        else:
            return None
        return round(tmb)
    elif sexo == 'masculino':
        tmb = (10 * peso_kg) + (6.25 * altura_cm) - (5 * idade_anos) + 5
        return round(tmb)
    elif sexo == 'feminino':
        tmb = (10 * peso_kg) + (6.25 * altura_cm) - (5 * idade_anos) - 161
        return round(tmb)
    else:
        return None

def calcular_necessidade_calorica(peso_kg, altura_cm, idade_anos, sexo, nivel_atividade, objetivo):
    """
    Calcula a necessidade calórica total com base nos inputs.
    """
    tmb = calcular_tmb(peso_kg, altura_cm, idade_anos, sexo)
    if tmb is None:
        return None
    fatores_naf = {
        'sedentario': 1.2, 'leve': 1.375, 'moderado': 1.55,
        'ativo': 1.725, 'extremo': 1.9
    }
    fator_naf_selecionado = fatores_naf.get(nivel_atividade.strip().lower())
    if fator_naf_selecionado is None:
        return None
    calorias_manutencao = round(tmb * fator_naf_selecionado)
    calorias_objetivo = calorias_manutencao
    objetivo = objetivo.strip().lower()
    if objetivo == 'perder':
        calorias_objetivo -= 500
    elif objetivo == 'ganhar':
        calorias_objetivo += 500
    elif objetivo != 'manter':
        return None
    return {
        'tmb': tmb,
        'fator_atividade': fator_naf_selecionado,
        'calorias_manutencao': calorias_manutencao,
        'calorias_objetivo': calorias_objetivo
    }

def calcular_macros_por_porcentagem(total_kcal, perc_carb, perc_prot, perc_gord):
    """Calcula os gramas de macros com base na distribuição percentual."""
    try:
        total_perc = perc_carb + perc_prot + perc_gord
        # CORREÇÃO: Usar uma margem de erro para comparar pontos flutuantes.
        if abs(total_perc - 100) > 0.1:
            return None
        gramas_carb = round((total_kcal * (perc_carb / 100.0)) / 4)
        gramas_prot = round((total_kcal * (perc_prot / 100.0)) / 4)
        gramas_gord = round((total_kcal * (perc_gord / 100.0)) / 9)
        return {'carboidrato': gramas_carb, 'proteina': gramas_prot, 'gordura': gramas_gord}
    except Exception:
        return None

def distribuir_macros_nas_refeicoes(macros_em_gramas, num_grandes, num_pequenas, perc_dist_grandes):
    """Distribui os gramas de macros entre as refeições grandes e pequenas."""
    try:
        if (num_grandes + num_pequenas) == 0:
            return None
        perc_dist_pequenas = 100 - perc_dist_grandes
        
        gramas_carb_grandes_total = macros_em_gramas['carboidrato'] * (perc_dist_grandes / 100.0)
        gramas_prot_grandes_total = macros_em_gramas['proteina'] * (perc_dist_grandes / 100.0)
        gramas_gord_grandes_total = macros_em_gramas['gordura'] * (perc_dist_grandes / 100.0)

        gramas_carb_pequenas_total = macros_em_gramas['carboidrato'] * (perc_dist_pequenas / 100.0)
        gramas_prot_pequenas_total = macros_em_gramas['proteina'] * (perc_dist_pequenas / 100.0)
        gramas_gord_pequenas_total = macros_em_gramas['gordura'] * (perc_dist_pequenas / 100.0)
        
        return {
            'por_refeicao_grande': {
                'carboidrato': round(gramas_carb_grandes_total / num_grandes) if num_grandes > 0 else 0,
                'proteina': round(gramas_prot_grandes_total / num_grandes) if num_grandes > 0 else 0,
                'gordura': round(gramas_gord_grandes_total / num_grandes) if num_grandes > 0 else 0
            },
            'por_refeicao_pequena': {
                'carboidrato': round(gramas_carb_pequenas_total / num_pequenas) if num_pequenas > 0 else 0,
                'proteina': round(gramas_prot_pequenas_total / num_pequenas) if num_pequenas > 0 else 0,
                'gordura': round(gramas_gord_pequenas_total / num_pequenas) if num_pequenas > 0 else 0
            }
        }
    except Exception:
        return None

def somar_macros_refeicoes(refeicoes_grandes, refeicoes_pequenas):
    """
    Soma os gramas de macros de todas as refeições ajustadas manualmente.
    """
    macros_somados = {'proteina': 0, 'carboidrato': 0, 'gordura': 0}
    try:
        for refeicao in refeicoes_grandes + refeicoes_pequenas:
            macros_somados['proteina'] += refeicao.get('proteina', 0)
            macros_somados['carboidrato'] += refeicao.get('carboidrato', 0)
            macros_somados['gordura'] += refeicao.get('gordura', 0)
        return macros_somados
    except (ValueError, TypeError):
        return None