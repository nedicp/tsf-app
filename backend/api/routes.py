from flask import request, jsonify, session, send_file
from werkzeug.utils import secure_filename
import os
import pandas as pd
from datetime import datetime
import tempfile
import uuid
import numpy as np
from . import api_bp
from backend.utils.ml_api_client import ml_client
from backend.utils.limiter import limiter

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
    series_filled = series.fillna('')
    return (series_filled != '').sum()

@api_bp.route('/upload', methods=['POST'])
@limiter.limit("5 per minute")
def upload_file():
    """Handle Excel file upload with strict validation"""
    try:
        if 'user' not in session:
            return jsonify({'success': False, 'message': 'Not authenticated'}), 401

        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400

        if not file.filename.lower().endswith(('.xlsx', '.xls', '.csv')):
            return jsonify({'success': False, 'message': 'File must be Excel or CSV format (.xlsx, .xls, or .csv)'}), 400

        filename = secure_filename(file.filename)
        file_id = str(uuid.uuid4())
        temp_path = os.path.join(tempfile.gettempdir(), f"{file_id}_{filename}")
        file.save(temp_path)

        validation_result = validate_excel_structure(temp_path)

        if not validation_result['is_valid']:
            os.remove(temp_path)
            return jsonify({
                'success': False,
                'message': f"Validation failed: {'; '.join(validation_result['errors'])}"
            }), 400

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

    repeat_down_columns = EXPECTED_COLUMNS.copy()
    repeat_down_columns.remove('Prethodna 24h')
    repeat_down_columns.remove('Sat')

    for col in repeat_down_columns:
        df_filled[col] = df_filled[col].ffill()

    if count_non_empty(df_filled['Sat']) == 1:
        first_hour_index = df_filled['Sat'].first_valid_index()
        if first_hour_index is not None:
            start_hour = int(df_filled.loc[first_hour_index, 'Sat'])
            for i in range(24):
                df_filled.loc[i, 'Sat'] = (start_hour + i) % 24

    df_filled = df_filled.fillna('')

    return df_filled

def validate_excel_structure(file_path):
    """Validate file structure according to strict requirements"""
    try:
        if file_path.lower().endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path, engine='openpyxl')

        errors = []

        if len(df) != 24:
            errors.append(f"Must have exactly 24 data rows, found {len(df)} rows")

        if len(df.columns) != 24:
            errors.append(f"Must have exactly 24 columns, found {len(df.columns)} columns")

        actual_columns = df.columns.tolist()
        for i, expected_col in enumerate(EXPECTED_COLUMNS):
            if i >= len(actual_columns) or actual_columns[i] != expected_col:
                errors.append(f"Column {i+1} should be '{expected_col}', found '{actual_columns[i] if i < len(actual_columns) else 'missing'}'")

        if errors:
            return {'is_valid': False, 'errors': errors}

        data_validation = validate_data_patterns(df)
        if data_validation['errors']:
            errors.extend(data_validation['errors'])

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
        return {'is_valid': False, 'errors': [f"Failed to read file: {str(e)}"]}

def validate_data_patterns(df):
    """Validate data patterns according to business rules"""
    errors = []

    sjutra_count = count_non_empty(df['Sjutra praznik'])
    if sjutra_count not in [1, 2, 24]:
        errors.append(f"'Sjutra praznik' must have 1-2 values or all 24 values, found {sjutra_count}")

    sat_count = count_non_empty(df['Sat'])
    if sat_count != 1 and sat_count != 24:
        errors.append(f"'Sat' must have 1 or 24 values, found {sat_count}")

    for col in ['Dan u mjesecu', 'Mjesec', 'Dan u nedelji']:
        col_count = count_non_empty(df[col])
        if col_count != 1 and col_count != 24:
            errors.append(f"'{col}' must have 1 or 24 values, found {col_count}")

    temp_columns = [col for col in EXPECTED_COLUMNS if col.startswith('Temp.')]
    for col in temp_columns:
        temp_count = count_non_empty(df[col])
        if temp_count not in [1, 2, 24]:
            errors.append(f"'{col}' must have 1-2 or 24 values, found {temp_count}")

    consumption_count = count_non_empty(df['Prethodna 24h'])
    if consumption_count != 24:
        errors.append(f"'Prethodna 24h' must have all 24 values, found {consumption_count}")

    advanced_errors = validate_advanced_patterns(df)
    errors.extend(advanced_errors)

    return {'errors': errors}

def validate_advanced_patterns(df):
    """Advanced validation for hour sequences and same-day consistency"""
    errors = []

    try:
        hours_series = pd.to_numeric(df['Sat'], errors='coerce')
        valid_hours = hours_series.dropna()

        if len(valid_hours) > 0:
            invalid_hours = valid_hours[(valid_hours < 1) | (valid_hours > 24)]
            if len(invalid_hours) > 0:
                errors.append(f"Hours must be between 1-24, found invalid values: {invalid_hours.tolist()}")

            if len(valid_hours) == 24:
                errors.extend(validate_hour_sequence_and_consistency(df, hours_series))

    except Exception as e:
        errors.append(f"Error validating hour column: {str(e)}")

    return errors

def validate_hour_sequence_and_consistency(df, hours_series):
    """Validate hour sequences and same-day data consistency"""
    errors = []

    try:
        day_groups = []
        current_day = []

        for i, hour in enumerate(hours_series):
            if pd.isna(hour):
                continue

            hour = int(hour)
            current_day.append((i, hour))

            if hour == 24 or (i < len(hours_series) - 1 and
                             not pd.isna(hours_series.iloc[i + 1]) and
                             int(hours_series.iloc[i + 1]) < hour):
                day_groups.append(current_day)
                current_day = []

        if current_day:
            day_groups.append(current_day)

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
        row_indices = [row[0] for row in day_rows]
        hours = [row[1] for row in day_rows]

        if len(hours) > 1:
            for i in range(1, len(hours)):
                expected_hour = hours[i-1] + 1
                if hours[i] != expected_hour:
                    if not (hours[i-1] == 24 and hours[i] == 1):
                        errors.append(f"Day {day_number}: Hour sequence not incremental. Hour {hours[i-1]} followed by {hours[i]} at rows {row_indices[i-1]+1}-{row_indices[i]+1}")

        same_day_columns = ['Sjutra praznik', 'Dan u nedelji', 'Dan u mjesecu', 'Mjesec']

        temp_columns = [col for col in EXPECTED_COLUMNS if col.startswith('Temp.')]
        same_day_columns.extend(temp_columns)

        for col in same_day_columns:
            if col in df.columns:
                day_values = []
                for row_idx in row_indices:
                    val = df.iloc[row_idx][col]
                    if pd.notna(val) and val != '':
                        day_values.append(val)

                if len(day_values) > 1:
                    unique_values = list(set(day_values))
                    if len(unique_values) > 1:
                        errors.append(f"Day {day_number}: '{col}' has inconsistent values within the same day: {unique_values} (rows {[r+1 for r in row_indices]})")

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
    """Generate predictions using specified models"""
    try:
        if 'user' not in session:
            return jsonify({'success': False, 'message': 'Not authenticated'}), 401

        data = request.get_json()
        file_id = data.get('fileId')
        prediction_period = data.get('predictionPeriod', 24)
        prediction_type = data.get('predictionType', 'country-level')
        model_types = data.get('modelTypes', ['nbeats'])

        if not file_id or file_id not in uploaded_files:
            return jsonify({'success': False, 'message': 'Invalid or missing file'}), 400

        if not model_types or len(model_types) == 0:
            return jsonify({'success': False, 'message': 'At least one model must be selected'}), 400

        file_info = uploaded_files[file_id]
        file_path = file_info['path']

        if file_path.lower().endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path, engine='openpyxl')

        if not ml_client.health_check():
            return jsonify({
                'success': False,
                'message': 'ML prediction service is currently unavailable. Please try again later.',
                'service_status': 'offline'
            }), 503

        consumption_data = pd.to_numeric(df['Prethodna 24h'], errors='coerce').tolist()

        start_hour = 0
        sat_values = df['Sat'][df['Sat'].notna() & (df['Sat'] != '')]
        if len(sat_values) > 0:
            start_hour = int(sat_values.iloc[0])

        hour_labels = []
        for i in range(24):
            hour = (start_hour + i) % 24
            hour_labels.append(f"{hour:02d}:00")

        try:
            ml_data = ml_client.prepare_data_for_ml_api(df)
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Failed to prepare data for ML model: {str(e)}'
            }), 400

        all_predictions = {}
        total_processing_time = 0

        for model_type in model_types:
            prediction_result = ml_client.make_prediction(ml_data, model_type)

            if not prediction_result['success']:
                return jsonify({
                    'success': False,
                    'message': f"ML prediction failed for {model_type}: {prediction_result['error']}",
                    'service_status': 'error'
                }), 500

            raw_predictions = prediction_result['predictions']

            if len(raw_predictions) != 24:
                return jsonify({
                    'success': False,
                    'message': f'Invalid prediction length for {model_type}: expected 24, got {len(raw_predictions)}'
                }), 500

            predictions_array = np.array(raw_predictions)
            confidence_min = (predictions_array * 0.97).tolist()
            confidence_max = (predictions_array * 1.03).tolist()

            metadata = prediction_result.get('metadata', {})
            processing_time = metadata.get('processing_time', 0)
            total_processing_time += processing_time

            all_predictions[model_type] = {
                'values': raw_predictions,
                'confidence_min': confidence_min,
                'confidence_max': confidence_max,
                'processing_time': processing_time
            }

        prediction_id = str(uuid.uuid4())
        prediction_results[prediction_id] = {
            'file_id': file_id,
            'model_types': model_types,
            'predictions': all_predictions,
            'timestamp': datetime.now(),
            'user_id': session['user']['username']
        }

        response_data = {
            'predictionId': prediction_id,
            'hours': hour_labels,
            'historical': consumption_data,
            'modelTypes': model_types,
            'predictions': all_predictions,
            'startHour': start_hour,
            'totalProcessingTime': total_processing_time,
            'serviceStatus': 'online'
        }

        return jsonify({
            'success': True,
            'data': response_data
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Prediction failed: {str(e)}',
            'service_status': 'error'
        }), 500


@api_bp.route('/export', methods=['POST'])
@limiter.limit("20 per hour")  # Max 20 exports per hour
def export_predictions():
    """Export prediction results in specified format"""
    try:
        if 'user' not in session:
            return jsonify({'success': False, 'message': 'Not authenticated'}), 401

        data = request.get_json()
        prediction_data = data.get('data')
        format_type = data.get('format', 'csv')

        if not prediction_data:
            return jsonify({'success': False, 'message': 'No data to export'}), 400

        start_hour = prediction_data.get('startHour', 0)

        hour_labels = []
        for i in range(24):
            hour = (start_hour + i) % 24
            hour_labels.append(f"{hour:02d}:00")

        historical_data = prediction_data.get('historical', [])
        formatted_historical = [f"{val:.4f}" if val is not None else "--" for val in historical_data]

        predictions = prediction_data.get('predictions', {})
        model_types = prediction_data.get('modelTypes', [])

        export_data = {
            'Sat': hour_labels,
            'Prethodna 24h': formatted_historical
        }

        for model_type in model_types:
            model_predictions = predictions.get(model_type, {})

            prediction_values = model_predictions.get('values', [])
            formatted_predictions = [f"{val:.4f}" if val is not None else "--" for val in prediction_values]
            export_data[f'Predikcija {model_type.upper()}'] = formatted_predictions

            confidence_min = model_predictions.get('confidence_min', [])
            confidence_max = model_predictions.get('confidence_max', [])
            confidence_intervals = []

            for min_val, max_val in zip(confidence_min, confidence_max):
                if min_val is not None and max_val is not None:
                    confidence_intervals.append(f"{min_val:.4f}-{max_val:.4f}")
                else:
                    confidence_intervals.append("--")

            export_data[f'Ocekivani interval odstupanja {model_type.upper()}'] = confidence_intervals

        export_df = pd.DataFrame(export_data)

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
