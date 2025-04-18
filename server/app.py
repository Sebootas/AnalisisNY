from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd

app = Flask(__name__)
CORS(app)

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

    # Contar negocios por ZIP
    business_counts = business_df.groupby(business_zip_col).size().reset_index(name='business_count')
    business_counts.rename(columns={business_zip_col: 'ZIP'}, inplace=True)

    # Merge con datos demográficos
    demo_df.rename(columns={demo_zip_col: 'ZIP'}, inplace=True)
    merged = business_counts.merge(demo_df, on='ZIP', how='left')

    # Filtrar filas donde faltan datos importantes
    merged = merged.dropna(subset=['business_count', 'ZIP'])  # Asegurarse de que haya negocios y un ZIP
    merged = merged[(merged['business_count'] > 0)]  # Solo considerar ZIPs con negocios

    # Correlación con ingreso si existe
    income_col = find_zip_column(merged.columns, ['MEDIAN INCOME', 'INCOME', 'AVG INCOME'])
    if income_col:
        merged[income_col] = pd.to_numeric(merged[income_col], errors='coerce')
        correlation = merged['business_count'].corr(merged[income_col])
    else:
        correlation = None

    # Top ZIPs
    top_zips = merged.sort_values('business_count', ascending=False).head(5)[['ZIP', 'business_count']]

    # Preparar todos los datos para el frontend
    business_sample = business_df[['Business Name', 'Industry', 'Address Building', 'Address Street Name', 'License Type', 'License Status', 'DCA License Number', 'Address Borough', 'Longitude', 'Latitude', business_zip_col]].copy()
    business_sample.rename(columns={business_zip_col: 'ZIP'}, inplace=True)
    business_sample = business_sample.fillna("")  # Reemplazar NaN por ""
    business_data = business_sample.to_dict(orient='records')  # Sin límite de 100

    demo_sample = demo_df.copy()

    # Filtrar datos demográficos donde se tengan registros válidos de la población
    demo_sample = demo_sample.dropna(subset=['PERCENT FEMALE', 'PERCENT MALE', 'PERCENT HISPANIC LATINO', 'PERCENT BLACK NON HISPANIC'])  # Eliminar filas con datos nulos relevantes
    demo_sample = demo_sample[(demo_sample['COUNT FEMALE'] > 0) | (demo_sample['COUNT MALE'] > 0)]  # Eliminar filas con 0 participación de género

    demo_sample = demo_sample.fillna("")  # Reemplazar NaN por ""
    demo_data = demo_sample.to_dict(orient='records')  # Sin límite de 100

    return {
        'correlation_with_income': correlation,
        'top_zipcodes': top_zips.to_dict(orient='records'),
        'total_zipcodes': merged.shape[0],
        'business_data': business_data,
        'demo_data': demo_data
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

if __name__ == '__main__':
    app.run(debug=True)
