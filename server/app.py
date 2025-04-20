from flask import Flask, request, jsonify, send_file, redirect, url_for
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

@app.route("/")
def home():
    return redirect(url_for('analyze'))

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


@app.route('/api/analyze', methods=['GET', 'POST'])
def analyze():
    try:
        if request.method == 'GET':
            return "Please submit your data via POST request"
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
        # Get business file
        business_file = request.files.get('business')
        if not business_file:
            return jsonify({"error": "Archivo de negocios faltante."}), 400

        # Read CSV
        business_df = pd.read_csv(business_file, low_memory=False)
        business_df.columns = business_df.columns.str.strip()

        # Group by Industry and get top 10
        industry_counts = business_df['Industry'].value_counts().reset_index()
        industry_counts.columns = ['Industry', 'count']
        industry_counts = industry_counts.sort_values('count', ascending=False)
        top_10 = industry_counts.head(10)
        other_count = industry_counts['count'][10:].sum()

        # Create final DataFrame
        final_counts = pd.concat([
            top_10,
            pd.DataFrame({'Industry': ['Other'], 'count': [other_count]})
        ])

        # Define colors
        colors = [
            '#4E79A7', '#F28E2B', '#E15759', '#76B7B2', '#59A14F',
            '#EDC948', '#B07AA1', '#FF9DA7', '#9C755F', '#BAB0AC', '#7F7F7F'
        ]

        # Create optimized pie chart
        plt.figure(figsize=(12, 12), dpi=120)

        # Shorten long labels
        labels = [label[:29] + '...' if len(label) > 29 else label
                 for label in final_counts['Industry']]

        wedges, texts, autotexts = plt.pie(
            final_counts['count'],
            labels=labels,
            colors=colors,
            autopct='%1.1f%%',
            pctdistance=0.85,
            startangle=140,
            textprops={'fontsize': 10}
        )


        plt.title('Distribución de Negocios por Industria (Top 10 + Other)', pad=20)
        plt.tight_layout(pad=5)

        # Save and return image
        buf = BytesIO()
        plt.savefig(buf, format="png", bbox_inches='tight', dpi=120)
        buf.seek(0)
        plt.close()

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
        # Get files
        business_file = request.files.get('business')
        demo_file = request.files.get('demographics')

        if not business_file or not demo_file:
            return jsonify({"error": "Missing business or demographic files."}), 400

        # Read files
        business_df = pd.read_csv(business_file, low_memory=False)
        demo_df = pd.read_csv(demo_file, low_memory=False)

        # Clean column names
        business_df.columns = business_df.columns.str.strip()
        demo_df.columns = demo_df.columns.str.strip()

        # Standardize ZIP codes
        business_df['ZIP'] = business_df['Address ZIP'].astype(str).str.extract('(\d{5})')[0]
        demo_df['ZIP'] = demo_df['JURISDICTION NAME'].astype(str).str.extract('(\d{5})')[0]

        # Prepare demographic data - focus on key columns
        demo_cols = ['ZIP', 'COUNT GENDER TOTAL',
                    'PERCENT FEMALE', 'PERCENT HISPANIC LATINO',
                    'PERCENT ASIAN NON HISPANIC', 'PERCENT WHITE NON HISPANIC',
                    'PERCENT BLACK NON HISPANIC']
        demo_df = demo_df[demo_cols].dropna()

        # Rename columns for clarity
        demo_df.columns = ['ZIP', 'Total Population', 'Percent Female',
                          'Percent Hispanic Latino', 'Percent Asian',
                          'Percent White', 'Percent Black']

        # Count businesses by ZIP
        business_counts = business_df['ZIP'].value_counts().reset_index()
        business_counts.columns = ['ZIP', 'business_count']

        # Merge data
        merged = pd.merge(business_counts, demo_df, on='ZIP', how='inner')
        merged['business_density'] = (merged['business_count'] / merged['Total Population']) * 1000

        # Calculate correlations
        corr_cols = ['business_density', 'Total Population', 'Percent Female',
                    'Percent Hispanic Latino', 'Percent Asian',
                    'Percent White', 'Percent Black']
        corr_matrix = merged[corr_cols].corr()

        # Create figure with adjusted size
        plt.figure(figsize=(12, 10), dpi=120)

        # Create heatmap with better formatting
        ax = sns.heatmap(
            corr_matrix,
            annot=True,
            fmt=".2f",
            cmap='coolwarm',
            center=0,
            vmin=-1,
            vmax=1,
            annot_kws={"size": 12},
            cbar_kws={"shrink": 0.8}
        )

        # Rotate and adjust x-axis labels
        ax.set_xticklabels(
            ax.get_xticklabels(),
            rotation=45,
            ha='right',
            fontsize=12
        )

        # Adjust y-axis labels
        ax.set_yticklabels(
            ax.get_yticklabels(),
            rotation=0,
            fontsize=12
        )

        plt.title('Business-Demographic Correlations by ZIP Code', pad=20, fontsize=14)

        # Adjust layout with more padding
        plt.tight_layout(pad=3)

        # Save with higher quality and proper bounding box
        buf = BytesIO()
        plt.savefig(
            buf,
            format='png',
            dpi=120,
            bbox_inches='tight',
            pad_inches=0.5
        )
        buf.seek(0)
        plt.close()

        return send_file(buf, mimetype='image/png')

    except Exception as e:
        print(f"Heatmap error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
