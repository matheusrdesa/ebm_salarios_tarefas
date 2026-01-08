import pandas as pd
import os
import re
import glob

# --- CONFIGURAÇÕES ---
DIRETORIO_ATUAL = os.getcwd()
PASTA_RAW = os.path.join(DIRETORIO_ATUAL, "dados_raw")
PASTA_SAIDA = os.path.join(DIRETORIO_ATUAL, "dados_tratados")

if not os.path.exists(PASTA_SAIDA):
    os.makedirs(PASTA_SAIDA)

def limpar_moeda(valor):
    """
    Transforma strings financeiras BR (ex: '1.250,00') em float python (1250.0).
    Lida com R$, espaços e converte corretamente milhar/decimal.
    """
    if pd.isna(valor) or valor == '':
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    
    s = str(valor).strip()
    s = re.sub(r'[R$\s]', '', s) # Remove R$ e espaços
    s = s.replace('.', '')       # Remove ponto de milhar
    s = s.replace(',', '.')      # Vírgula vira ponto decimal
    
    try:
        return float(s)
    except ValueError:
        return 0.0

def extrair_metadados_nome_arquivo(nome_arquivo):
    try:
        base = nome_arquivo.replace('.xlsx', '')
        partes = base.split(' - ')
        competencia = partes[-1]
        nome_obra = partes[-2] if len(partes) >= 2 else "DESCONHECIDO"
        return nome_obra, competencia
    except:
        return "DESCONHECIDO", "0000-00"

def processar_servicos(row, nome_obra, competencia):
    texto_bruto = row.get('Descrição dos serviços', '')
    if pd.isna(texto_bruto): return []

    linhas = str(texto_bruto).split('\n')
    tarefas_extraidas = []
    regex_padrao = r'(.*?):\s*\((.*?)\)\s*([\d\.,]+)'
    
    for linha in linhas:
        linha = linha.strip()
        if not linha: continue
        
        match = re.search(regex_padrao, linha)
        if match:
            tarefas_extraidas.append({
                'Competencia': competencia,
                'Obra': nome_obra,
                'Funcionario': row.get('Nome', 'Não Identificado'),
                'Funcao': row.get('Função', 'Não Identificado'),
                'Tipo': 'Produção',
                'Descricao_Servico': match.group(1).strip(),
                'Centro_Custo': match.group(2).strip(),
                'Valor_Tarefa': limpar_moeda(match.group(3).strip())
            })
        else:
            # Captura linhas fora do padrão (Ajustes, Prêmios manuais no texto, etc)
            match_valor = re.search(r'([\d\.,]+)$', linha)
            valor = limpar_moeda(match_valor.group(1)) if match_valor else 0.0
            
            tipo_item = 'Outros'
            if any(k in linha.lower() for k in ['prêmio', 'premio', 'gratificação']):
                tipo_item = 'Prêmio (Texto)'

            tarefas_extraidas.append({
                'Competencia': competencia,
                'Obra': nome_obra,
                'Funcionario': row.get('Nome', 'Não Identificado'),
                'Funcao': row.get('Função', 'Não Identificado'),
                'Tipo': tipo_item,
                'Descricao_Servico': linha,
                'Centro_Custo': 'Geral',
                'Valor_Tarefa': valor
            })
    return tarefas_extraidas

def main_etl():
    print(f">>> INICIANDO ETL (LEITURA EXATA DAS COLUNAS) <<<")
    arquivos = glob.glob(os.path.join(PASTA_RAW, "*.xlsx"))
    
    if not arquivos:
        print("[ERRO] Nenhum arquivo .xlsx encontrado na pasta dados_raw!")
        return
    
    lista_salarios = []
    lista_tarefas = []
    
    # LISTA DE COLUNAS EXATAS PARA LER DO EXCEL
    colunas_numericas_salarios = [
        'Salario Base (R$)', 
        'HE 50% (em tarefas)', 
        'HE 50% (fora tarefas)',
        'Valor das tarefas (R$)', 
        'Saldo de tarefas', 
        'Adicional',
        'Salário bruto (R$)',          # Bruto antes dos descontos
        'Salário bruto - faltas (R$)', # Valor Líquido/Pago pela empresa (KPI Principal)
        'Valor total de prêmios (R$)'  # <--- COLUNA FALTANTE ADICIONADA
    ]
    
    colunas_justificativa = ['Justificativa', 'Justificativas', 'Observação', 'Obs']

    for arquivo in arquivos:
        nome_arquivo = os.path.basename(arquivo)
        print(f"Lendo: {nome_arquivo}...")
        
        try:
            obra, competencia = extrair_metadados_nome_arquivo(nome_arquivo)
            
            # Leitura do Excel com tentativas de engine
            try:
                df = pd.read_excel(arquivo, engine='openpyxl')
                if 'Nome' not in df.columns:
                     df = pd.read_excel(arquivo, engine='openpyxl', skiprows=1)
            except Exception as e:
                print(f" -> Erro leitura Excel: {e}")
                continue
            
            # Normaliza colunas (remove espaços extras no nome)
            df.columns = [c.strip() for c in df.columns]

            # --- PROCESSAR SALÁRIOS ---
            df_sal = df.copy()
            df_sal['Obra'] = obra
            df_sal['Competencia'] = competencia
            
            # Tratamento Numérico (Limpeza de Moeda)
            for col in colunas_numericas_salarios:
                if col in df_sal.columns:
                    df_sal[col] = df_sal[col].apply(limpar_moeda)
                else:
                    # Se não achar a coluna, cria zerada para não quebrar o padrão
                    # (mas avisa no print para você saber)
                    # print(f" -> Aviso: Coluna '{col}' não encontrada em {nome_arquivo}")
                    df_sal[col] = 0.0

            # Tratamento de Justificativas (Concatena possíveis colunas de obs)
            df_sal['Justificativa_Final'] = ""
            for col_txt in colunas_justificativa:
                if col_txt in df_sal.columns:
                    df_sal['Justificativa_Final'] += df_sal[col_txt].fillna('').astype(str) + " "
            df_sal['Justificativa_Final'] = df_sal['Justificativa_Final'].str.strip()

            # Seleção Final
            cols_export = ['Competencia', 'Obra', 'Nome', 'Função', 'Justificativa_Final'] + colunas_numericas_salarios
            # Filtra apenas colunas que realmente existem no DF agora
            cols_export = [c for c in cols_export if c in df_sal.columns]
            
            lista_salarios.append(df_sal[cols_export])

            # --- PROCESSAR TAREFAS ---
            if 'Descrição dos serviços' in df.columns:
                for _, row in df.iterrows():
                    tarefas = processar_servicos(row, obra, competencia)
                    lista_tarefas.extend(tarefas)
                
        except Exception as e:
            print(f" -> [ERRO] Falha no arquivo {nome_arquivo}: {e}")

    # Salvar Arquivos Finais
    if lista_salarios:
        final_sal = pd.concat(lista_salarios, ignore_index=True)
        final_sal.rename(columns={'Justificativa_Final': 'Justificativa'}, inplace=True)
        
        caminho_sal = os.path.join(PASTA_SAIDA, "base_salarios_consolidada.csv")
        final_sal.to_csv(caminho_sal, sep=';', index=False, encoding='utf-8-sig', decimal=',')
        print(f"[SUCESSO] Salários Consolidados: {len(final_sal)} registros.")

    if lista_tarefas:
        final_tar = pd.DataFrame(lista_tarefas)
        caminho_tar = os.path.join(PASTA_SAIDA, "base_tarefas_detalhada.csv")
        final_tar.to_csv(caminho_tar, sep=';', index=False, encoding='utf-8-sig', decimal=',')
        print(f"[SUCESSO] Tarefas Detalhadas: {len(final_tar)} registros.")

if __name__ == "__main__":
    main_etl()