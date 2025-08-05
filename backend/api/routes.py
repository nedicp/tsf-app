from flask import request, jsonify, session, send_file
from werkzeug.utils import secure_filename
import os
import pandas as pd
import openpyxl
from datetime import datetime
import json
import tempfile
import uuid
import numpy as np
from . import api_bp
from backend.utils.ml_api_client import ml_client
from backend.utils.limiter import limiter

# Store for uploaded files and predictions (in production, use database)
uploaded_files = {}
prediction_results = {}

EXPECTED_COLUMNS = [
    'Sjutra praznik',
    'Dan u nedelji',
    'Dan u mjesecu',
    'Mjesec',
    'Sat',
    'Temp. min Pg', 'Temp. max Pg', 'Temp. sr Pg',
    'Temp. min Nk', 'Temp. max Nk', 'Temp. sr Nk',
    'Temp. min Pv', 'Temp. max Pv', 'Temp. sr Pv',
    'Temp. min Br', 'Temp. max Br', 'Temp. sr Br',
    'Temp. min Ul', 'Temp. max Ul', 'Temp. sr Ul',
    'Temp. min Ct', 'Temp. max Ct', 'Temp. sr Ct',
    'Prethodna 24h'
]

def count_non_empty(series):
    """Helper function to count non-empty values (0 is considered valid)"""
    # Fill NA/NaN values with an empty string to make the series safe for comparison.
    # This ensures that we don't get the 'ambiguous boolean' error.
    series_filled = series.fillna('')
    # Now, simply count every entry that is not an empty string.
    # This correctly includes 0, 0.0, and any other text or number.
    return (series_filled != '').sum()

@api_bp.route('/upload', methods=['POST'])
@limiter.limit("10 per minute")  # Max 10 uploads per minute
def upload_file():
    """Handle Excel file upload with strict validation"""
    try:
        # Check authentication
        if 'user' not in session:
            return jsonify({'success': False, 'message': 'Not authenticated'}), 401

        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400

        # Validate file type
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({'success': False, 'message': 'File must be Excel format (.xlsx or .xls)'}), 400

        # Save file temporarily
        filename = secure_filename(file.filename)
        file_id = str(uuid.uuid4())
        temp_path = os.path.join(tempfile.gettempdir(), f"{file_id}_{filename}")
        file.save(temp_path)

        # Validate Excel structure
        validation_result = validate_excel_structure(temp_path)

        if not validation_result['is_valid']:
            # Clean up temp file
            os.remove(temp_path)
            return jsonify({
                'success': False,
                'message': f"Validation failed: {'; '.join(validation_result['errors'])}"
            }), 400

        # Store file info and data
        uploaded_files[file_id] = {
            'filename': filename,
            'path': temp_path,
            'upload_time': datetime.now(),
            'user_id': session['user']['username']
        }

        return jsonify({
            'success': True,
            'data': {
                'fileId': file_id,
                'fileName': filename,
                'preview': validation_result['preview_data'],
                'statistics': validation_result['statistics']
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'Upload failed: {str(e)}'}), 500

def fill_missing_values(df):
    """Fill missing values with repeated values according to business rules"""
    df_filled = df.copy()

    # Define columns where the first valid entry should be repeated downwards
    repeat_down_columns = EXPECTED_COLUMNS.copy()
    repeat_down_columns.remove('Prethodna 24h') # This column must be full
    repeat_down_columns.remove('Sat') # Hour has special handling

    for col in repeat_down_columns:
        # Forward fill the first valid value downwards
        df_filled[col] = df_filled[col].ffill()

    # Handle the 'Sat' (hour) column specifically
    # If only one hour value is provided, fill the rest incrementally
    if count_non_empty(df_filled['Sat']) == 1:
        first_hour_index = df_filled['Sat'].first_valid_index()
        if first_hour_index is not None:
            start_hour = int(df_filled.loc[first_hour_index, 'Sat'])
            for i in range(24):
                df_filled.loc[i, 'Sat'] = (start_hour + i) % 24

    # After all filling logic, replace any remaining NaNs with empty strings for the final preview
    df_filled = df_filled.fillna('')

    return df_filled

def validate_excel_structure(file_path):
    """Validate Excel file structure according to strict requirements"""
    try:
        # Read Excel file
        df = pd.read_excel(file_path, engine='openpyxl')

        errors = []

        # 1. Check dimensions (25 rows total = 1 header + 24 data rows)
        if len(df) != 24:
            errors.append(f"Must have exactly 24 data rows, found {len(df)} rows")

        if len(df.columns) != 24:
            errors.append(f"Must have exactly 24 columns, found {len(df.columns)} columns")

        # 2. Check column names and order
        actual_columns = df.columns.tolist()
        for i, expected_col in enumerate(EXPECTED_COLUMNS):
            if i >= len(actual_columns) or actual_columns[i] != expected_col:
                errors.append(f"Column {i+1} should be '{expected_col}', found '{actual_columns[i] if i < len(actual_columns) else 'missing'}'")

        # If basic structure is wrong, return early
        if errors:
            return {'is_valid': False, 'errors': errors}

        # 3. Validate data patterns
        data_validation = validate_data_patterns(df)
        if data_validation['errors']:
            errors.extend(data_validation['errors'])

        # 4. Generate preview data and statistics
        filled_df = fill_missing_values(df)
        preview_data = filled_df.to_dict('records')
        statistics = calculate_statistics(df)

        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'preview_data': preview_data,
            'statistics': statistics
        }

    except Exception as e:
        return {'is_valid': False, 'errors': [f"Failed to read Excel file: {str(e)}"]}

def validate_data_patterns(df):
    """Validate data patterns according to business rules"""
    errors = []

    # 1. Sjutra praznik (1-2 values or all 24 values)
    sjutra_count = count_non_empty(df['Sjutra praznik'])
    if sjutra_count not in [1, 2, 24]:
        errors.append(f"'Sjutra praznik' must have 1-2 values or all 24 values, found {sjutra_count}")

    # 2. Sat (Hour) - 1 or all 24 values
    sat_count = count_non_empty(df['Sat'])
    if sat_count != 1 and sat_count != 24:
        errors.append(f"'Sat' must have 1 or 24 values, found {sat_count}")

    # 3. Date columns - 1 or all 24 values
    for col in ['Dan u mjesecu', 'Mjesec', 'Dan u nedelji']:
        col_count = count_non_empty(df[col])
        if col_count != 1 and col_count != 24:
            errors.append(f"'{col}' must have 1 or 24 values, found {col_count}")

    # 4. Temperature columns (1-2 values or all 24 values)
    temp_columns = [col for col in EXPECTED_COLUMNS if col.startswith('Temp.')]
    for col in temp_columns:
        temp_count = count_non_empty(df[col])
        if temp_count not in [1, 2, 24]:
            errors.append(f"'{col}' must have 1-2 or 24 values, found {temp_count}")

    # 5. Prethodna 24h - MUST have all 24 values
    consumption_count = count_non_empty(df['Prethodna 24h'])
    if consumption_count != 24:
        errors.append(f"'Prethodna 24h' must have all 24 values, found {consumption_count}")

    # 6. Advanced validation for hour sequences and same-day consistency
    advanced_errors = validate_advanced_patterns(df)
    errors.extend(advanced_errors)

    return {'errors': errors}

def validate_advanced_patterns(df):
    """Advanced validation for hour sequences and same-day consistency"""
    errors = []

    # Convert hour column to numeric, handling empty values
    try:
        hours_series = pd.to_numeric(df['Sat'], errors='coerce')
        valid_hours = hours_series.dropna()

        if len(valid_hours) > 0:
            # 1. Validate hour values are in range 1-24 (not 0-23)
            invalid_hours = valid_hours[(valid_hours < 1) | (valid_hours > 24)]
            if len(invalid_hours) > 0:
                errors.append(f"Hours must be between 1-24, found invalid values: {invalid_hours.tolist()}")

            # 2. If we have all 24 hours, validate the sequence and same-day consistency
            if len(valid_hours) == 24:
                errors.extend(validate_hour_sequence_and_consistency(df, hours_series))

    except Exception as e:
        errors.append(f"Error validating hour column: {str(e)}")

    return errors

def validate_hour_sequence_and_consistency(df, hours_series):
    """Validate hour sequences and same-day data consistency"""
    errors = []

    try:
        # Group rows by day based on hour resets
        day_groups = []
        current_day = []

        for i, hour in enumerate(hours_series):
            if pd.isna(hour):
                continue

            hour = int(hour)
            current_day.append((i, hour))

            # If we see hour 24 or if next hour is less than current (day reset), end current day
            if hour == 24 or (i < len(hours_series) - 1 and
                             not pd.isna(hours_series.iloc[i + 1]) and
                             int(hours_series.iloc[i + 1]) < hour):
                day_groups.append(current_day)
                current_day = []

        # Add remaining hours to last day if any
        if current_day:
            day_groups.append(current_day)

        # Validate each day group
        for day_idx, day_rows in enumerate(day_groups):
            if not day_rows:
                continue

            day_errors = validate_single_day(df, day_rows, day_idx + 1)
            errors.extend(day_errors)

    except Exception as e:
        errors.append(f"Error validating day sequences: {str(e)}")

    return errors

def validate_single_day(df, day_rows, day_number):
    """Validate a single day's data for consistency and hour sequence"""
    errors = []

    try:
        # Extract row indices and hours for this day
        row_indices = [row[0] for row in day_rows]
        hours = [row[1] for row in day_rows]

        # 1. Validate hour sequence within the day (should be incremental)
        if len(hours) > 1:
            for i in range(1, len(hours)):
                expected_hour = hours[i-1] + 1
                if hours[i] != expected_hour:
                    # Allow wrap-around from 24 to 1 only at day boundaries
                    if not (hours[i-1] == 24 and hours[i] == 1):
                        errors.append(f"Day {day_number}: Hour sequence not incremental. Hour {hours[i-1]} followed by {hours[i]} at rows {row_indices[i-1]+1}-{row_indices[i]+1}")

        # 2. Validate same-day consistency for columns that should be identical within a day
        same_day_columns = ['Sjutra praznik', 'Dan u nedelji', 'Dan u mjesecu', 'Mjesec']

        # Add temperature columns
        temp_columns = [col for col in EXPECTED_COLUMNS if col.startswith('Temp.')]
        same_day_columns.extend(temp_columns)

        for col in same_day_columns:
            if col in df.columns:
                day_values = []
                for row_idx in row_indices:
                    val = df.iloc[row_idx][col]
                    if pd.notna(val) and val != '':
                        day_values.append(val)

                # If we have multiple values for this day, they should all be the same
                if len(day_values) > 1:
                    unique_values = list(set(day_values))
                    if len(unique_values) > 1:
                        errors.append(f"Day {day_number}: '{col}' has inconsistent values within the same day: {unique_values} (rows {[r+1 for r in row_indices]})")

        # 3. Validate that we don't have gaps in the day (if it's a complete day)
        if len(hours) > 1:
            min_hour = min(hours)
            max_hour = max(hours)
            expected_hours = list(range(min_hour, max_hour + 1))

            if len(hours) == len(expected_hours) and hours != expected_hours:
                missing_hours = set(expected_hours) - set(hours)
                if missing_hours:
                    errors.append(f"Day {day_number}: Missing hours in sequence: {sorted(missing_hours)}")

    except Exception as e:
        errors.append(f"Error validating day {day_number}: {str(e)}")

    return errors

def calculate_statistics(df):
    """Calculate basic statistics from the data"""
    try:
        consumption_data = pd.to_numeric(df['Prethodna 24h'], errors='coerce').dropna()

        return {
            'totalRows': len(df),
            'totalColumns': len(df.columns),
            'avgConsumption': consumption_data.mean(),
            'peakConsumption': consumption_data.max(),
            'minConsumption': consumption_data.min(),
            'totalConsumption': consumption_data.sum()
        }
    except:
        return {
            'totalRows': len(df),
            'totalColumns': len(df.columns),
            'avgConsumption': 0,
            'peakConsumption': 0,
            'minConsumption': 0,
            'totalConsumption': 0
        }

@api_bp.route('/predict', methods=['POST'])
@limiter.limit("5 per minute")  # Max 5 predictions per minute (expensive operation)
def generate_predictions():
    """Generate predictions using specified model"""
    try:
        # Check authentication
        if 'user' not in session:
            return jsonify({'success': False, 'message': 'Not authenticated'}), 401

        data = request.get_json()
        file_id = data.get('fileId')
        prediction_period = data.get('predictionPeriod', 24)
        model_type = data.get('modelType', 'nbeats')

        # Validate input
        if not file_id or file_id not in uploaded_files:
            return jsonify({'success': False, 'message': 'Invalid or missing file'}), 400

        # Load the uploaded file data
        file_info = uploaded_files[file_id]
        df = pd.read_excel(file_info['path'], engine='openpyxl')

        # First, check if ML API is available
        if not ml_client.health_check():
            return jsonify({
                'success': False,
                'message': 'ML prediction service is currently unavailable. Please try again later.',
                'service_status': 'offline'
            }), 503

        # Extract historical consumption data for response
        consumption_data = pd.to_numeric(df['Prethodna 24h'], errors='coerce').tolist()

        # Extract starting hour from uploaded data
        start_hour = 0
        sat_values = df['Sat'][df['Sat'].notna() & (df['Sat'] != '')]
        if len(sat_values) > 0:
            start_hour = int(sat_values.iloc[0])

        # Generate hour labels starting from the uploaded data's first hour
        hour_labels = []
        for i in range(24):
            hour = (start_hour + i) % 24
            hour_labels.append(f"{hour:02d}:00")

        # Prepare data for ML API (24x24 format)
        try:
            ml_data = ml_client.prepare_data_for_ml_api(df)
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Failed to prepare data for ML model: {str(e)}'
            }), 400

        # Make prediction using ML API
        prediction_result = ml_client.make_prediction(ml_data, model_type)

        if not prediction_result['success']:
            return jsonify({
                'success': False,
                'message': f"ML prediction failed: {prediction_result['error']}",
                'service_status': 'error'
            }), 500

        # Extract predictions and calculate confidence intervals
        raw_predictions = prediction_result['predictions']

        # Ensure we have exactly 24 predictions
        if len(raw_predictions) != 24:
            return jsonify({
                'success': False,
                'message': f'Invalid prediction length: expected 24, got {len(raw_predictions)}'
            }), 500

        # Calculate confidence intervals (±3% as in mock)
        predictions_array = np.array(raw_predictions)
        confidence_min = (predictions_array * 0.97).tolist()
        confidence_max = (predictions_array * 1.03).tolist()

        # Calculate accuracy based on model type (use metadata if available)
        metadata = prediction_result.get('metadata', {})
        processing_time = metadata.get('processing_time', 0)

        # Model accuracy estimates (you can adjust these based on your model performance)
        model_accuracies = {
            'nbeats': 92.5,
            'cnn-nbeats': 94.2,
            'nbeats-cnn': 93.8
        }
        accuracy = model_accuracies.get(model_type, 90.0)

        predictions = {
            'values': raw_predictions,
            'confidence_min': confidence_min,
            'confidence_max': confidence_max,
            'accuracy': accuracy,
            'processing_time': processing_time
        }

        # Store prediction results
        prediction_id = str(uuid.uuid4())
        prediction_results[prediction_id] = {
            'file_id': file_id,
            'model_type': model_type,
            'predictions': predictions,
            'timestamp': datetime.now(),
            'user_id': session['user']['username']
        }

        return jsonify({
            'success': True,
            'data': {
                'predictionId': prediction_id,
                'hours': hour_labels,
                'historical': consumption_data,
                'predictions': predictions['values'],
                'confidenceMin': predictions['confidence_min'],
                'confidenceMax': predictions['confidence_max'],
                'accuracy': predictions['accuracy'],
                'modelType': model_type,
                'startHour': start_hour,
                'processingTime': predictions.get('processing_time', 0),
                'serviceStatus': 'online'
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Prediction failed: {str(e)}',
            'service_status': 'error'
        }), 500

def generate_mock_predictions(historical_data, model_type):
    """Generate mock predictions based on historical data"""
    import numpy as np

    # Use historical data as base with some variation
    base_values = np.array(historical_data)

    # Add model-specific variations
    if model_type == 'nbeats':
        # N-BEATS: smooth trending
        predictions = base_values * (1 + np.sin(np.arange(24) * np.pi / 12) * 0.1)
        accuracy = 92.5
    elif model_type == 'cnn-nbeats':
        # CNN-N-BEATS: more pattern recognition
        predictions = base_values * (1 + np.cos(np.arange(24) * np.pi / 8) * 0.15)
        accuracy = 94.2
    elif model_type == 'nbeats-cnn':
        # N-BEATS-CNN: hybrid approach
        predictions = base_values * (1 + np.sin(np.arange(24) * np.pi / 6) * 0.12)
        accuracy = 93.8
    else:
        predictions = base_values
        accuracy = 90.0

    # Add slight random variation
    predictions = predictions * (1 + np.random.normal(0, 0.05, 24))

    # Calculate confidence intervals (±3%)
    confidence_min = predictions * 0.97
    confidence_max = predictions * 1.03

    return {
        'values': predictions.tolist(),
        'confidence_min': confidence_min.tolist(),
        'confidence_max': confidence_max.tolist(),
        'accuracy': accuracy
    }

@api_bp.route('/export', methods=['POST'])
@limiter.limit("20 per hour")  # Max 20 exports per hour
def export_predictions():
    """Export prediction results in specified format"""
    try:
        # Check authentication
        if 'user' not in session:
            return jsonify({'success': False, 'message': 'Not authenticated'}), 401

        data = request.get_json()
        prediction_data = data.get('data')
        format_type = data.get('format', 'csv')

        if not prediction_data:
            return jsonify({'success': False, 'message': 'No data to export'}), 400

        # Get starting hour from prediction data
        start_hour = prediction_data.get('startHour', 0)

        # Generate hour labels starting from the actual starting hour
        hour_labels = []
        for i in range(24):
            hour = (start_hour + i) % 24
            hour_labels.append(f"{hour:02d}:00")

        # Combine confidence intervals into Serbian format
        confidence_min = prediction_data.get('confidenceMin', [])
        confidence_max = prediction_data.get('confidenceMax', [])
        confidence_intervals = []

        for min_val, max_val in zip(confidence_min, confidence_max):
            if min_val is not None and max_val is not None:
                confidence_intervals.append(f"{min_val:.4f}-{max_val:.4f}")
            else:
                confidence_intervals.append("--")

        # Format numerical data to 4 decimal places
        historical_data = prediction_data.get('historical', [])
        prediction_values = prediction_data.get('predictions', [])

        # Format to 4 decimal places
        formatted_historical = [f"{val:.4f}" if val is not None else "--" for val in historical_data]
        formatted_predictions = [f"{val:.4f}" if val is not None else "--" for val in prediction_values]

        # Create export data with Serbian column names
        export_df = pd.DataFrame({
            'Sat': hour_labels,
            'Prethodna 24h': formatted_historical,
            'Predikcija 24h': formatted_predictions,
            'Ocekivani interval odstupanja': confidence_intervals
        })

        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if format_type == 'csv':
            filename = f'predikcija_{timestamp}.csv'
            temp_path = os.path.join(tempfile.gettempdir(), filename)
            export_df.to_csv(temp_path, index=False, encoding='utf-8')

        elif format_type == 'excel':
            filename = f'predikcija_{timestamp}.xlsx'
            temp_path = os.path.join(tempfile.gettempdir(), filename)
            export_df.to_excel(temp_path, index=False, engine='openpyxl')

        elif format_type == 'pdf':
            # For PDF, we'll use a simple text-based approach
            filename = f'predikcija_{timestamp}.txt'
            temp_path = os.path.join(tempfile.gettempdir(), filename)
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write("Predikcija potrošnje električne energije\n")
                f.write("="*45 + "\n\n")
                f.write(export_df.to_string(index=False))

        return send_file(
            temp_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )

    except Exception as e:
        return jsonify({'success': False, 'message': f'Export failed: {str(e)}'}), 500

# Model-specific prediction endpoints (for future use)
@api_bp.route('/models/nbeats', methods=['POST'])
def predict_nbeats():
    """N-BEATS model prediction endpoint (placeholder)"""
    return jsonify({'message': 'N-BEATS model endpoint - to be implemented'})

@api_bp.route('/models/cnn-nbeats', methods=['POST'])
def predict_cnn_nbeats():
    """CNN-N-BEATS model prediction endpoint (placeholder)"""
    return jsonify({'message': 'CNN-N-BEATS model endpoint - to be implemented'})

@api_bp.route('/models/nbeats-cnn', methods=['POST'])
def predict_nbeats_cnn():
    """N-BEATS-CNN model prediction endpoint (placeholder)"""
    return jsonify({'message': 'N-BEATS-CNN model endpoint - to be implemented'})

# Health check endpoint
@api_bp.route('/health', methods=['GET'])
def health_check():
    """API health check"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@api_bp.route('/ml-service/health', methods=['GET'])
def ml_service_health():
    """Check ML service availability"""
    try:
        is_healthy = ml_client.health_check()
        return jsonify({
            'status': 'healthy' if is_healthy else 'unhealthy',
            'ml_service': 'online' if is_healthy else 'offline',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'ml_service': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500
