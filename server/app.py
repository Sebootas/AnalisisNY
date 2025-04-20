from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pandas as pd
import re
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')
import seaborn as sns
from io import BytesIO


app = Flask(__name__)
CORS(app)

def is_likely_individual(name):
    name = str(name).strip().lower()
    if any(word in name for word in ["corp", "inc", "llc", "co", "company", "corporation", "&", "store"]):
        return False
    return bool(re.fullmatch(r"[a-z]+ [a-z]+", name))

def find_zip_column(columns, posibles_nombres):
    """
    Encuentra el nombre de la columna ZIP probable (case insensitive, sin espacios).
    """
    columnas_normalizadas = {col.strip().upper().replace(" ", "").replace("_", ""): col for col in columns}
    for nombre in posibles_nombres:
        clave = nombre.strip().upper().replace(" ", "").replace("_", "")
        if clave in columnas_normalizadas:
            return columnas_normalizadas[clave]
    return None

def analyze_data(business_df, demo_df):
    # Normalizar nombres de columnas
    business_df.columns = business_df.columns.str.strip()
    demo_df.columns = demo_df.columns.str.strip()

    # Buscar columna ZIP en datos de negocios
    business_zip_col = find_zip_column(business_df.columns, ['ZIP', 'ZIPCODE', 'ZIP CODE', 'Address ZIP'])
    demo_zip_col = find_zip_column(demo_df.columns, ['JURISDICTION NAME', 'ZIP', 'ZIPCODE'])

    if not business_zip_col:
        raise ValueError("No se encontró una columna ZIP válida en el archivo de negocios.")
    if not demo_zip_col:
        raise ValueError("No se encontró una columna ZIP válida en el archivo demográfico.")

    # Asegurar que las columnas ZIP estén como strings y con 5 dígitos
    business_df[business_zip_col] = business_df[business_zip_col].astype(str).str.zfill(5)
    demo_df[demo_zip_col] = demo_df[demo_zip_col].astype(str).str.zfill(5)

    # -------- NUEVO: detectar individuos --------
    business_df['is_individual'] = business_df['Business Name'].apply(is_likely_individual)

    # Groupby ZIP + Industry
    zip_industry_counts = business_df.groupby([business_zip_col, 'Industry']).size().reset_index(name='count_by_zip_industry')
    zip_industry_counts.rename(columns={business_zip_col: 'ZIP'}, inplace=True)

    # Conteo total de negocios por ZIP
    business_counts = business_df.groupby(business_zip_col).size().reset_index(name='business_count')
    business_counts.rename(columns={business_zip_col: 'ZIP'}, inplace=True)

    # Conteo de individuos por ZIP
    individual_counts = business_df[business_df['is_individual']].groupby(business_zip_col).size().reset_index(name='individual_count')
    individual_counts.rename(columns={business_zip_col: 'ZIP'}, inplace=True)

    # Merge counts
    merged_counts = business_counts.merge(individual_counts, on='ZIP', how='left')
    merged_counts['individual_count'] = merged_counts['individual_count'].fillna(0).astype(int)

    # Merge con datos demográficos
    demo_df.rename(columns={demo_zip_col: 'ZIP'}, inplace=True)
    merged = merged_counts.merge(demo_df, on='ZIP', how='left')

    # Filtrar filas donde faltan datos importantes
    merged = merged.dropna(subset=['business_count', 'ZIP'])
    merged = merged[(merged['business_count'] > 0)]

    # Correlación con ingreso si existe
    income_col = find_zip_column(merged.columns, ['MEDIAN INCOME', 'INCOME', 'AVG INCOME'])
    if income_col:
        merged[income_col] = pd.to_numeric(merged[income_col], errors='coerce')
        correlation = merged['business_count'].corr(merged[income_col])
    else:
        correlation = None

    # Top ZIPs por cantidad de negocios
    top_zips = merged.sort_values('business_count', ascending=False).head(5)[['ZIP', 'business_count']]

    # Top ZIPs por individuos
    top_individual_zips = merged.sort_values('individual_count', ascending=False).head(5)[['ZIP', 'individual_count']]

    # Ethnicity columns
    ethnicity_columns = [
        'PERCENT PACIFIC ISLANDER', 'PERCENT HISPANIC LATINO', 'PERCENT AMERICAN INDIAN',
        'PERCENT ASIAN NON HISPANIC', 'PERCENT WHITE NON HISPANIC', 'PERCENT BLACK NON HISPANIC',
        'PERCENT OTHER ETHNICITY', 'PERCENT ETHNICITY UNKNOWN'
    ]
    ethnicity_data = merged[ethnicity_columns + ['ZIP']].fillna("").to_dict(orient='records')

    # Preparar business_data
    business_sample = business_df[['Business Name', 'Industry', 'Address Building', 'Address Street Name',
                                   'License Type', 'License Status', 'DCA License Number', 'Address Borough',
                                   'Longitude', 'Latitude', business_zip_col, 'is_individual']].copy()
    business_sample.rename(columns={business_zip_col: 'ZIP'}, inplace=True)
    business_sample = business_sample.fillna("")
    business_data = business_sample.to_dict(orient='records')

    # Preparar demo_data
    demo_sample = demo_df.copy()
    demo_sample = demo_sample.dropna(subset=['PERCENT FEMALE', 'PERCENT MALE', 'PERCENT HISPANIC LATINO', 'PERCENT BLACK NON HISPANIC'])
    demo_sample = demo_sample[(demo_sample['COUNT FEMALE'] > 0) | (demo_sample['COUNT MALE'] > 0)]
    demo_sample = demo_sample.fillna("")
    demo_data = demo_sample.to_dict(orient='records')

    return {
        'correlation_with_income': correlation,
        'top_zipcodes': top_zips.to_dict(orient='records'),
        'top_individual_zipcodes': top_individual_zips.to_dict(orient='records'),
        'total_zipcodes': merged.shape[0],
        'business_data': business_data,
        'demo_data': demo_data,
        'ethnicity_data': ethnicity_data,
        'grouped_by_zip_industry': zip_industry_counts.to_dict(orient='records')
    }


@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        business_file = request.files.get('business')
        demo_file = request.files.get('demographics')

        if not business_file or not demo_file:
            return jsonify({"error": "Faltan uno o ambos archivos CSV."}), 400

        business_df = pd.read_csv(business_file, low_memory=False)
        demo_df = pd.read_csv(demo_file, low_memory=False)

        result = analyze_data(business_df, demo_df)

        return jsonify({"status": "success", "analysis": result})

    except Exception as e:
        print(f"Analysis error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/plot/pie_industries', methods=['POST'])
def pie_industries_plot():
    try:
        # Obtener archivo de negocios
        business_file = request.files.get('business')

        if not business_file:
            return jsonify({"error": "Archivo de negocios faltante."}), 400

        # Leer el archivo CSV
        business_df = pd.read_csv(business_file, low_memory=False)
        business_df.columns = business_df.columns.str.strip()

        # Agrupar por Industria y obtener los top 10
        industry_counts = business_df['Industry'].value_counts().reset_index()
        industry_counts.columns = ['Industry', 'count']

        # Ordenar y limitar a top 10
        industry_counts = industry_counts.sort_values('count', ascending=False)
        top_10 = industry_counts.head(10)

        # Calcular la suma de los demás
        other_count = industry_counts['count'][10:].sum()

        # Crear DataFrame final con "Other"
        final_counts = pd.concat([
            top_10,
            pd.DataFrame({'Industry': ['Other'], 'count': [other_count]})
        ])

        # Definir una paleta de colores distintivos
        colors = [
            '#4E79A7',  # blue
            '#F28E2B',  # orange
            '#E15759',  # red
            '#76B7B2',  # teal
            '#59A14F',  # green
            '#EDC948',  # yellow
            '#B07AA1',  # purple
            '#FF9DA7',  # pink
            '#9C755F',  # brown
            '#BAB0AC',  # gray
            '#7F7F7F'   # dark gray for "Other"
        ]

        # Crear gráfico de pastel con colores explícitos
        plt.figure(figsize=(8, 8))
        plt.pie(final_counts['count'],
                labels=final_counts['Industry'],
                autopct='%1.1f%%',
                startangle=140,
                colors=colors)
        plt.title('Distribución de Negocios por Industria (Top 10 + Other)')
        plt.axis('equal')

        # Devolver imagen como archivo
        buf = BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        plt.close()

        # Enviar la imagen
        return send_file(buf, mimetype='image/png')

    except Exception as e:
        print(f"Plot error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/plot/bar_business_per_capita', methods=['POST'])
def bar_business_per_capita_plot():
    try:
        print("Archivos recibidos:", request.files.keys())

        business_file = request.files.get('business')
        demo_file = request.files.get('demographics')

        if not business_file or not demo_file:
            return jsonify({"error": "Archivos de negocios o demográficos faltantes."}), 400

        business_df = pd.read_csv(business_file, low_memory=False)
        demo_df = pd.read_csv(demo_file, low_memory=False)

        # Limpiar nombres de columnas
        business_df.columns = business_df.columns.str.strip()
        demo_df.columns = demo_df.columns.str.strip()

        # Verificar y adaptar columnas ZIP
        if 'Address ZIP' in business_df.columns:
            business_df['ZIP'] = business_df['Address ZIP'].astype(str).str.zfill(5)
        elif 'ZIP' in business_df.columns:
            business_df['ZIP'] = business_df['ZIP'].astype(str).str.zfill(5)
        else:
            return jsonify({"error": "No se encuentra una columna ZIP válida en el archivo de negocios."}), 400

        if 'JURISDICTION NAME' not in demo_df.columns or 'COUNT GENDER TOTAL' not in demo_df.columns:
            return jsonify({"error": "Columnas necesarias no se encuentran en el archivo demográfico."}), 400

        # Agrupar negocios por ZIP
        business_zip_counts = business_df['ZIP'].value_counts().reset_index()
        business_zip_counts.columns = ['ZIP', 'business_count']

        # Preparar demográficos
        demo_df['ZIP'] = demo_df['JURISDICTION NAME'].astype(str).str.zfill(5)
        demo_zip = demo_df[['ZIP', 'COUNT GENDER TOTAL']].dropna()
        demo_zip.columns = ['ZIP', 'Total Population']

        # Merge y cálculo
        combined_data = pd.merge(business_zip_counts, demo_zip, on='ZIP', how='inner')

        # Filtrar ZIPs con población cero y calcular métrica
        combined_data = combined_data[combined_data['Total Population'] > 0]
        combined_data['business_per_capita'] = (combined_data['business_count'] / combined_data['Total Population']) * 1000

        # Ordenar y limitar a top 10
        combined_data = combined_data.sort_values('business_per_capita', ascending=False).head(10)

        # Crear gráfico con colores distintos
        plt.figure(figsize=(12, 6))
        colors = ['#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f',
                 '#edc948', '#b07aa1', '#ff9da7', '#9c755f', '#bab0ac']

        bars = plt.bar(combined_data['ZIP'],
                      combined_data['business_per_capita'],
                      color=colors[:len(combined_data)])

        plt.xlabel('ZIP Code')
        plt.ylabel('Negocios por 1000 Residentes')
        plt.title('Top 10 Códigos ZIP por Negocios per Cápita')
        plt.xticks(rotation=45)

        # Añadir valores encima de las barras
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}',
                    ha='center', va='bottom')

        plt.tight_layout()

        buf = BytesIO()
        plt.savefig(buf, format="png", dpi=120)
        buf.seek(0)
        plt.close()

        return send_file(buf, mimetype='image/png')

    except Exception as e:
        print(f"Plot error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/plot/correlation_heatmap', methods=['POST'])
def correlation_heatmap_plot():
    try:
        # Obtener archivos
        business_file = request.files.get('business')
        demo_file = request.files.get('demographics')

        if not business_file or not demo_file:
            return jsonify({"error": "Archivos de negocios o demográficos faltantes."}), 400

        # Leer archivos
        business_df = pd.read_csv(business_file, low_memory=False)
        demo_df = pd.read_csv(demo_file, low_memory=False)

        business_df.columns = business_df.columns.str.strip()
        demo_df.columns = demo_df.columns.str.strip()

        # Encontrar columnas ZIP
        business_zip_col = find_zip_column(business_df.columns, ['ZIP', 'ZIPCODE', 'ZIP CODE', 'Address ZIP'])
        demo_zip_col = find_zip_column(demo_df.columns, ['JURISDICTION NAME', 'ZIP', 'ZIPCODE'])

        if not business_zip_col or not demo_zip_col:
            return jsonify({"error": "No se pudo encontrar una columna ZIP válida en los archivos."}), 400

        business_df[business_zip_col] = business_df[business_zip_col].astype(str).str.zfill(5)
        demo_df[demo_zip_col] = demo_df[demo_zip_col].astype(str).str.zfill(5)

        # Agrupar negocios por ZIP
        business_counts = business_df.groupby(business_zip_col).size().reset_index(name='business_count')
        business_counts.rename(columns={business_zip_col: 'ZIP'}, inplace=True)

        # Preparar datos demográficos
        demo_df.rename(columns={demo_zip_col: 'ZIP'}, inplace=True)

        # Combinar datasets
        merged = pd.merge(demo_df, business_counts, on='ZIP', how='inner')

        # Filtrar columnas numéricas para la correlación
        numeric_cols = merged.select_dtypes(include=['number']).columns

        # Calcular matriz de correlación
        corr = merged[numeric_cols].corr()

        # Crear heatmap
        plt.figure(figsize=(12, 10))
        sns.heatmap(corr, annot=True, fmt=".2f", cmap='coolwarm', square=True)
        plt.title('Heatmap de Correlación entre Variables Numéricas')

        # Devolver imagen como archivo
        buf = BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()

        return send_file(buf, mimetype='image/png')

    except Exception as e:
        print(f"Heatmap error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
