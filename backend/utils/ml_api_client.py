import requests
import numpy as np
import pandas as pd
from typing import Dict
from backend.config import Config
import logging

logger = logging.getLogger(__name__)

class MLAPIClient:
    """Client for communicating with the FastAPI ML service"""

    def __init__(self):
        self.base_url = Config.ML_API_BASE_URL
        self.timeout = Config.ML_API_TIMEOUT

    def health_check(self) -> bool:
        """Check if the ML API service is available"""
        try:
            response = requests.get(
                f"{self.base_url}/healthz",
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("status") == "ok"

            return False

        except Exception as e:
            logger.error(f"ML API health check failed: {e}")
            return False

    def prepare_data_for_ml_api(self, df: pd.DataFrame) -> np.ndarray:
        """
        Convert uploaded Excel data to 24x24 numpy array format expected by ML API

        Args:
            df: DataFrame with 24 rows and 24 columns from Excel

        Returns:
            np.ndarray: 24x24 array ready for ML API
        """
        try:
            if len(df) != 24 or len(df.columns) != 24:
                raise ValueError(f"Expected 24x24 data, got {len(df)}x{len(df.columns)}")

            numeric_data = []

            for _, row in df.iterrows():
                numeric_row = []
                for value in row:
                    try:
                        if pd.isna(value) or value == '' or value is None:
                            numeric_row.append(0.0)
                        else:
                            numeric_row.append(float(value))
                    except (ValueError, TypeError):
                        numeric_row.append(0.0)

                numeric_data.append(numeric_row)

            data_array = np.array(numeric_data, dtype=np.float32)

            if data_array.shape != (24, 24):
                raise ValueError(f"Data conversion resulted in shape {data_array.shape}, expected (24, 24)")

            logger.info(f"Successfully prepared data for ML API: shape {data_array.shape}")
            return data_array

        except Exception as e:
            logger.error(f"Error preparing data for ML API: {e}")
            raise

    def make_prediction(self, data: np.ndarray, model_type: str) -> Dict:
        """
        Make prediction using the specified model

        Args:
            data: 24x24 numpy array
            model_type: 'nbeats', 'cnn-nbeats', or 'nbeats-cnn'

        Returns:
            Dict with prediction results
        """
        try:
            if data.shape != (24, 24):
                raise ValueError(f"Input data must be 24x24, got {data.shape}")

            endpoint_map = {
                'nbeats': '/predict/nbeats',
                'cnn-nbeats': '/predict/cnn-nbeats',
                'nbeats-cnn': '/predict/nbeats-cnn'
            }

            if model_type not in endpoint_map:
                raise ValueError(f"Unknown model type: {model_type}")

            endpoint = endpoint_map[model_type]
            url = f"{self.base_url}{endpoint}"

            payload = {
                "data": data.tolist()
            }

            logger.info(f"Making prediction request to {url} with model {model_type}")

            response = requests.post(
                url,
                json=payload,
                timeout=self.timeout,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code == 200:
                result = response.json()

                if result.get('success', False):
                    forecast = result.get('forecast', [])
                    metadata = result.get('metadata', {})

                    logger.info(f"Prediction successful: {len(forecast)} values returned")

                    return {
                        'success': True,
                        'predictions': forecast,
                        'metadata': metadata,
                        'model_type': model_type
                    }
                else:
                    error_msg = result.get('error_message', 'Unknown error from ML API')
                    logger.error(f"ML API returned error: {error_msg}")
                    return {
                        'success': False,
                        'error': error_msg,
                        'model_type': model_type
                    }
            else:
                logger.error(f"ML API HTTP error: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}: {response.text[:200]}',
                    'model_type': model_type
                }

        except requests.exceptions.Timeout:
            logger.error(f"ML API timeout after {self.timeout} seconds")
            return {
                'success': False,
                'error': f'Request timeout after {self.timeout} seconds',
                'model_type': model_type
            }
        except requests.exceptions.ConnectionError:
            logger.error("Cannot connect to ML API service")
            return {
                'success': False,
                'error': 'Cannot connect to ML API service',
                'model_type': model_type
            }
        except Exception as e:
            logger.error(f"Unexpected error in ML API call: {e}")
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}',
                'model_type': model_type
            }


ml_client = MLAPIClient()
