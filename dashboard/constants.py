# -*- coding: utf-8 -*-
"""
dashboard/constants.py — Constantes compartilhadas do dashboard.

Contém os grupos de contas CVM (STANDARD_NAME) e o mapa de tickers B3.
"""

# ── Grupos de contas CVM (STANDARD_NAME) ──────────────────────────────────────
RECEITA   = ['Receita de Venda de Bens e/ou Serviços', 'Receitas das Operações',
             'Receitas de Intermediação Financeira']
LUCRO     = ['Lucro/Prejuízo Consolidado do Período',
             'Resultado Líquido das Operações Continuadas']
RES_BRUT  = ['Resultado Bruto']
CUSTO     = ['Custo dos Bens e/ou Serviços Vendidos']
DESP_OP   = ['Despesas/Receitas Operacionais']
AT_CIRC   = ['Ativo Circulante']
AT_NCIRC  = ['Ativo Não Circulante']
CAIXA     = ['Caixa e Equivalentes de Caixa']
PL        = ['Patrimônio Líquido Consolidado']
PASS_C    = ['Passivo Circulante']
PASS_NC   = ['Passivo Não Circulante']
DIVIDA    = ['Empréstimos e Financiamentos', 'Debêntures']
FCO       = ['Caixa Líquido Atividades Operacionais']
FCI       = ['Caixa Líquido Atividades de Investimento']
FCF_ACTIV = ['Caixa Líquido Atividades de Financiamento']

# ── Mapa CVM → Ticker B3 (Yahoo Finance) ─────────────────────────────────────
TICKER_MAP: dict[int, str] = {
    9512:  'PETR4.SA',   # PETROBRAS
    4170:  'VALE3.SA',   # VALE
    19348: 'ITUB4.SA',   # ITAÚ UNIBANCO
    906:   'BBDC4.SA',   # BANCO BRADESCO
    1023:  'BBAS3.SA',   # BANCO DO BRASIL
    23264: 'ABEV3.SA',   # AMBEV
    5410:  'WEGE3.SA',   # WEG
    20087: 'EMBR3.SA',   # EMBRAER
    21610: 'B3SA3.SA',   # B3
    3980:  'GGBR4.SA',   # GERDAU
    24783: 'NTCO3.SA',   # NATURA
    24813: 'RENT3.SA',   # LOCALIZA
    13986: 'SUZB3.SA',   # SUZANO PAPEL
    8133:  'LREN3.SA',   # RENNER
    19992: 'TOTS3.SA',   # TOTVS
    2437:  'ELET3.SA',   # ELETROBRAS
    17671: 'VIVT3.SA',   # TELEFÔNICA BRASIL
    21431: 'HYPE3.SA',   # HYPERA PHARMA
    12653: 'KLBN11.SA',  # KLABIN
    20788: 'MRFG3.SA',   # MARFRIG
    20575: 'JBSS3.SA',   # JBS
    22470: 'MGLU3.SA',   # MAGAZINE LUIZA
    24392: 'HAPV3.SA',   # HAPVIDA
    24821: 'RDOR3.SA',   # REDE D'OR
    20532: 'SANB11.SA',  # BANCO SANTANDER BRASIL
    5258:  'RADL3.SA',   # DROGASIL
    14443: 'SBSP3.SA',   # SABESP
    21199: 'BPAN4.SA',   # BANCO PAN
    19836: 'CSAN3.SA',   # COSAN
    18660: 'CPFE3.SA',   # CPFL ENERGIA
    25585: 'CMIN3.SA',   # CSN MINERAÇÃO
    14460: 'CYRE3.SA',   # CYRELA
    21016: 'YDUQ3.SA',   # ESTÁCIO (YDUQS)
    21881: 'FLRY3.SA',   # FLEURY
    25186: 'GMAT3.SA',   # GRUPO MATEUS
    24180: 'IRBR3.SA',   # IRB BRASIL RESSEGUROS
    17973: 'COGN3.SA',   # KROTON (COGNA)
    8451:  'POMO4.SA',   # MARCOPOLO
    20931: 'BEEF3.SA',   # MINERVA
    20915: 'MRVE3.SA',   # MRV ENGENHARIA
    20982: 'MULT3.SA',   # MULTIPLAN
    22187: 'PRIO3.SA',   # PETRO RIO
    14109: 'RAPT4.SA',   # RANDON
    20745: 'SLCE3.SA',   # SLC AGRÍCOLA
    20516: 'SMTO3.SA',   # SÃO MARTINHO
    17329: 'EGIE3.SA',   # ENGIE BRASIL (ex-Tractebel — ticker atualizado)
    14320: 'USIM5.SA',   # USIMINAS
    24805: 'VIVA3.SA',   # VIVARA
    21490: 'ALUP11.SA',  # ALUPAR
    22357: 'ALOS3.SA',   # ALLOS (ex-BR Malls / Aliansce Sonae)
    10456: 'ALPA4.SA',   # ALPARGATAS
    22616: 'BPAC11.SA',  # BTG PACTUAL
    25291: 'BRAV3.SA',   # BRAVA ENERGIA (ex-3R Petroleum)
    25283: 'AERI3.SA',   # AERIS
    21032: 'ALGT3.SA',   # ALGAR TELECOM
    17450: 'RAIL3.SA',   # RUMO LOGÍSTICA (ex-ALL)
    24058: 'ALLY3.SA',   # ALLIANÇA SAÚDE
    22217: 'ALPER3.SA',  # ALPER CONSULTORIA
    # ── Adicionados ───────────────────────────────────────────────────────────
     2453: 'CMIG4.SA',   # CEMIG
     1431: 'CPLE6.SA',   # COPEL
     7617: 'ITSA4.SA',   # ITAÚSA
    22152: 'BBSE3.SA',   # BB SEGURIDADE
    20281: 'BRFS3.SA',   # BRF
    21369: 'EQTL3.SA',   # EQUATORIAL ENERGIA
    24767: 'AZUL4.SA',   # AZUL LINHAS AÉREAS
    19615: 'CCRO3.SA',   # CCR
     3697: 'ENBR3.SA',   # EDP BRASIL
    20303: 'VBBR3.SA',   # VIBRA ENERGIA (ex-BR Distribuidora)
    18112: 'IGTI11.SA',  # IGUATEMI
    24010: 'INTB3.SA',   # INTELBRAS
    21229: 'GOLL4.SA',   # GOL LINHAS AÉREAS
    23450: 'RECV3.SA',   # PETRORECÔNCAVO
    16284: 'TUPY3.SA',   # TUPY
    19283: 'FRAS3.SA',   # FRAS-LE
    16160: 'AGRO3.SA',   # BRASILAGRO
    24554: 'ARZZ3.SA',   # AREZZO
    22063: 'SOMA3.SA',   # GRUPO SOMA
}

# ── Mapa reverso: Ticker → CD_CVM (para busca por ticker na sidebar) ──────────
REVERSE_TICKER_MAP: dict[str, int] = {
    v.replace('.SA', '').upper(): k for k, v in TICKER_MAP.items()
}
