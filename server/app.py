from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd

app = Flask(__name__)

# Enable CORS for all domains or specify your React app's origin
CORS(app)

@app.route('/api/upload', methods=['POST'])
def upload_file():
    try:
        # Check if a file is provided
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400

        file = request.files['file']

        # Check if the file is empty
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        # Read the CSV file into a DataFrame, handle NaN values and optimize memory
        df = pd.read_csv(file, low_memory=False)

        # Handle NaN values by replacing them with an empty string or another placeholder
        df = df.fillna('')

        # Convert the DataFrame to JSON format (choose the appropriate 'orient' based on how you want the data formatted)
        data = df.to_dict(orient='records')  # This gives a list of dictionaries, one per row

        # Return the processed data as a JSON response
        return jsonify({
            "status": "success",
            "data": data
        }), 200

    except pd.errors.ParserError:
        return jsonify({"error": "CSV parsing error. Please check the file format."}), 400
    except Exception as e:
        # Log the exception to the console and return a generic error message
        print(f"Error: {str(e)}")  # Log the actual error for debugging
        return jsonify({"error": "An internal server error occurred"}), 500

if __name__ == '__main__':
    app.run(debug=True)
