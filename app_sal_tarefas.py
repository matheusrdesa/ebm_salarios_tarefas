import dash
from dash import dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from dash.dash_table.Format import Format, Scheme, Symbol, Group
import pandas as pd
import os

# =============================================================================
# 1. CONFIGURAÇÃO DE SEGURANÇA (LOGIN)
# =============================================================================
# DEFINA AQUI SEUS USUÁRIOS E SENHAS
USUARIOS = {
    "admin": "admin",  # <--- TROQUE A SENHA AQUI
    "rubens.prudencini": "ebm2026",
}

# =============================================================================
# 2. CONFIGURAÇÃO VISUAL E APP
# =============================================================================
FONT_AWESOME = "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css"

# IMPORTANTE: suppress_callback_exceptions=True é necessário para login dinâmico
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.SLATE, FONT_AWESOME], title="Gestão de Obras", suppress_callback_exceptions=True)
server = app.server

# Paleta Padronizada
COLORS = {
    'background': '#0f172a', 'card_bg': '#1e293b', 'filter_bg': '#020617',
    'text': '#f8fafc', 'subtext': '#94a3b8',
    'accent_main': '#06b6d4', 
    'danger': '#f43f5e', 'success': '#10b981', 
    'azul': '#3b82f6', 'roxo': '#a855f7', 'cyan': '#06b6d4',
    'grid': '#334155', 'base_gray': '#475569'
}

BLUE_NEON_SCALE = [(0.0, "#172554"), (0.5, "#1e40af"), (1.0, "#3b82f6")]
money_fmt = Format(precision=2, scheme=Scheme.fixed, symbol=Symbol.yes, symbol_prefix='R$ ', group=Group.yes, group_delimiter='.', decimal_delimiter=',')
hour_fmt = Format(precision=1, scheme=Scheme.fixed, symbol=Symbol.yes, symbol_suffix=' h')

def update_layout_theme(fig):
    fig.update_layout(
        template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        separators=",.", font={'color': COLORS['text'], 'family': 'Segoe UI, sans-serif'},
        margin=dict(l=20, r=20, t=40, b=20),
        hoverlabel=dict(bgcolor=COLORS['card_bg'], bordercolor=COLORS['cyan'], font_color='white', font_size=13, font_family="Segoe UI")
    )
    return fig

# =============================================================================
# 3. DADOS E LÓGICA (MANTIDO ORIGINAL)
# =============================================================================
TERMOS_INDIRETOS = [
    'MESTRE', 'ENCARREGADO', 'ESTAGIARIO', 'ESTAGIÁRIO', 'ENGENHEIRO', 'TECNICO', 'TÉCNICO', 
    'ANALISTA', 'ASSISTENTE', 'AUXILIAR', 'COORDENADOR', 'GERENTE', 'ALMOXARIFE', 
    'ADMINISTRATIVO', 'APONTADOR', 'VIGIA', 'GUARITA'
]

def classificar_mo(funcao):
    if pd.isna(funcao): return 'Direto'
    if any(termo in str(funcao).upper() for termo in TERMOS_INDIRETOS): return 'Indireto'
    return 'Direto'

# Ajuste para ler da pasta dados_tratados corretamente no Render
PASTA_DADOS = os.path.join(os.getcwd(), 'dados_tratados')

def tropicalizar_valor_input(valor):
    if pd.isna(valor) or valor == '': return 0.0
    if isinstance(valor, (float, int)): return float(valor)
    s = str(valor).replace('R$', '').replace(' ', '').strip()
    try:
        if ',' in s: s = s.replace('.', '').replace(',', '.')
        return float(s)
    except: return 0.0

def load_data():
    try:
        df_tar = pd.read_csv(os.path.join(PASTA_DADOS, 'base_tarefas_detalhada.csv'), sep=';', dtype=str)
        df_sal = pd.read_csv(os.path.join(PASTA_DADOS, 'base_salarios_consolidada.csv'), sep=';', dtype=str)
        df_tar.columns = df_tar.columns.str.strip()
        df_sal.columns = df_sal.columns.str.strip()

        cols_num = ['Salario Base (R$)', 'HE 50% (em tarefas)', 'HE 50% (fora tarefas)',
                    'Valor das tarefas (R$)', 'Salário bruto (R$)', 
                    'Valor total de prêmios (R$)', 'Salário bruto - faltas (R$)']
        
        for col in cols_num:
            if col in df_sal.columns: df_sal[col] = df_sal[col].apply(tropicalizar_valor_input)
            else: df_sal[col] = 0.0

        if 'Valor_Tarefa' in df_tar.columns: df_tar['Valor_Tarefa'] = df_tar['Valor_Tarefa'].apply(tropicalizar_valor_input)
        if 'Função' in df_sal.columns: df_sal['Tipo_MO'] = df_sal['Função'].apply(classificar_mo)
        else: df_sal['Tipo_MO'] = 'Direto'
        return df_tar, df_sal
    except FileNotFoundError: return pd.DataFrame(), pd.DataFrame()

df_tarefas, df_salarios = load_data()

# Tratamentos Globais
if not df_tarefas.empty:
    if 'Centro_Custo' in df_tarefas.columns: df_tarefas['Centro_Custo'] = df_tarefas['Centro_Custo'].fillna('N/I')
    if 'Descricao_Servico' in df_tarefas.columns: df_tarefas['Descricao_Servico'] = df_tarefas['Descricao_Servico'].fillna('Serviço N/I')
    if 'Tipo' not in df_tarefas.columns: df_tarefas['Tipo'] = 'Produção'

if not df_salarios.empty:
    if 'Função' in df_salarios.columns: df_salarios['Função'] = df_salarios['Função'].fillna('Outros')
    if 'Justificativa' in df_salarios.columns: df_salarios['Justificativa'] = df_salarios['Justificativa'].fillna('-')

obras = sorted(df_salarios['Obra'].unique()) if not df_salarios.empty else []
comps = sorted(df_salarios['Competencia'].unique()) if not df_salarios.empty else []

# =============================================================================
# 4. LAYOUTS (LOGIN vs DASHBOARD)
# =============================================================================

# --- A. TELA DE LOGIN (MODERNA) ---
login_layout = html.Div(
    [
        dbc.Card(
            dbc.CardBody([
                # Cabeçalho do Card
                html.Div([
                    # Tente usar uma logo com fundo transparente se possível
                    html.Img(src=app.get_asset_url("logo.png"), style={'height': '80px', 'marginBottom': '10px', 'filter': 'brightness(0) invert(1)'}),
                    html.H4("EBM Labor Intelligence", style={'color': 'white', 'fontWeight': 'bold', 'marginBottom': '5px'}),
                    html.P("Acesso Restrito Administrativo", style={'color': COLORS['subtext'], 'fontSize': '0.9rem'}),
                ], className="text-center mb-4"),

                # Inputs Estilizados
                dbc.Label("USUÁRIO", style={'color': COLORS['accent_main'], 'fontWeight': 'bold', 'fontSize': '0.7rem'}),
                dbc.Input(
                    id="username-box", 
                    placeholder="Digite seu usuário...", 
                    type="text", 
                    className="mb-3",
                    style={'backgroundColor': '#0f172a', 'color': 'white', 'border': f'1px solid {COLORS["grid"]}', 'padding': '10px'}
                ),

                dbc.Label("SENHA", style={'color': COLORS['accent_main'], 'fontWeight': 'bold', 'fontSize': '0.7rem'}),
                dbc.Input(
                    id="password-box", 
                    placeholder="Digite sua senha...", 
                    type="password", 
                    className="mb-4",
                    style={'backgroundColor': '#0f172a', 'color': 'white', 'border': f'1px solid {COLORS["grid"]}', 'padding': '10px'}
                ),

                # Botão com Gradiente
                dbc.Button(
                    "ACESSAR SISTEMA", 
                    id="login-button", 
                    className="w-100", 
                    size="lg",
                    style={
                        'backgroundImage': 'linear-gradient(to right, #06b6d4, #3b82f6)', 
                        'border': 'none', 
                        'fontWeight': 'bold', 
                        'letterSpacing': '1px',
                        'transition': '0.3s'
                    }
                ),

                html.Div(id="login-output", className="text-danger text-center mt-3", style={'fontWeight': 'bold'})
            ]),
            style={
                'width': '100%', 
                'maxWidth': '420px', 
                'backgroundColor': 'rgba(30, 41, 59, 0.95)', # Leve transparência
                'border': f'1px solid {COLORS["grid"]}',
                'borderRadius': '16px',
                'boxShadow': '0 10px 25px -5px rgba(0, 0, 0, 0.5)' # Sombra elegante
            },
            className="shadow-2xl"
        ),
        
        # Rodapézinho discreto
        html.Div("Desenvolvido por EBM Dados © 2026", style={'position': 'absolute', 'bottom': '20px', 'color': COLORS['subtext'], 'fontSize': '0.8rem'})
    ],
    # Flexbox para centralizar PERFEITAMENTE na tela
    style={
        'height': '100vh',
        'width': '100vw',
        'display': 'flex',
        'justifyContent': 'center',
        'alignItems': 'center',
        'flexDirection': 'column',
        # Fundo Gradiente Escuro
        'background': 'radial-gradient(circle at center, #1e293b 0%, #020617 100%)'
    }
)

# --- B. LAYOUT DO DASHBOARD (Encapsulado em Função) ---
def get_dashboard_layout():
    sidebar = html.Div([
        html.Div([
            html.Img(src=app.get_asset_url("logo.png"), className="logo-white", style={'height': '40px'}),
            html.Span("FILTROS", style={'fontSize': '1.2rem', 'fontWeight': 'bold', 'marginLeft': '12px', 'color': 'white'})
        ], className="d-flex align-items-center mb-5 px-2"),

        html.Label("COMPETÊNCIA", className="small text-muted fw-bold mb-2 px-2"),
        dcc.Dropdown(id='filtro-competencia', options=[{'label': c, 'value': c} for c in comps], 
                     value=comps[-1] if comps else None, clearable=False, className="mb-4", style={'backgroundColor': COLORS['filter_bg']}),

        html.Label("OBRA", className="small text-muted fw-bold mb-2 px-2"),
        dcc.Dropdown(id='filtro-obra', options=[{'label': 'TODAS', 'value': 'TODAS'}] + [{'label': o, 'value': o} for o in obras], 
                     value='TODAS', clearable=False, className="mb-4"),

        html.Div([html.Hr(style={'borderColor': COLORS['grid']}), html.Small("v19.0 - Cálculo Qtd Horas", className="text-muted text-center d-block")], style={'marginTop': 'auto'})
    ], id="sidebar", className="sidebar")

    content = html.Div([
        html.Div([
            dbc.Button(html.I(className="fa-solid fa-bars"), id="btn_sidebar", color="link", style={'color': 'white', 'fontSize': '1.2rem', 'textDecoration': 'none'}),
            html.Img(src=app.get_asset_url("logo.png"), className="logo-white ms-4 me-3", style={'height': '45px'}),
            html.H3("Gestão de Tarefas e Custos de Obra", className="m-0 text-white", style={'fontWeight': 'bold'}),
            # Botão de Logout
            dbc.Button("Sair", id="logout-button", color="danger", size="sm", className="ms-auto", style={'fontWeight': 'bold'})
        ], className="d-flex align-items-center mb-4 pb-3", style={'borderBottom': f"1px solid {COLORS['grid']}"}),

        # KPIs
        dbc.Row([
            dbc.Col(html.Div([
                html.Div([html.I(className="fa-solid fa-money-check-dollar fa-lg", style={'color': COLORS['cyan']})], className="kpi-icon-container"),
                html.Div([html.H6("CUSTO REAL (PAGO)", style={'color': COLORS['subtext'], 'fontSize': '0.65rem', 'fontWeight': 'bold'}), html.H4(id="kpi-custo-real", style={'color': 'white', 'fontWeight': 'bold', 'fontSize': '1.1rem'})], className="ms-2")
            ], className="kpi-card d-flex align-items-center p-3 mb-4"), width=True),
            dbc.Col(html.Div([
                html.Div([html.I(className="fa-solid fa-hammer fa-lg", style={'color': COLORS['cyan']})], className="kpi-icon-container"),
                html.Div([html.H6("PRODUÇÃO MEDIDA", style={'color': COLORS['subtext'], 'fontSize': '0.65rem', 'fontWeight': 'bold'}), html.H4(id="kpi-prod", style={'color': 'white', 'fontWeight': 'bold', 'fontSize': '1.1rem'})], className="ms-2")
            ], className="kpi-card d-flex align-items-center p-3 mb-4"), width=True),
            dbc.Col(html.Div([
                html.Div([html.I(className="fa-solid fa-chart-line fa-lg", style={'color': COLORS['cyan']})], className="kpi-icon-container"),
                html.Div([html.H6("EFICIÊNCIA (DIRETOS)", style={'color': COLORS['subtext'], 'fontSize': '0.65rem', 'fontWeight': 'bold'}), html.Div(id="kpi-efic")], className="ms-2")
            ], className="kpi-card d-flex align-items-center p-3 mb-4"), width=True),
            dbc.Col(html.Div([
                html.Div([html.I(className="fa-solid fa-users-viewfinder fa-lg", style={'color': COLORS['cyan']})], className="kpi-icon-container"),
                html.Div([html.H6("% EQUIPE BONIFICADA", style={'color': COLORS['subtext'], 'fontSize': '0.65rem', 'fontWeight': 'bold'}), html.H4(id="kpi-pct-bonificada", style={'color': COLORS['success'], 'fontWeight': 'bold', 'fontSize': '1.1rem'})], className="ms-2")
            ], className="kpi-card d-flex align-items-center p-3 mb-4"), width=True),
            dbc.Col(html.Div([
                html.Div([html.I(className="fa-solid fa-scale-balanced fa-lg", style={'color': COLORS['cyan']})], className="kpi-icon-container"),
                html.Div([html.H6("RESULTADO (ROI)", style={'color': COLORS['subtext'], 'fontSize': '0.65rem', 'fontWeight': 'bold'}), html.Div(id="kpi-resultado")], className="ms-2")
            ], className="kpi-card d-flex align-items-center p-3 mb-4"), width=True),
            dbc.Col(html.Div([
                html.Div([html.I(className="fa-solid fa-hand-holding-dollar fa-lg", style={'color': COLORS['cyan']})], className="kpi-icon-container"),
                html.Div([html.H6("SUBSÍDIO (PERDA)", style={'color': COLORS['subtext'], 'fontSize': '0.65rem', 'fontWeight': 'bold'}), html.H4(id="kpi-desperdicio", style={'color': COLORS['danger'], 'fontWeight': 'bold', 'fontSize': '1.1rem'})], className="ms-2")
            ], className="kpi-card d-flex align-items-center p-3 mb-4"), width=True),
        ]),

        # ROI
        dbc.Row([
            dbc.Col(html.Div([
                html.H5("Balanço Financeiro Global (ROI da Produtividade)", className="mb-3", style={'fontWeight': 'bold'}),
                dcc.Graph(id='grafico-balanco-roi', style={'height': '350px'}, config={'displayModeBar': False})
            ], className="kpi-card p-4 mb-4"), width=12),
        ]),

        # Custo e Pizza
        dbc.Row([
            dbc.Col(html.Div([
                html.H5("Custo por Obra (Direto vs Indireto)", className="mb-3", style={'fontWeight': 'bold'}),
                dcc.Graph(id='grafico-obra-stack', style={'height': '400px'}, config={'displayModeBar': False})
            ], className="kpi-card p-4 mb-4"), width=12, lg=8),
            dbc.Col(html.Div([
                html.H5("Composição do Custo", className="mb-3", style={'fontWeight': 'bold'}),
                dcc.Graph(id='grafico-pie-mo', style={'height': '400px'}, config={'displayModeBar': False})
            ], className="kpi-card p-4 mb-4"), width=12, lg=4),
        ]),

        # HE
        dbc.Row([
            dbc.Col(html.Div([
                html.H5("Horas Extras por Obra (Geral - R$)", className="mb-3", style={'fontWeight': 'bold'}),
                dcc.Graph(id='grafico-he-obra', style={'height': '400px'}, config={'displayModeBar': False})
            ], className="kpi-card p-4 mb-4"), width=12, lg=6),
            dbc.Col(html.Div([
                html.H5("Ranking HE por Função (Top 10 - R$)", className="mb-3", style={'fontWeight': 'bold'}),
                dcc.Graph(id='grafico-he-funcao', style={'height': '400px'}, config={'displayModeBar': False})
            ], className="kpi-card p-4 mb-4"), width=12, lg=6),
        ]),
        
        # TOP Indiretos HE (QTD)
        dbc.Row([
            dbc.Col(html.Div([
                html.H5("Top 10 Indiretos: Quantidade de Horas Extras (Estimado)", className="mb-3", style={'fontWeight': 'bold', 'color': COLORS['text']}),
                dcc.Graph(id='grafico-he-indireto-qtd', style={'height': '400px'}, config={'displayModeBar': False})
            ], className="kpi-card p-4 mb-4"), width=12),
        ]),

        # Tarefas
        dbc.Row([
            dbc.Col(html.Div([
                html.Div([
                    html.H5("Top 15 Tarefas Mais Custosas (Curva ABC)", className="mb-0", style={'fontWeight': 'bold'}),
                    dcc.RadioItems(id='radio-tipo-tarefa', options=[{'label': ' Tudo', 'value': 'TODOS'}, {'label': ' Produção', 'value': 'Produção'}, {'label': ' Outros/Adm', 'value': 'Outros'}], value='TODOS', inputStyle={"marginRight": "5px", "marginLeft": "15px"}, style={'color': 'white'})
                ], className="d-flex justify-content-between align-items-center mb-3"),
                dcc.Graph(id='grafico-top-tarefas', style={'height': '450px'}, config={'displayModeBar': False})
            ], className="kpi-card p-4 mb-4"), width=12),
        ]),

        # Scatter
        dbc.Row([
            dbc.Col(html.Div([
                html.H5("Dispersão: Salário Fixo vs Produção (MO Direta)", className="mb-3", style={'fontWeight': 'bold'}),
                dcc.Graph(id='grafico-scatter', style={'height': '450px'}, config={'displayModeBar': False})
            ], className="kpi-card p-4 mb-4"), width=12),
        ]),

        # Rankings
        dbc.Row([
            dbc.Col(html.Div([
                html.H5("Ranking de Custo: MO DIRETA", className="mb-3", style={'fontWeight': 'bold', 'color': COLORS['azul']}),
                dcc.Graph(id='grafico-funcao-direto', style={'height': '450px'}, config={'displayModeBar': False})
            ], className="kpi-card p-4 mb-4"), width=12, lg=6),
            dbc.Col(html.Div([
                html.H5("Ranking de Custo: MO INDIRETA (Gestão)", className="mb-3", style={'fontWeight': 'bold', 'color': COLORS['roxo']}),
                dcc.Graph(id='grafico-funcao-indireto', style={'height': '450px'}, config={'displayModeBar': False})
            ], className="kpi-card p-4 mb-4"), width=12, lg=6),
        ]),

        # Tabela
        dbc.Row([
            dbc.Col(html.Div([
                dbc.Tabs([
                    dbc.Tab(label="🏆 Alta Performance", tab_id="tab-alta", label_style={"color": COLORS['success']}),
                    dbc.Tab(label="⚠️ Déficit", tab_id="tab-baixa", label_style={"color": COLORS['danger']}),
                    dbc.Tab(label="📋 Indiretos", tab_id="tab-indiretos", label_style={"color": COLORS['roxo']}),
                ], id="tabs-tabelas", active_tab="tab-alta", className="mb-3"),
                html.Div(id="conteudo-tabela")
            ], className="kpi-card p-4 mb-4"), width=12),
        ]),
    ], id="page-content", className="content")
    
    return html.Div([dcc.Store(id='side_click'), sidebar, content])

# APP LAYOUT PRINCIPAL (CONTROLADOR)
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='login-state', data={'logged_in': False}),
    html.Div(id='page-wrapper', children=login_layout) # Começa com Login
])

# =============================================================================
# 5. CALLBACKS DE LOGIN
# =============================================================================
@app.callback(
    [Output('page-wrapper', 'children'), Output('login-output', 'children')],
    [Input('login-button', 'n_clicks'), Input('logout-button', 'n_clicks')],
    [State('username-box', 'value'), State('password-box', 'value'), State('login-state', 'data')]
)
def manage_login(n_login, n_logout, username, password, state):
    ctx = dash.callback_context
    if not ctx.triggered:
        return login_layout, ""
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == 'logout-button':
        return login_layout, ""

    if button_id == 'login-button':
        if username in USUARIOS and USUARIOS[username] == password:
            return get_dashboard_layout(), ""
        else:
            return login_layout, "Usuário ou senha incorretos."

    return login_layout, ""


# =============================================================================
# 6. CALLBACKS DO DASHBOARD (LÓGICA ORIGINAL)
# =============================================================================
@app.callback(
    [Output("sidebar", "className"), Output("page-content", "className")],
    [Input("btn_sidebar", "n_clicks")],
    [State("sidebar", "className"), State("page-content", "className")]
)
def toggle_sidebar(n, s_class, c_class):
    if n: return ("sidebar", "content") if "sidebar-collapsed" in s_class else ("sidebar sidebar-collapsed", "content content-expanded")
    return s_class, c_class

@app.callback(
    [Output('kpi-custo-real', 'children'), Output('kpi-prod', 'children'),
     Output('kpi-efic', 'children'), Output('kpi-pct-bonificada', 'children'),
     Output('kpi-resultado', 'children'), Output('kpi-desperdicio', 'children'), 
     Output('grafico-balanco-roi', 'figure'),
     Output('grafico-obra-stack', 'figure'), Output('grafico-pie-mo', 'figure'),
     Output('grafico-he-obra', 'figure'), Output('grafico-he-funcao', 'figure'), Output('grafico-he-indireto-qtd', 'figure'),
     Output('grafico-top-tarefas', 'figure'),
     Output('grafico-scatter', 'figure'), 
     Output('grafico-funcao-direto', 'figure'), Output('grafico-funcao-indireto', 'figure'),
     Output('conteudo-tabela', 'children')],
    [Input('filtro-competencia', 'value'), Input('filtro-obra', 'value'),
     Input('tabs-tabelas', 'active_tab'), Input('radio-tipo-tarefa', 'value')]
)
def update_dash(comp, obra, tab, tipo_tarefa_filtro):
    if df_salarios.empty: return "R$ 0", "R$ 0", "", "0%", "", "R$ 0", {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, []

    df_s = df_salarios[df_salarios['Competencia'] == comp].copy()
    if obra != 'TODAS': df_s = df_s[df_s['Obra'] == obra]
    df_t = df_tarefas[df_tarefas['Competencia'] == comp].copy()
    if obra != 'TODAS': df_t = df_t[df_t['Obra'] == obra]

    # --- KPI: DIRETO ---
    df_direto_kpi = df_s[df_s['Tipo_MO'] == 'Direto'].copy()
    df_direto_kpi['Ganho_Real'] = df_direto_kpi['Valor das tarefas (R$)'] > df_direto_kpi['Salario Base (R$)']
    
    total_diretos = len(df_direto_kpi)
    total_bonificados = len(df_direto_kpi[df_direto_kpi['Ganho_Real'] == True])
    pct_bonificada = (total_bonificados / total_diretos * 100) if total_diretos > 0 else 0
    kpi_pct_bonif_fmt = f"{pct_bonificada:.1f}%"

    base_direto = df_direto_kpi['Salario Base (R$)'].sum()
    prod_direto = df_direto_kpi['Valor das tarefas (R$)'].sum()
    custo_direto = df_direto_kpi['Salário bruto - faltas (R$)'].sum()
    
    df_direto_kpi['Gap'] = df_direto_kpi['Valor das tarefas (R$)'] - df_direto_kpi['Salario Base (R$)']
    desperdicio = abs(df_direto_kpi[df_direto_kpi['Gap'] < 0]['Gap'].sum())
    custo_total_geral = df_s['Salário bruto - faltas (R$)'].sum()
    
    efic = (prod_direto / base_direto * 100) if base_direto > 0 else 0
    delta = efic - 100
    if delta < 0:
        kpi_efic_comp = html.Span([html.I(className="fa-solid fa-arrow-trend-down me-2"), f"{efic:.1f}% ", html.Span(f"({abs(delta):.1f}% Abaixo)", style={'fontSize': '0.65rem', 'opacity': '0.8'})], style={'color': COLORS['danger'], 'fontWeight': 'bold', 'fontSize': '1.1rem'})
    else:
        kpi_efic_comp = html.Span([html.I(className="fa-solid fa-arrow-trend-up me-2"), f"{efic:.1f}% ", html.Span("(Meta)", style={'fontSize': '0.65rem', 'opacity': '0.8'})], style={'color': COLORS['azul'], 'fontWeight': 'bold', 'fontSize': '1.1rem'})

    fmt = lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    resultado = prod_direto - custo_direto
    cor_res = COLORS['success'] if resultado >= 0 else COLORS['danger']
    icone_res = "fa-thumbs-up" if resultado >= 0 else "fa-thumbs-down"
    kpi_res_comp = html.H4([html.I(className=f"fa-solid {icone_res} me-2"), fmt(resultado)], style={'color': cor_res, 'fontWeight': 'bold', 'fontSize': '1.1rem'})

    # 0. ROI
    fig_roi = go.Figure()
    fig_roi.add_trace(go.Bar(x=['Investimento Previsto (Base)', 'Valor Produzido', 'Custo Real (Pago)'], y=[base_direto, prod_direto, custo_direto], text=[fmt(base_direto), fmt(prod_direto), fmt(custo_direto)], textposition='auto', marker_color=[COLORS['base_gray'], COLORS['azul'], COLORS['roxo']], hovertemplate='<b>%{x}</b><br>Valor: %{text}<extra></extra>'))
    fig_roi = update_layout_theme(fig_roi)
    fig_roi.update_layout(title="Balanço Financeiro (Apenas MO Direta)", margin=dict(t=40, b=30))

    # 1. Stacked
    df_stack = df_s.groupby(['Obra', 'Tipo_MO'])['Salário bruto - faltas (R$)'].sum().reset_index()
    if obra == 'TODAS':
        fig_stack = px.bar(df_stack, y='Obra', x='Salário bruto - faltas (R$)', color='Tipo_MO', orientation='h', color_discrete_map={'Direto': COLORS['azul'], 'Indireto': COLORS['roxo']})
    else:
        fig_stack = px.bar(df_stack, x='Tipo_MO', y='Salário bruto - faltas (R$)', color='Tipo_MO', color_discrete_map={'Direto': COLORS['azul'], 'Indireto': COLORS['roxo']})
    fig_stack = update_layout_theme(fig_stack)
    fig_stack.update_layout(legend_title=None, legend=dict(orientation="h", y=1.1))
    fig_stack.update_traces(hovertemplate='<b>%{y}</b><br>%{data.name}: R$ %{x:,.2f}<extra></extra>' if obra == 'TODAS' else '<b>%{x}</b><br>%{data.name}: R$ %{y:,.2f}<extra></extra>')

    # 2. Pizza
    custo_ind = df_s[df_s['Tipo_MO'] == 'Indireto']['Salário bruto - faltas (R$)'].sum()
    fig_pie = px.pie(names=['Direto', 'Indireto'], values=[custo_direto, custo_ind], hole=0.6, color_discrete_sequence=[COLORS['azul'], COLORS['roxo']])
    fig_pie = update_layout_theme(fig_pie)
    fig_pie.update_traces(textinfo='percent+label', hovertemplate='<b>%{label}</b><br>Total: R$ %{value:,.2f}<extra></extra>')

    # 3. HE
    df_he_obra = df_s.melt(id_vars='Obra', value_vars=['HE 50% (em tarefas)', 'HE 50% (fora tarefas)'], var_name='Tipo', value_name='Valor')
    df_he_obra = df_he_obra.groupby(['Obra', 'Tipo'])['Valor'].sum().reset_index()
    fig_he_obra = px.bar(df_he_obra, x='Obra', y='Valor', color='Tipo', barmode='group', color_discrete_map={'HE 50% (em tarefas)': COLORS['azul'], 'HE 50% (fora tarefas)': COLORS['roxo']})
    fig_he_obra = update_layout_theme(fig_he_obra)
    fig_he_obra.update_layout(legend=dict(orientation="h", y=1.1, title=None))
    fig_he_obra.update_traces(hovertemplate='<b>%{x}</b><br>%{data.name}: R$ %{y:,.2f}<extra></extra>')

    # 4. HE Função
    df_he_func = df_s.melt(id_vars='Função', value_vars=['HE 50% (em tarefas)', 'HE 50% (fora tarefas)'], var_name='Tipo', value_name='Valor')
    df_he_func = df_he_func.groupby(['Função', 'Tipo'])['Valor'].sum().reset_index()
    top_func = df_he_func.groupby('Função')['Valor'].sum().nlargest(10).index
    df_he_func = df_he_func[df_he_func['Função'].isin(top_func)]
    fig_he_func = px.bar(df_he_func, x='Valor', y='Função', color='Tipo', orientation='h', barmode='stack', color_discrete_map={'HE 50% (em tarefas)': COLORS['azul'], 'HE 50% (fora tarefas)': COLORS['roxo']})
    fig_he_func = update_layout_theme(fig_he_func)
    fig_he_func.update_layout(legend=dict(orientation="h", y=1.1, title=None))
    fig_he_func.update_traces(hovertemplate='<b>%{y}</b><br>%{data.name}: R$ %{x:,.2f}<extra></extra>')

    # 4.1. TOP Indiretos QTD HE (Cálculo Estimado)
    df_ind_he = df_s[df_s['Tipo_MO'] == 'Indireto'].copy()
    df_ind_he['Total_HE_Val'] = df_ind_he['HE 50% (em tarefas)'] + df_ind_he['HE 50% (fora tarefas)']
    # Reverse Engineering: Qtd = ValorPago / ( (Base/220)*1.5 )
    df_ind_he['Qtd_Horas'] = df_ind_he.apply(lambda x: x['Total_HE_Val'] / ((x['Salario Base (R$)']/220)*1.5) if x['Salario Base (R$)'] > 0 else 0, axis=1)
    df_top_ind_he = df_ind_he.sort_values('Qtd_Horas', ascending=False).head(10)
    
    if not df_top_ind_he.empty:
        fig_he_ind_qtd = px.bar(df_top_ind_he, x='Qtd_Horas', y='Nome', orientation='h', color='Qtd_Horas', color_continuous_scale=BLUE_NEON_SCALE)
        fig_he_ind_qtd = update_layout_theme(fig_he_ind_qtd)
        fig_he_ind_qtd.update_layout(yaxis=dict(autorange="reversed")) 
        fig_he_ind_qtd.update_traces(hovertemplate='<b>%{y}</b><br>Horas Extras: %{x:.1f}h<br>Valor: R$ %{customdata:.2f}<br>Salário Base: R$ %{text}<extra></extra>', customdata=df_top_ind_he['Total_HE_Val'], text=df_top_ind_he['Salario Base (R$)'].apply(fmt))
    else:
        fig_he_ind_qtd = go.Figure(); fig_he_ind_qtd = update_layout_theme(fig_he_ind_qtd)

    # 5. Top Tarefas
    if not df_t.empty:
        if tipo_tarefa_filtro == 'Produção': df_t_filt = df_t[df_t['Tipo'] == 'Produção']
        elif tipo_tarefa_filtro == 'Outros': df_t_filt = df_t[df_t['Tipo'] != 'Produção']
        else: df_t_filt = df_t.copy()
        df_serv = df_t_filt.groupby('Descricao_Servico')['Valor_Tarefa'].sum().reset_index()
        df_serv = df_serv.sort_values('Valor_Tarefa', ascending=False).head(15)
        fig_tar = px.bar(df_serv, x='Valor_Tarefa', y='Descricao_Servico', orientation='h', color='Valor_Tarefa', color_continuous_scale=BLUE_NEON_SCALE)
        fig_tar = update_layout_theme(fig_tar)
        fig_tar.update_layout(yaxis=dict(autorange="reversed"))
        fig_tar.update_traces(hovertemplate='<b>%{y}</b><br>Total: R$ %{x:,.2f}<extra></extra>')
    else:
        fig_tar = go.Figure(); fig_tar = update_layout_theme(fig_tar)

    # 6. Scatter
    df_direto_kpi['Status'] = df_direto_kpi['Gap'].apply(lambda x: 'Alta' if x > 0 else 'Baixa')
    fig_sc = px.scatter(df_direto_kpi, x='Salario Base (R$)', y='Valor das tarefas (R$)', color='Status', hover_data=['Nome', 'Função'], color_discrete_map={'Alta': COLORS['azul'], 'Baixa': COLORS['roxo']})
    max_val = df_direto_kpi['Salario Base (R$)'].max() if not df_direto_kpi.empty else 1000
    fig_sc.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val, line=dict(color="white", dash="dash"))
    fig_sc = update_layout_theme(fig_sc)
    fig_sc.update_traces(hovertemplate='<b>%{customdata[0]}</b><br>%{customdata[1]}<br>Base: R$ %{x:,.2f} | Prod: R$ %{y:,.2f}<extra></extra>')

    # 7. Rankings
    df_f_dir = df_s[df_s['Tipo_MO'] == 'Direto'].groupby('Função')['Salário bruto - faltas (R$)'].sum().reset_index()
    top_f_dir = df_f_dir.sort_values('Salário bruto - faltas (R$)', ascending=False).head(15)
    fig_fun_dir = px.bar(top_f_dir, x='Salário bruto - faltas (R$)', y='Função', orientation='h', color_discrete_sequence=[COLORS['azul']])
    fig_fun_dir = update_layout_theme(fig_fun_dir)
    fig_fun_dir.update_layout(yaxis=dict(autorange="reversed"))
    fig_fun_dir.update_traces(hovertemplate='<b>%{y}</b><br>Pago: R$ %{x:,.2f}<extra></extra>')

    df_f_ind = df_s[df_s['Tipo_MO'] == 'Indireto'].groupby('Função')['Salário bruto - faltas (R$)'].sum().reset_index()
    top_f_ind = df_f_ind.sort_values('Salário bruto - faltas (R$)', ascending=False).head(15)
    fig_fun_ind = px.bar(top_f_ind, x='Salário bruto - faltas (R$)', y='Função', orientation='h', color_discrete_sequence=[COLORS['roxo']])
    fig_fun_ind = update_layout_theme(fig_fun_ind)
    fig_fun_ind.update_layout(yaxis=dict(autorange="reversed"))
    fig_fun_ind.update_traces(hovertemplate='<b>%{y}</b><br>Pago: R$ %{x:,.2f}<extra></extra>')

    # Tabela
    df_s['Total_HE_Val'] = df_s['HE 50% (em tarefas)'] + df_s['HE 50% (fora tarefas)']
    df_s['Qtd_HE_Calc'] = df_s.apply(lambda x: x['Total_HE_Val'] / ((x['Salario Base (R$)']/220)*1.5) if x['Salario Base (R$)'] > 0 else 0, axis=1)

    cols = [
        {"name": "Nome", "id": "Nome"}, {"name": "Função", "id": "Função"}, {"name": "Tipo", "id": "Tipo_MO"},
        {"name": "Salario Base", "id": "Salario Base (R$)", "type": "numeric", "format": money_fmt},
        {"name": "Produção", "id": "Valor das tarefas (R$)", "type": "numeric", "format": money_fmt},
        {"name": "Valor HE", "id": "Total_HE_Val", "type": "numeric", "format": money_fmt},
        {"name": "Qtd HE (h)", "id": "Qtd_HE_Calc", "type": "numeric", "format": hour_fmt}, # NOVA COLUNA
        {"name": "Prêmios", "id": "Valor total de prêmios (R$)", "type": "numeric", "format": money_fmt},
        {"name": "Custo Real", "id": "Salário bruto - faltas (R$)", "type": "numeric", "format": money_fmt},
        {"name": "Justificativa", "id": "Justificativa"}
    ]

    if tab == "tab-alta":
        df_tab = df_s[df_s['Tipo_MO'] == 'Direto'].copy()
        df_tab['Gap'] = df_tab['Valor das tarefas (R$)'] - df_tab['Salario Base (R$)']
        df_tab = df_tab[df_tab['Gap'] > 0].sort_values('Gap', ascending=False)
        head_color = COLORS['success']
    elif tab == "tab-baixa":
        df_tab = df_s[df_s['Tipo_MO'] == 'Direto'].copy()
        df_tab['Gap'] = df_tab['Valor das tarefas (R$)'] - df_tab['Salario Base (R$)']
        df_tab = df_tab[df_tab['Gap'] < 0].sort_values('Gap', ascending=True)
        head_color = COLORS['danger']
    else:
        df_tab = df_s[df_s['Tipo_MO'] == 'Indireto'].sort_values('Salário bruto - faltas (R$)', ascending=False)
        head_color = COLORS['roxo']

    tabela = dash_table.DataTable(
        data=df_tab.head(200).to_dict('records'), columns=cols,
        page_size=15, sort_action='native', style_as_list_view=True,
        style_header={'backgroundColor': '#0f172a', 'color': head_color, 'fontWeight': 'bold', 'borderBottom': '2px solid #334155'},
        style_cell={'backgroundColor': 'transparent', 'color': '#cbd5e1', 'borderBottom': '1px solid #334155', 'textAlign': 'left', 'padding': '12px'},
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgba(255, 255, 255, 0.02)'}]
    )

    return fmt(custo_total_geral), fmt(prod_direto), kpi_efic_comp, kpi_pct_bonif_fmt, kpi_res_comp, fmt(desperdicio), fig_roi, fig_stack, fig_pie, fig_he_obra, fig_he_func, fig_he_ind_qtd, fig_tar, fig_sc, fig_fun_dir, fig_fun_ind, tabela

if __name__ == '__main__':
    app.run(debug=True)