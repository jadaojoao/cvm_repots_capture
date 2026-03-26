import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

def render_kpi_cards(company_kpis, target_year):
    """
    Espera receber o dataframe filtrado da base analítica para a empresa ativa.
    Se extrai ROE, ROA, Margem Bruta, etc. do alvo (target_year) vs anterior.
    """
    col_curr = f'VALUE_{target_year}'
    col_prev = f'VALUE_{target_year - 1}'
    
    # Se a base de dados não tem a coluna atual
    if col_curr not in company_kpis.columns:
        st.warning(f"Sem dados carregados para {target_year}")
        return
        
    def get_val(kpi_id):
        row = company_kpis[company_kpis['kpi_id'] == kpi_id]
        if row.empty: return None, None
        
        curr = row.iloc[0].get(col_curr, None)
        prev = row.iloc[0].get(col_prev, None) if col_prev in row.columns else None
        
        # Parse to float if possible
        try: curr = float(curr) if pd.notna(curr) else None
        except: curr = None
        
        try: prev = float(prev) if pd.notna(prev) else None
        except: prev = None
        
        return curr, prev

    # Lista de KPIs prioritários financeiros mapeados:
    # UNI_001 = Crescimento Receita, UNI_002 = Margem Bruta
    # UNI_005 = ROA, UNI_006 = ROE
    kpis_to_show = [
        ('UNI_001', 'Crescimento Rec.', '%'),
        ('UNI_002', 'Margem Bruta', '%'),
        ('UNI_006', 'ROE', '%'),
        ('UNI_005', 'ROA', '%'),
        ('UNI_011', 'Margem Líquida', '%')
    ]
    
    st.markdown("### Métricas Operacionais e Retorno")
    cols = st.columns(len(kpis_to_show))
    
    for i, (k_id, k_name, k_unit) in enumerate(kpis_to_show):
        curr, prev = get_val(k_id)
        
        val_str = "N/D"
        delta_str = None
        
        if curr is not None:
            val_str = f"{curr*100:.1f}{k_unit}"
            if prev is not None and prev != 0:
                # Delta points difference
                delta = (curr - prev) * 100
                delta_str = f"{delta:+.1f} ppt"
        
        cols[i].metric(label=k_name, value=val_str, delta=delta_str)

def render_historical_chart(company_kpis, kpi_id, title):
    """Plot simple bar or line chart indicating the history of a chosen metric"""
    row = company_kpis[company_kpis['kpi_id'] == kpi_id]
    if row.empty: return
    
    # Extrair os anos 2023, 2024, 2025
    years = []
    vals = []
    for y in [2023, 2024, 2025]:
        col = f'VALUE_{y}'
        if col in row.columns:
            val = row.iloc[0][col]
            if pd.notna(val):
                try:
                    vals.append(float(val)*100)
                    years.append(str(y))
                except:
                    pass
    
    if not vals:
        return
        
    df_plot = pd.DataFrame({'Ano': years, 'Valor (%)': vals})
    
    fig = px.bar(df_plot, x='Ano', y='Valor (%)', text='Valor (%)',
                 title=title, template='plotly_white')
                 
    fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside', marker_color='#00BF7A')
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=50, b=20),
        height=300,
        yaxis=dict(showgrid=True, gridcolor='#e2e8f0', zeroline=True, zerolinecolor='#cbd5e1')
    )
    st.plotly_chart(fig, use_container_width=True)

def render_financial_statements_grid(raw_df):
    """Mostra um pivot elegante dos dados brutos com st.dataframe"""
    if raw_df.empty: return
    
    st.markdown("### Composição do Balanço/DRE (Dados Brutos)")
    
    # Filtra apenas algumas contas essenciais para não explodir a tela
    key_accounts = [
        'Ativo Total', 'Patrimônio Líquido', 'Caixa e Equivalentes de Caixa',
        'Receita de Venda de Bens e/ou Serviços', 'Resultado Bruto',
        'Lucro/Prejuízo Consolidado do Período'
    ]
    df_filtered = raw_df[raw_df['STANDARD_NAME'].isin(key_accounts)].copy()
    
    if df_filtered.empty:
        df_filtered = raw_df.copy() # fallback show all
        
    # Pivot
    pivot = df_filtered.pivot_table(
        index=['STATEMENT_TYPE', 'STANDARD_NAME'],
        columns='REPORT_YEAR',
        values='VL_CONTA',
        aggfunc='sum'
    ).fillna(0)
    
    # Formatação de contabilidade Brasileira (Bilhões/Milhões)
    st.dataframe(
        pivot.style.format("{:,.0f}"),
        use_container_width=True,
        height=300
    )

def render_quarterly_chart(raw_df):
    """Gera um gráfico histórico sequencial baseado nos trimestres da DRE"""
    if raw_df.empty: return
    
    st.markdown("### Histórico Sazonal (Contas Trimestrais Isoladas)")
    
    # Filtra apenas DRE e os períodos isolados
    dre = raw_df[(raw_df['STATEMENT_TYPE'] == 'DRE') & (raw_df['PERIOD_LABEL'].isin(['1Q', '2Q', '3Q', '4Q']))].copy()
    if dre.empty:
        st.info("Não há dados trimestrais (1Q-4Q) registrados individualmente para gerar sazonalidade.")
        return
        
    metricas_validas = [
        'Receita de Venda de Bens e/ou Serviços', 
        'Receitas das Operações',
        'Receitas de Intermediação Financeira',
        'Lucro/Prejuízo Consolidado do Período',
        'Lucro/Prejuízo Líquido',
        'Resultado Bruto'
    ]
    
    dre = dre[dre['STANDARD_NAME'].isin(metricas_validas)]
    if dre.empty: return
    
    # Unificar Receitas sob o mesmo nome para plot
    dre['STANDARD_NAME'] = dre['STANDARD_NAME'].replace({
        'Receitas das Operações': 'Receita Líquida',
        'Receitas de Intermediação Financeira': 'Receita Líquida',
        'Receita de Venda de Bens e/ou Serviços': 'Receita Líquida',
        'Lucro/Prejuízo Consolidado do Período': 'Lucro Líquido',
        'Lucro/Prejuízo Líquido': 'Lucro Líquido'
    })
    
    # Eixo X cronológico (Ex: 2023 - 1Q)
    dre['Timeline'] = dre['REPORT_YEAR'].astype(str) + " - " + dre['PERIOD_LABEL']
    dre = dre.sort_values(by=['REPORT_YEAR', 'PERIOD_LABEL'])
    
    metricas_disp = dre['STANDARD_NAME'].unique().tolist()
    if not metricas_disp: return
    
    sel_metric = st.selectbox("Conta Contábil Trimestral", metricas_disp, index=0)
    plot_df = dre[dre['STANDARD_NAME'] == sel_metric]
    
    fig = px.bar(plot_df, x='Timeline', y='VL_CONTA', text='VL_CONTA',
                 title=f'{sel_metric} por Trimestre (R$ Milhares)', 
                 template='plotly_white')
                 
    fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside', marker_color='#1e293b')
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=50, b=20),
        height=350,
        yaxis=dict(showgrid=True, gridcolor='#e2e8f0', zeroline=True, zerolinecolor='#cbd5e1')
    )
    st.plotly_chart(fig, use_container_width=True)

