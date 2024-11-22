import pandas as pd
import geopandas as gpd
import plotly.express as px
import dash
from  dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import numpy as np
#pd.set_option('future.no_silent_downcasting', True)

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LUMEN, dbc.icons.FONT_AWESOME],requests_pathname_prefix='/cobertura_vacinal/')
server = app.server

cabecalho = html.H1("Coberturas Vacinais", className="bg-primary text-white p-2 mb-4")
arquivo = '/var/www/aplicacoes/dash-cobertura-vacinal/data/coberturas_2023.xlsx'
ano = arquivo[-9:-5]
coberturas = pd.read_excel(arquivo)
coberturas.reset_index(inplace=True)

for coluna in ['Região Ocorrência', 'UF Residência', 'Macrorregião Saúde', 'Região de Saúde', 'Município Residência']:
    coberturas.drop(coberturas.loc[coberturas[coluna]=='Totais'].index, axis=0, inplace=True)

coberturas.replace({'-': -9999}, inplace=True)
coberturas['Código IBGE 6'] = coberturas['Município Residência'].apply(lambda x: x.split('-')[0].strip())
coberturas['Nome município'] = coberturas['Município Residência'].apply(lambda x: x.split('-')[1].strip())
coberturas.drop(['index',
                 ' ',
                 'Região Ocorrência',
                 'Macrorregião Saúde',
                 'Região de Saúde',
                 'Município Residência',
                 'Imunobiológico'],
                axis=1,
                inplace=True)

municipios = gpd.read_file('/var/www/aplicacoes/dash-cobertura-vacinal/data/BR_Municipios_2022/BR_Municipios_2022_simp.shp', encoding='utf-8')
municipios['CD_MUN_6'] = municipios['CD_MUN'].apply(lambda x: x[0:6])
municipios_cobertura = municipios.merge(coberturas, how='left', left_on='CD_MUN_6', right_on='Código IBGE 6')
municipios_cobertura.drop(['AREA_KM2', 'CD_MUN_6', 'UF Residência', 'Código IBGE 6', 'Nome município'], axis=1, inplace=True)

imunogenos =  ['BCG',
               'DTP',
               'DTP (1° Reforço)',
               'dTpa Adulto',
               'Febre Amarela',
               'Hepatite A Infantil',
               'Hepatite B',
               'Hepatite B (< 30 Dias)',
               'Meningo C',
               'Meningo C (1° Reforço)',
               'Penta (DTP/HepB/Hib)',
               'Pneumo 10',
               'Pneumo 10 (1° Reforço)',
               'Polio Injetável (VIP)',
               'Polio Oral Bivalente',
               'Rotavírus',
               'Tríplice Viral - 1° Dose',
               'Tríplice Viral - 2° Dose',
               'Varicela']

for imunogeno in imunogenos:
    municipios_cobertura[imunogeno] = municipios_cobertura[imunogeno].astype(float)

municipios_cobertura.replace({-9999: None}, inplace=True)

fig = px.choropleth(municipios_cobertura,
                            geojson=municipios_cobertura.__geo_interface__,
                            locations="CD_MUN",
                            featureidkey="properties.CD_MUN",
                            hover_name=municipios_cobertura["NM_MUN"],
                            hover_data={"SIGLA_UF": True,  "CD_MUN": False},
                            )
fig.update_layout(map_style="white-bg")
fig.update_geos(fitbounds="locations", visible=False)
fig.update_traces(marker_line=dict(width=.5, color='#a1a1a1'))
fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})

@app.callback([Output('cobertura', 'figure'),
               ],[
              Input('imunogeno', 'value'),
              Input('uf', 'value'),
              Input('municipio_uf', 'value'),
              ])
def gera_mapa(imunogeno, uf, municipio_uf):
    global ano, municipios_cobertura
    if not imunogeno:
        fig = px.choropleth(municipios_cobertura,
                            geojson=municipios_cobertura.__geo_interface__,
                            locations="CD_MUN",
                            featureidkey="properties.CD_MUN",
                            hover_name=municipios_cobertura["NM_MUN"],
                            hover_data={"SIGLA_UF": True,  "CD_MUN": False},
                            )
        fig.update_layout(map_style="white-bg")
        fig.update_geos(fitbounds="locations", visible=False)
        fig.update_traces(marker_line=dict(width=.5, color='#a1a1a1'))
        fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
        return fig
    else:
        bins = [-np.inf, .79999, 0.89999, 0.94999, 1, +np.inf]
        municipios_mapa = municipios_cobertura.copy()
        municipios_mapa['categorias'] = None
        municipios_mapa['categorias'] = pd.cut(municipios_mapa[imunogeno],
                                               bins,
                                               labels=['< 80.0','80.0 a 89.9', '90.0 a 94.9', '95.0 a 100.0', '> 100.0']
                                               ).values.add_categories('Sem informação')
        municipios_mapa['categorias'].fillna('Sem informação')
        municipios_mapa['cores'] = municipios_mapa['categorias'].map({'< 80.0': '#e70304',
                                                                      '> 100.0': '#4e27e6',
                                                                      '90.0 a 94.9': '#eee907',
                                                                      '80.0 a 89.9': '#fe941e',
                                                                      '95.0 a 100.0': '#15a222',
                                                                      np.str_('Sem informação'): '#ffffff'})


        if municipio_uf:
            municipios_mapa = municipios_mapa.loc[(municipios_mapa['SIGLA_UF'] == uf) &
                                                  (municipios_mapa['NM_MUN'] == municipio_uf), :]
        elif uf:
            municipios_mapa = municipios_mapa.loc[municipios_mapa['SIGLA_UF']==uf,:]
        else:
            pass

        fig = px.choropleth(municipios_mapa,
                            geojson=municipios_mapa.__geo_interface__,
                            locations="CD_MUN",
                            featureidkey="properties.CD_MUN",
                            color='categorias',
                            color_discrete_sequence=["#e70304", "#fe941e", "#eee907", "#15a222", "#4e27e6", "#ffffff"],
                            hover_name=municipios_mapa["NM_MUN"],
                            hover_data={"SIGLA_UF": True, imunogeno: ":.3f", "categorias": False, "CD_MUN": False},
                            category_orders={
                                "categorias": ['< 80.0', '80.0 a 89.9', '90.0 a 94.9', '95.0 a 100.0', '> 100.0',
                                               'Sem informação']}
                            )
        fig.update_layout(map_style="white-bg")
        fig.update_geos(fitbounds="locations", visible=False)
        fig.update_layout(legend_title_text='Coberturas vacinais')
        fig.update_traces(marker_line=dict(width=.5, color='#a1a1a1'))
        fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
        return [fig]

seletor_imunogeno = html.Div([
    dbc.Label('Imunógeno', html_for="imunogeno"),
    dcc.Dropdown(id='imunogeno',
                 options=[{'label': imun, 'value': imun}
                          for imun in sorted(imunogenos)],
                 placeholder="Selecione o imunógeno", disabled=False)
], className='card-text'),

seletor_uf = html.Div([
    dbc.Label('Unidade Federativa', html_for="uf"),
    dcc.Dropdown(id='uf',
                 options=[{'label': uf, 'value': uf}
                          for uf in sorted(municipios['SIGLA_UF'].unique())],
                 placeholder="Selecione a unidade federativa", disabled=False)
], className='card-text'),


seletor_municipio = html.Div([
    dbc.Label('Município', html_for="municipio"),
    dcc.Dropdown(id='municipio_uf',
                 options=[{'label': mun, 'value': mun}
                          for mun in sorted(municipios['NM_MUN'])],
                 placeholder="Selecione o município", disabled=False)
], className='card-text'),

@app.callback(Output('municipio_uf', 'options'),
              [Input('uf', 'value'),
               ])
def atualiza_municipios(uf):
    options = [{'label': mun, 'value': mun}
               for mun in
               sorted(municipios.loc[(municipios['SIGLA_UF'] == uf ),'NM_MUN'])]
    return options

app.layout = dbc.Container([
                cabecalho,
                html.Div([
                    html.P("Selecione:", className="card-header border-dark mb-2"),
                    dbc.Container([
                        dbc.Row(
                            [dbc.Col(seletor_imunogeno, width=4),
                            dbc.Col(seletor_uf, width=4),
                            dbc.Col(seletor_municipio, width=4)
                            ], className="border-dark mb-2"),
                        ])
                    ], id='cabecalho_filtro', className="card border-dark mb-2"),

                html.Div([
                    dbc.Container([
                        dbc.Row([
                            html.P("Mapa", className="card-header border-dark mb-2"),
                            ]),
                        dbc.Row([
                            dbc.Col(dcc.Graph(id='cobertura', figure=fig), width=12),
                            ]),
                        ], fluid=True),
                    ], id='mapa_container', className="card border-dark mb-2"),
    ])


if __name__ == '__main__':
    app.run(debug=True)
