###############################################################
#     TABLERO COMPLETO – EDUCACIÓN COLOMBIA (2016)
#     Versión final corregida, sin errores
###############################################################

import pandas as pd
import numpy as np
import geopandas as gpd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
import gdown

###############################################################
# 1. CARGA DE DATOS
###############################################################
url = "https://drive.google.com/uc?id=1u14rZaVygDiB45FCN7hSO2km1LyOunbT"
output = "panel.dta"

gdown.download(url, output, quiet=False)

df = pd.read_stata(output)
df = df[df["ano"] == 2016].copy()

# Normalizar código municipal
df["codmpio"] = df["codmpio"].astype(int)

# Variables derivadas
df["prop_total"] = df["docen_total"] / df["alumn_total"]
df["prop_rural"] = df["docen_rural"] / df["alumn_rural"]
df["prop_urbano"] = df["docen_urbano"] / df["alumn_urbano"]
df["disp_cat"] = pd.qcut(df["prop_total"], 3, labels=["Baja", "Media", "Alta"])

# Crear código departamento (primeros 2 dígitos)
df["depto"] = df["codmpio"].astype(str).str.zfill(5).str[0:2].astype(int)

###############################################################
# 2. GEOJSON MUNICIPIOS
###############################################################

geo_mun = gpd.read_file(
    "https://raw.githubusercontent.com/finiterank/mapa-colombia-js/master/colombia-municipios.json",
    layer="mpios"
)

# Normalizar ID
geo_mun["id"] = geo_mun["id"].astype(int)

# MERGE MUNICIPAL
gdf_mun = geo_mun.merge(df, left_on="id", right_on="codmpio", how="left")

###############################################################
# 3. GEOJSON DEPARTAMENTOS (FUNCIONA)
###############################################################

geo_dep = gpd.read_file(
    "https://gist.githubusercontent.com/john-guerra/43c7656821069d00dcbc/raw/3aadedf47badbdac823b00dbe259f6bc6d9e1899/colombia.geo.json"
)

# Normalizar código departamento
geo_dep["DPTO"] = geo_dep["DPTO"].astype(int)

# Agregar datos departamentales
dep = df.groupby("depto").agg({
    "s11_total": "mean",
    "prop_total": "mean",
    "prop_rural": "mean",
    "prop_urbano": "mean"
}).reset_index()

gdf_dep = geo_dep.merge(dep, left_on="DPTO", right_on="depto", how="left")

###############################################################
# 4. DASH APP – ORGANIZADO Y DISEÑO MEJORADO
###############################################################

app = Dash(__name__)
app.title = "Educación Colombia"

# ---- Estilos generales ----
STYLE_CARD = {
    "padding": "15px",
    "margin": "10px",
    "border-radius": "8px",
    "background-color": "#f7f7f7",
    "box-shadow": "0 2px 4px rgba(0,0,0,0.1)",
    "text-align": "center"
}

###############################################################
# 5. LAYOUT MEJORADO
###############################################################

app.layout = html.Div(style={"padding": "20px"}, children=[

    # -------------------------------------------------------
    # TÍTULO GENERAL
    # -------------------------------------------------------
    html.H1("Tablero Interactivo – Educación en Colombia (2016)",
            style={"text-align": "center", "margin-bottom": "20px"}),

    html.P(
        "Explora indicadores educativos por municipio y departamento: "
        "disponibilidad docente, puntajes Saber 11 y brechas territoriales.",
        style={"text-align": "center", "color": "gray", "margin-bottom": "40px"}
    ),

    # -------------------------------------------------------
    # FILA DE TARJETAS KPI
    # -------------------------------------------------------
    html.Div(style={"display": "flex", "justify-content": "center"}, children=[
        html.Div(style=STYLE_CARD, children=[
            html.H3("Promedio nacional Saber 11"),
            html.H2(f"{df['s11_total'].mean():.1f}")
        ]),
        html.Div(style=STYLE_CARD, children=[
            html.H3("Máxima disponibilidad docente"),
            html.H2(f"{df['prop_total'].max():.3f}")
        ]),
        html.Div(style=STYLE_CARD, children=[
            html.H3("Mínimo puntaje Saber 11"),
            html.H2(f"{df['s11_total'].min():.1f}")
        ]),
    ]),

    html.Hr(),

    # -------------------------------------------------------
    # SECCIÓN MAPA PRINCIPAL
    # -------------------------------------------------------
    html.Div([
        html.Label("Selecciona tipo de mapa:", style={"font-weight": "bold"}),

        dcc.Dropdown(
            id="map_selector",
            options=[
                {"label": "Municipios – Disponibilidad", "value": "mun_disp"},
                {"label": "Municipios – Puntaje Saber 11", "value": "mun_punt"},
                {"label": "Departamentos – Puntaje Saber 11", "value": "dep_punt"},
                {"label": "Departamentos – Disponibilidad", "value": "dep_disp"},
            ],
            value="mun_disp",
            style={"width": "40%", "margin-bottom": "20px"}
        ),

        dcc.Graph(id="mapa_principal")
    ], style={"margin-bottom": "50px"}),

    html.H2("Análisis Complementario", style={"text-align": "center"}),

    dcc.Dropdown(
        id="zona_selector",
        options=[
            {"label": "Todas las zonas", "value": "all"},
            {"label": "Rural", "value": "rural"},
            {"label": "Urbana", "value": "urbano"},
        ],
        value="all",
        style={"width": "40%", "margin": "20px auto"}
    ),

    # -------------------------------------------------------
    # FILA DE GRÁFICOS (2 columnas + 1 abajo)
    # -------------------------------------------------------
    html.Div(style={"display": "flex", "gap": "20px"}, children=[
        html.Div(style={"flex": 1}, children=[
            dcc.Graph(id="scatter_relacion")
        ]),
        html.Div(style={"flex": 1}, children=[
            dcc.Graph(id="barras_disp")
        ])
    ]),

    html.Div(style={"margin-top": "30px"}, children=[
        dcc.Graph(id="brecha_rural_urbana")
    ]),

])

###############################################################
# 6. CALLBACKS – MAPA PRINCIPAL
###############################################################

@app.callback(
    Output("mapa_principal", "figure"),
    Input("map_selector", "value")
)
def actualizar_mapa(tipo):

    if tipo == "mun_disp":
        fig = px.choropleth(
            gdf_mun,
            geojson=gdf_mun.__geo_interface__,
            locations=gdf_mun.index,
            color="prop_total",
            hover_name="name",
            color_continuous_scale="YlGnBu",
            title="Disponibilidad docente por municipio"
        )

    elif tipo == "mun_punt":

        fig = px.choropleth(
            gdf_mun,
            geojson=gdf_mun.__geo_interface__,
            locations=gdf_mun.index,
            color="s11_total",
            hover_name="name",
            color_continuous_scale="OrRd",
            title="Puntaje Saber 11 por municipio"
        )

    elif tipo == "dep_punt":

        fig = px.choropleth(
            gdf_dep,
            geojson=gdf_dep.__geo_interface__,
            locations=gdf_dep.index,
            color="s11_total",
            hover_name="NOMBRE_DPT",
            color_continuous_scale="OrRd",
            title="Puntaje promedio Saber 11 por departamento"
        )

    else:

        fig = px.choropleth(
            gdf_dep,
            geojson=gdf_dep.__geo_interface__,
            locations=gdf_dep.index,
            color="prop_total",
            hover_name="NOMBRE_DPT",
            color_continuous_scale="YlGnBu",
            title="Disponibilidad docente por departamento"
        )

    fig.update_geos(fitbounds="locations", visible=False)
    return fig

###############################################################
# 7. CALLBACK – SCATTER
###############################################################

@app.callback(
    Output("scatter_relacion", "figure"),
    Input("zona_selector", "value")
)
def actualizar_scatter(zona):

    if zona == "rural":
        temp = df[df["alumn_rural"] > 0]
        x_var = "prop_rural"
        titulo = "Disponibilidad Rural vs Puntaje Saber 11"

    elif zona == "urbano":
        temp = df[df["alumn_urbano"] > 0]
        x_var = "prop_urbano"
        titulo = "Disponibilidad Urbana vs Puntaje Saber 11"

    else:
        temp = df
        x_var = "prop_total"
        titulo = "Disponibilidad Total vs Puntaje Saber 11"

    # 🔥 SOLUCIÓN: limpiar NA y valores inválidos
    temp = temp.replace([np.inf, -np.inf], np.nan).dropna(subset=[x_var, "s11_total"])

    # Si aún queda vacío, devolvemos un gráfico vacío
    if temp.empty:
        fig = go.Figure()
        fig.update_layout(title="No hay datos suficientes para esta visualización")
        return fig

    fig = px.scatter(
        temp,
        x=x_var,
        y="s11_total",
        trendline="ols",
        title=titulo,
        labels={x_var: "Disponibilidad docente", "s11_total": "Puntaje Saber 11"}
    )

    return fig


###############################################################
# 8. CALLBACK – BARRAS DISPONIBILIDAD
###############################################################

@app.callback(
    Output("barras_disp", "figure"),
    Input("zona_selector", "value")
)
def barras(zona):

    resumen = df.groupby("disp_cat")["s11_total"].mean().reset_index()

    fig = px.bar(
        resumen,
        x="disp_cat",
        y="s11_total",
        text="s11_total",
        title="Puntaje promedio según nivel de disponibilidad"
    )

    fig.update_traces(texttemplate="%{text:.1f}")
    return fig

###############################################################
# 9. CALLBACK – BRECHA RURAL/URBANA
###############################################################

@app.callback(
    Output("brecha_rural_urbana", "figure"),
    Input("zona_selector", "value")
)
def brecha(zona):

    df2 = df.copy()
    df2["zona"] = np.where(df2["alumn_rural"] > df2["alumn_urbano"], "Rural", "Urbano")

    resumen = df2.groupby(["disp_cat", "zona"])["s11_total"].mean().reset_index()

    fig = px.bar(
        resumen,
        x="disp_cat",
        y="s11_total",
        color="zona",
        barmode="group",
        title="Brecha rural–urbana por nivel de disponibilidad"
    )

    return fig

###############################################################
# 10. EJECUTAR SERVIDOR
###############################################################

if __name__ == "__main__":
    app.run(debug=True)