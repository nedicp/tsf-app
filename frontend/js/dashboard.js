// Dashboard JavaScript
//
// TODO: Excel File Format - STRICT VALIDATION REQUIRED
// =====================================================
//
// Expected Excel structure (EXACT columns required):
// Row 1 (Header): | Sjutra praznik | Dan u nedelji | Dan u mjesecu | Mjesec | Sat | Temp. min Pg | Temp. max Pg | Temp. sr Pg | Temp. min Nk | Temp. max Nk | Temp. sr Nk | Temp. min Pv | Temp. max Pv | Temp. sr Pv | Temp. min Br | Temp. max Br | Temp. sr Br | Temp. min Ul | Temp. max Ul | Temp. sr Ul | Temp. min Ct | Temp. max Ct | Temp. sr Ct | Prethodna 24h |
// Rows 2-25 (Data): 24 rows of actual data values
//
// VALIDATION RULES (STRICTLY ENFORCED):
//
// 1. Sjutra praznik (Tomorrow Holiday):
//    - Can contain 1-2 values OR all 24 values
//    - If predicting for same day: 1 value
//    - If predicting for next day: 2 values (repeated for same day)
//    - Can also have all 24 values filled in
//
// 2. Sat (Hour):
//    - Can contain ONLY first value OR all 24 values
//    - When hour switches from 23 to 0, increment day/month based on first values
//
// 3. Dan u mjesecu (Day of Month):
//    - Can contain ONLY first value OR all values
//    - Values depend on hour progression
//
// 4. Mjesec (Month):
//    - Can contain ONLY first value OR all values
//    - Values depend on hour progression
//
// 5. Dan u nedelji (Day of Week):
//    - Can contain ONLY first value OR all values
//    - Values depend on hour progression
//
// 6. Temperature columns (18 columns total):
//    - Can contain 1-2 values per row OR all values
//    - Values for the SAME DAY must be IDENTICAL
//    - Columns: min/max/sr for Pg, Nk, Pv, Br, Ul, Ct
//
// 7. Prethodna 24h (Previous 24h consumption):
//    - MUST contain ALL 24 values (MWh per hour)
//    - NO missing values allowed
//
// Table dimensions: EXACTLY 25 rows x 24 columns (1 header row + 24 data rows)
// =============================================================================

class DashboardManager {
    constructor() {
        this.currentUser = null;
        this.uploadedFile = null;
        this.uploadedData = null;
        this.predictionResults = null;
        this.chart = null;

        // Expected column structure
        this.expectedColumns = [
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
        ];

        this.initialize();
    }

    async initialize() {
        await this.checkAuthentication();
        this.initializeEventListeners();
    }

    async checkAuthentication() {
        try {
            const response = await fetch('/auth/check-session');
            const data = await response.json();

            if (!data.authenticated) {
                window.location.href = '/index.html';
                return;
            }

            this.currentUser = data.user;
            this.loadUserInfo(); // Load user info after authentication completes
        } catch (error) {
            console.error('Authentication check failed:', error);
            window.location.href = '/index.html';
        }
    }

    initializeEventListeners() {
        // Logout functionality
        const logoutBtn = document.getElementById('logoutBtn');
        logoutBtn.addEventListener('click', this.handleLogout.bind(this));

        // File upload functionality
        this.initializeFileUpload();

        // Prediction controls
        this.initializePredictionControls();

        // Chart controls
        this.initializeChartControls();

        // Export functionality
        this.initializeExportControls();
    }

    initializeFileUpload() {
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const browseBtn = document.getElementById('browseBtn');
        const removeFileBtn = document.getElementById('removeFileBtn');

        // Drag and drop events
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('drag-over');
        });

        uploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFileSelection(files[0]);
            }
        });

        // Click to upload
        uploadArea.addEventListener('click', () => {
            if (!this.uploadedFile) {
                fileInput.click();
            }
        });

        browseBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            fileInput.click();
        });

        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.handleFileSelection(e.target.files[0]);
            }
        });

        // Remove file
        removeFileBtn.addEventListener('click', () => {
            this.removeFile();
        });
    }

    initializePredictionControls() {
        const predictBtn = document.getElementById('predictBtn');
        predictBtn.addEventListener('click', () => {
            this.generatePredictions();
        });
    }

    initializeChartControls() {
        const chartBtns = document.querySelectorAll('.chart-btn');
        chartBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                // Remove active class from all buttons
                chartBtns.forEach(b => b.classList.remove('active'));
                // Add active class to clicked button
                btn.classList.add('active');

                const viewType = btn.dataset.view || btn.dataset.chart;
                if (this.predictionResults) {
                    this.switchView(viewType);
                }
            });
        });
    }

    switchView(viewType) {
        const chartCanvas = document.getElementById('predictionChart');
        const tableDiv = document.getElementById('predictionTable');

        if (viewType === 'table') {
            chartCanvas.style.display = 'none';
            tableDiv.style.display = 'block';
            this.createPredictionTable(this.predictionResults);
        } else {
            // Ensure we destroy any existing chart first
            if (this.chart) {
                this.chart.destroy();
                this.chart = null;
            }
            tableDiv.style.display = 'none';
            chartCanvas.style.display = 'block';
            // Force canvas to reset and recreate chart
            setTimeout(() => {
                this.createChart(this.predictionResults);
            }, 50);
        }
    }

    createPredictionTable(data) {
        const tableDiv = document.getElementById('predictionTable');

        // Use actual prediction data from backend
        const hours = data.hours || Array.from({length: 24}, (_, i) => `${i.toString().padStart(2, '0')}:00`);
        const predictions = data.predictions || [];
        const confidenceMin = data.confidenceMin || [];
        const confidenceMax = data.confidenceMax || [];
        const historical = data.historical || [];

        // Create table data
        const tableData = hours.map((hour, index) => ({
            hour: hour,
            historical: historical[index] || 0,
            predicted: predictions[index] || 0,
            confidenceMin: confidenceMin[index] || 0,
            confidenceMax: confidenceMax[index] || 0
        }));

        const table = document.createElement('table');
        table.innerHTML = `
            <thead>
                <tr>
                    <th>Hour</th>
                    <th>Previous 24h (MWh)</th>
                    <th>Next 24h (MWh)</th>
                    <th>Confidence Range (±3%)</th>
                </tr>
            </thead>
            <tbody>
                ${tableData.map(row => `
                    <tr>
                        <td class="hour-cell">${row.hour}</td>
                        <td class="value-cell">${row.historical.toFixed(3)}</td>
                        <td class="value-cell">${row.predicted.toFixed(3)}</td>
                        <td class="confidence-cell">${row.confidenceMin.toFixed(3)} - ${row.confidenceMax.toFixed(3)}</td>
                    </tr>
                `).join('')}
            </tbody>
        `;

        tableDiv.innerHTML = '';
        tableDiv.appendChild(table);
    }

    loadUserInfo() {
        const userName = document.getElementById('userName');
        userName.innerHTML = `<i class="fas fa-user"></i> ${this.currentUser.username}`;
    }

    initializeExportControls() {
        document.getElementById('exportCSV').addEventListener('click', () => {
            this.exportData('csv');
        });
    }

    handleFileSelection(file) {
        // Validate file
        if (!this.validateFile(file)) {
            return;
        }

        this.uploadedFile = file;
        this.showFileInfo(file);
        this.uploadFile(file);
    }

    validateFile(file) {
        const maxSize = 10 * 1024 * 1024; // 10MB
        const allowedTypes = [
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-excel'
        ];

        if (file.size > maxSize) {
            this.showNotification('File size must be less than 10MB', 'error');
            return false;
        }

        if (!allowedTypes.includes(file.type)) {
            this.showNotification('Please upload an Excel file (.xlsx or .xls) with the required 24×24 structure', 'error');
            return false;
        }

        // Show strict format requirements
        this.showNotification('Validating Excel structure... File must have exactly 25 rows × 24 columns (1 header + 24 data rows)', 'info');

        return true;
    }

    showFileInfo(file) {
        const fileName = document.getElementById('fileName');
        const fileSize = document.getElementById('fileSize');
        const fileInfo = document.getElementById('fileInfo');

        fileName.textContent = file.name;
        fileSize.textContent = this.formatFileSize(file.size);
        fileInfo.style.display = 'block';
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    async uploadFile(file) {
        const uploadStatus = document.getElementById('uploadStatus');
        const progressFill = document.getElementById('progressFill');
        const statusText = document.getElementById('statusText');

        uploadStatus.style.display = 'block';

        const formData = new FormData();
        formData.append('file', file);

        try {
            // Simulate upload progress
            this.simulateProgress(progressFill, statusText);

            // Upload to backend
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                progressFill.style.width = '100%';
                statusText.textContent = 'Upload complete!';

                setTimeout(() => {
                    uploadStatus.style.display = 'none';
                    this.processUploadedData(result.data);
                }, 1000);
            } else {
                throw new Error(result.message || 'Upload failed');
            }
        } catch (error) {
            console.error('Upload error:', error);
            statusText.textContent = 'Upload failed. Please try again.';
            statusText.style.color = '#ef4444';

            // Show detailed error message as a notification - make sure it's persistent
            console.log('Showing error notification:', error.message);
            this.showNotification(error.message, 'error');

            setTimeout(() => {
                uploadStatus.style.display = 'none';
                this.removeFile();
            }, 2000);
        }
    }



    simulateProgress(progressFill, statusText) {
        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.random() * 15;
            if (progress > 90) {
                clearInterval(interval);
                progressFill.style.width = '90%';
                statusText.textContent = 'Processing file...';
                return;
            }
            progressFill.style.width = progress + '%';
            statusText.textContent = `Uploading... ${Math.round(progress)}%`;
        }, 200);
    }

    processUploadedData(data) {
        // Backend has already validated the data, so trust the backend validation
        // Check if data has the expected structure from backend
        if (!data || !data.preview || !Array.isArray(data.preview)) {
            this.showNotification('Invalid data structure received from server', 'error');
            this.removeFile();
            return;
        }

        this.uploadedData = data;
        this.showDataPreview(data);
        this.updateStatistics(data);
        this.enablePredictionControls();
        // Remove the automatic success notification - let user focus on the data
    }

    // This entire method is now redundant since the backend handles all validation and data filling.
    // Kept here for documentation purposes.
    validateExcelStructure(data) {
        return { isValid: true, errors: [] };
    }

    // This method is also redundant.
    validateDataPatterns(rows) {
        return { errors: [] };
    }

    // This method is also redundant.
    validateSameDayTemperatures(rows, columnName) {
        return { isValid: true };
    }

    showDataPreview(data) {
        const previewContent = document.getElementById('previewContent');

        if (!data || !data.preview || data.preview.length === 0) {
            previewContent.innerHTML = `
                <div class="no-data">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>No data found in the uploaded file</p>
                </div>
            `;
            return;
        }

        // Create table with validation status indicators
        const table = document.createElement('table');
        table.className = 'preview-table';
        const thead = document.createElement('thead');
        const tbody = document.createElement('tbody');

        // Headers with validation indicators
        const headerRow = document.createElement('tr');
        this.expectedColumns.forEach(columnName => {
            const th = document.createElement('th');
            th.innerHTML = `
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span>${columnName}</span>
                    <i class="fas fa-check-circle" style="color: #10b981; font-size: 0.75rem;" title="Valid column"></i>
                </div>
            `;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);

        // Data rows (show all 24 rows)
        data.preview.forEach((row, index) => {
            const tr = document.createElement('tr');
            this.expectedColumns.forEach(columnName => {
                const td = document.createElement('td');
                const value = row[columnName];

                // Highlight missing required values
                if ((columnName === 'Prethodna 24h') && (value === null || value === undefined || value === '')) {
                    td.innerHTML = `<span style="color: #ef4444;">MISSING</span>`;
                } else if (value === null || value === undefined || value === '') {
                    td.textContent = '--';
                } else {
                    td.textContent = value;
                }

                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });

        table.appendChild(thead);
        table.appendChild(tbody);
        previewContent.innerHTML = '';
        previewContent.appendChild(table);

        // No longer showing validation summary - let the notification handle success messages
    }

    updateStatistics(data) {
        // TODO: When implementing with real uploaded data, extract basic statistics
        // Expected data structure:
        // data.statistics = {
        //     avgConsumption: 1250.5,
        //     peakConsumption: 1850.2,
        //     dateRange: 30,
        //     recordCount: 720
        // }

        // For now, just show that data was processed
        console.log('Data statistics updated for uploaded file:', data);
    }

    enablePredictionControls() {
        const predictBtn = document.getElementById('predictBtn');
        predictBtn.disabled = false;
    }

    retryPrediction() {
        // Automatically trigger prediction generation when user clicks "Try Again"
        console.log('Retrying prediction after service warning...');
        this.generatePredictions();
    }

    async checkMLServiceHealth() {
        try {
            const response = await fetch('/api/ml-service/health');
            const result = await response.json();
            return result.ml_service === 'online';
        } catch (error) {
            console.error('ML service health check failed:', error);
            return false;
        }
    }

    async generatePredictions() {
        if (!this.uploadedData) {
            this.showNotification('Please upload data first', 'error');
            return;
        }

        // Check ML service health before prediction
        const predictBtn = document.getElementById('predictBtn');
        const originalText = predictBtn.innerHTML;

        predictBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Checking service...';
        predictBtn.disabled = true;

        const isServiceHealthy = await this.checkMLServiceHealth();

        if (!isServiceHealthy) {
            this.showServiceDownWarning();
            predictBtn.innerHTML = originalText;
            predictBtn.disabled = false;
            return;
        }

        predictBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating predictions...';

        try {
            const predictionPeriod = document.getElementById('predictionPeriod').value;
            const modelType = document.getElementById('modelType').value;

            const response = await fetch('/api/predict', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    fileId: this.uploadedData.fileId,
                    predictionPeriod: parseInt(predictionPeriod),
                    modelType: modelType
                })
            });

            const result = await response.json();

            if (result.success) {
                this.predictionResults = result.data;
                this.displayPredictionResults(result.data);
                this.enableExportControls();

                const processingTime = result.data.processingTime || 0;
                this.showNotification(
                    `Predictions generated successfully in ${processingTime.toFixed(2)}s using ${modelType.toUpperCase()}!`,
                    'success'
                );
            } else {
                if (result.service_status === 'offline') {
                    this.showServiceDownWarning();
                } else {
                    throw new Error(result.message || 'Prediction failed');
                }
            }
        } catch (error) {
            console.error('Prediction error:', error);
            this.showNotification('Failed to generate predictions. Please try again.', 'error');
        } finally {
            predictBtn.innerHTML = originalText;
            predictBtn.disabled = false;
        }
    }

    showServiceDownWarning() {
        // Create a prominent warning overlay
        const overlay = document.createElement('div');
        overlay.className = 'service-warning-overlay';
        overlay.innerHTML = `
            <div class="service-warning-content">
                <div class="service-warning-icon">
                    <i class="fas fa-exclamation-triangle"></i>
                </div>
                <h3>ML Service Temporarily Unavailable</h3>
                <p>The machine learning prediction service is currently offline or unreachable.</p>
                <p>Please check:</p>
                <ul>
                    <li>Your internet connection</li>
                    <li>Contact system administrator if problem persists</li>
                </ul>
                <div class="service-warning-actions">
                    <button class="retry-btn" onclick="window.dashboardManager.retryPrediction(); this.parentElement.parentElement.parentElement.remove()">
                        <i class="fas fa-redo"></i> Try Again
                    </button>
                    <button class="dismiss-btn" onclick="this.parentElement.parentElement.parentElement.remove()">
                        <i class="fas fa-times"></i> Dismiss
                    </button>
                </div>
            </div>
        `;

        // Add styles for the warning overlay
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            backdrop-filter: blur(5px);
        `;

        document.body.appendChild(overlay);

        // Auto-remove after 10 seconds
        setTimeout(() => {
            if (overlay.parentElement) {
                overlay.remove();
            }
        }, 10000);
    }

    displayPredictionResults(data) {
        // Update prediction statistics
        this.updatePredictionStatistics(data);

        // Show chart by default
        this.createChart(data);

        // Hide no-results message
        document.getElementById('noResults').style.display = 'none';
        document.getElementById('predictionChart').style.display = 'block';
    }

    updatePredictionStatistics(data) {
        // Calculate statistics from actual prediction data
        const predictions = data.predictions || [];
        const hours = data.hours || Array.from({length: 24}, (_, i) => `${i.toString().padStart(2, '0')}:00`);

        if (predictions.length === 0) {
            // No data available
            document.getElementById('avgPredictionConsumption').textContent = '--';
            document.getElementById('dailyTotalConsumption').textContent = '--';
            document.getElementById('peakPredictionConsumption').textContent = '--';
            document.getElementById('peakHour').textContent = '--';
            document.getElementById('minPredictionConsumption').textContent = '--';
            document.getElementById('minHour').textContent = '--';
            return;
        }

        // Calculate statistics
        const total = predictions.reduce((sum, val) => sum + val, 0);
        const average = total / predictions.length;
        const peakValue = Math.max(...predictions);
        const peakIndex = predictions.indexOf(peakValue);
        const peakHour = hours[peakIndex];
        const minValue = Math.min(...predictions);
        const minIndex = predictions.indexOf(minValue);
        const minHour = hours[minIndex];

        // Update UI
        document.getElementById('avgPredictionConsumption').textContent =
            `${average.toFixed(3)} MWh`;
        document.getElementById('dailyTotalConsumption').textContent =
            `${total.toFixed(3)} MWh`;
        document.getElementById('peakPredictionConsumption').textContent =
            `${peakValue.toFixed(3)} MWh`;
        document.getElementById('peakHour').textContent =
            `at ${peakHour}`;
        document.getElementById('minPredictionConsumption').textContent =
            `${minValue.toFixed(3)} MWh`;
        document.getElementById('minHour').textContent =
            `at ${minHour}`;
    }



    createChart(data) {
        const ctx = document.getElementById('predictionChart').getContext('2d');

        // Destroy existing chart if it exists
        if (this.chart) {
            this.chart.destroy();
        }

        // Use actual prediction data from backend
        const chartData = {
            hours: data.hours || Array.from({length: 24}, (_, i) => `${i.toString().padStart(2, '0')}:00`),
            predictions: data.predictions || [],
            confidenceMin: data.confidenceMin || [],
            confidenceMax: data.confidenceMax || [],
            historical: data.historical || []
        };

        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: chartData.hours,
                datasets: [
                    {
                        label: 'Previous 24h',
                        data: chartData.historical,
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        borderWidth: 2,
                        fill: false,
                        pointBackgroundColor: '#3b82f6',
                        pointBorderColor: '#ffffff',
                        pointBorderWidth: 2,
                        pointRadius: 3,
                        pointHoverRadius: 5
                    },
                    {
                        label: 'Confidence Range (±3%)',
                        data: chartData.confidenceMin,
                        backgroundColor: 'rgba(107, 114, 128, 0.1)',
                        borderColor: 'transparent',
                        fill: '+2'
                    },
                    {
                        label: 'Confidence Range (±3%)',
                        data: chartData.confidenceMax,
                        backgroundColor: 'rgba(107, 114, 128, 0.1)',
                        borderColor: 'transparent',
                        fill: false
                    },
                    {
                        label: 'Next 24h',
                        data: chartData.predictions,
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        borderWidth: 3,
                        fill: false,
                        pointBackgroundColor: '#10b981',
                        pointBorderColor: '#ffffff',
                        pointBorderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    legend: {
                        labels: {
                            color: '#e2e8f0',
                            filter: (legendItem, chartData) => {
                                // Show historical and predicted data, hide confidence bands
                                return legendItem.text === 'Next 24h' ||
                                       legendItem.text === 'Previous 24h';
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const datasetIndex = context.datasetIndex;
                                const value = context.parsed.y;

                                if (datasetIndex === 0) { // Previous 24h data
                                    return `Previous 24h: ${value.toFixed(2)} MWh`;
                                } else if (datasetIndex === 3) { // Next 24h line
                                    const hourIndex = context.dataIndex;
                                    const minValue = chartData.confidenceMin[hourIndex];
                                    const maxValue = chartData.confidenceMax[hourIndex];
                                    return [
                                        `Next 24h: ${value.toFixed(2)} MWh`,
                                        `Confidence Range: ${minValue?.toFixed(2)} - ${maxValue?.toFixed(2)} MWh`
                                    ];
                                }
                                return null;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Hour of Day',
                            color: '#94a3b8'
                        },
                        ticks: {
                            color: '#94a3b8'
                        },
                        grid: {
                            color: 'rgba(71, 85, 105, 0.3)'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Consumption (MWh)',
                            color: '#94a3b8'
                        },
                        ticks: {
                            color: '#94a3b8',
                            callback: function(value) {
                                return value.toFixed(1) + ' MWh';
                            }
                        },
                        grid: {
                            color: 'rgba(71, 85, 105, 0.3)'
                        }
                    }
                }
            }
        });
    }



    enableExportControls() {
        document.getElementById('exportCSV').disabled = false;
    }

    async exportData(format) {
        if (!this.predictionResults) {
            this.showNotification('No data to export', 'error');
            return;
        }

        try {
            const response = await fetch('/api/export', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    data: this.predictionResults,
                    format: format
                })
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `predictions.${format}`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);

                this.showNotification(`Data exported as ${format.toUpperCase()}`, 'success');
            } else {
                throw new Error('Export failed');
            }
        } catch (error) {
            console.error('Export error:', error);
            this.showNotification('Export failed. Please try again.', 'error');
        }
    }

    removeFile() {
        this.uploadedFile = null;
        this.uploadedData = null;
        this.predictionResults = null;

        // Reset file input
        document.getElementById('fileInput').value = '';
        document.getElementById('fileInfo').style.display = 'none';
        document.getElementById('uploadStatus').style.display = 'none';

        // Reset preview
        document.getElementById('previewContent').innerHTML = `
            <div class="no-data">
                <i class="fas fa-table"></i>
                <p>Upload a file to preview your data</p>
            </div>
        `;

        // Reset statistics
        document.getElementById('avgPredictionConsumption').textContent = '--';
        document.getElementById('dailyTotalConsumption').textContent = '--';
        document.getElementById('peakPredictionConsumption').textContent = '--';
        document.getElementById('peakHour').textContent = '--';
        document.getElementById('minPredictionConsumption').textContent = '--';
        document.getElementById('minHour').textContent = '--';

        // Reset controls
        document.getElementById('predictBtn').disabled = true;

        // Reset export button
        document.getElementById('exportCSV').disabled = true;

        // Reset chart and table
        if (this.chart) {
            this.chart.destroy();
            this.chart = null;
        }
        document.getElementById('noResults').style.display = 'flex';
        document.getElementById('predictionChart').style.display = 'none';
        document.getElementById('predictionTable').style.display = 'none';

        // Reset view buttons
        document.querySelectorAll('.chart-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        // Set chart view as default active
        const chartBtn = document.querySelector('.chart-btn[data-chart="line"]') || document.querySelector('.chart-btn:first-child');
        if (chartBtn) {
            chartBtn.classList.add('active');
        }
    }

    showNotification(message, type = 'info') {
        console.log(`Creating notification: type="${type}", message="${message}"`);

        // Remove any existing notifications of the same type
        const existingNotifications = document.querySelectorAll(`.notification-${type}`);
        existingNotifications.forEach(notif => notif.remove());

        // For error messages (especially validation errors), show as centered overlay
        if (type === 'error' && message.length > 100) {
            this.showCenteredErrorMessage(message);
            return;
        }

        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;

        // Force errors to be persistent - extra safety check
        const isPersistent = type === 'error' || type === 'warning';

        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
                <span class="notification-message">${message}</span>
            </div>
            ${isPersistent ? '<button class="notification-close" onclick="this.parentElement.remove()" title="Click to dismiss"><i class="fas fa-times"></i></button>' : ''}
        `;

        // Add styles - make errors more prominent
        const backgroundColor = type === 'error' ? 'rgba(239, 68, 68, 0.98)' :
                              type === 'success' ? 'rgba(16, 185, 129, 0.95)' :
                              'rgba(59, 130, 246, 0.95)';

        const borderColor = type === 'error' ? 'rgba(239, 68, 68, 0.5)' :
                           type === 'success' ? 'rgba(16, 185, 129, 0.3)' :
                           'rgba(59, 130, 246, 0.3)';

        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${backgroundColor};
            color: white;
            padding: 1.25rem 1.5rem;
            border-radius: 12px;
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 1rem;
            z-index: 9999;
            backdrop-filter: blur(20px);
            animation: slideIn 0.3s ease;
            max-width: 500px;
            min-width: 350px;
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
            border: 2px solid ${borderColor};
            font-weight: ${type === 'error' ? '500' : '400'};
        `;

        document.body.appendChild(notification);
        console.log(`Notification added to DOM. Type: ${type}, Persistent: ${isPersistent}`);

        // ONLY auto-remove success and info messages - NEVER errors or warnings
        if (type === 'success' || type === 'info') {
            console.log('Setting auto-removal timer for success/info message');
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.style.animation = 'slideOut 0.3s ease';
                    setTimeout(() => {
                        if (notification.parentElement) {
                            notification.remove();
                        }
                    }, 300);
                }
            }, 3000);
        } else {
            console.log('Error/warning notification will persist until manually dismissed');
        }

        // For persistent notifications, add click handler for close button
        if (isPersistent) {
            const closeBtn = notification.querySelector('.notification-close');
            if (closeBtn) {
                closeBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    console.log('Manually closing notification');
                    notification.remove();
                });
            }
        }
    }

    showCenteredErrorMessage(message) {
        // Create a centered error overlay for long validation messages
        const overlay = document.createElement('div');
        overlay.className = 'error-message-overlay';
        overlay.innerHTML = `
            <div class="error-message-content">
                <div class="error-message-header">
                    <i class="fas fa-exclamation-triangle"></i>
                    <h3>Validation Error</h3>
                </div>
                <div class="error-message-body">
                    <p>${message}</p>
                </div>
                <div class="error-message-actions">
                    <button class="error-dismiss-btn" onclick="this.parentElement.parentElement.parentElement.remove()">
                        <i class="fas fa-times"></i> Close
                    </button>
                </div>
            </div>
        `;

        // Add styles for the error overlay
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            backdrop-filter: blur(5px);
        `;

        document.body.appendChild(overlay);
    }

    loadUserInfo() {
        if (!this.currentUser) {
            console.log('No user data available');
            return;
        }

        // console.log('Loading user info for:', this.currentUser);

        try {
            // Update navigation - show username or name
            const userName = document.getElementById('userName');
            if (userName) {
                const displayName = this.currentUser.name || this.currentUser.username || 'User';
                userName.textContent = displayName;
                // console.log('Updated userName element with:', displayName);
            } else {
                console.log('userName element not found');
            }

            // Update user info section (these elements might not exist in current HTML)
            const userEmail = document.getElementById('userEmail');
            if (userEmail) {
                userEmail.textContent = this.currentUser.email;
            }

            const userRole = document.getElementById('userRole');
            if (userRole) {
                userRole.textContent = this.currentUser.role.charAt(0).toUpperCase() + this.currentUser.role.slice(1);
            }

            const loginTime = document.getElementById('loginTime');
            if (loginTime) {
                loginTime.textContent = new Date().toLocaleString();
            }
        } catch (error) {
            console.error('Error loading user info:', error);
        }
    }

    async handleLogout() {
        try {
            const response = await fetch('/auth/logout', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            const data = await response.json();

            if (data.success) {
                // Clear any cached data
                sessionStorage.clear();
                localStorage.clear();

                // Redirect to login
                window.location.href = data.redirect || '/index.html';
            } else {
                console.error('Logout failed:', data.message);
                // Force redirect anyway
                window.location.href = '/index.html';
            }
        } catch (error) {
            console.error('Logout error:', error);
            // Force redirect on error
            window.location.href = '/index.html';
        }
    }
}

// Add notification animations and styles to document
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }

    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }

    .notification-content {
        display: flex;
        align-items: flex-start;
        gap: 0.75rem;
        flex: 1;
    }

    .notification-message {
        flex: 1;
        line-height: 1.4;
        word-wrap: break-word;
    }

    .notification-close {
        background: none;
        border: none;
        color: white;
        cursor: pointer;
        padding: 0.25rem;
        border-radius: 4px;
        display: flex;
        align-items: center;
        justify-content: center;
        min-width: 24px;
        height: 24px;
        opacity: 0.8;
        transition: all 0.2s ease;
        margin-top: 2px;
    }

    .notification-close:hover {
        opacity: 1;
        background: rgba(255, 255, 255, 0.2);
        transform: scale(1.1);
    }

    .notification-close i {
        font-size: 0.875rem;
    }

    .notification-error {
        animation: pulse 0.5s ease-in-out;
    }

    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.02); }
        100% { transform: scale(1); }
    }

    /* Service Warning Overlay Styles */
    .service-warning-content {
        background: linear-gradient(135deg, #dc2626, #b91c1c);
        color: white;
        padding: 2rem;
        border-radius: 16px;
        max-width: 500px;
        width: 90%;
        text-align: center;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        animation: warningSlideIn 0.4s ease-out;
    }

    @keyframes warningSlideIn {
        from { transform: scale(0.8); opacity: 0; }
        to { transform: scale(1); opacity: 1; }
    }

    .service-warning-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
        color: #fbbf24;
        animation: warningPulse 2s ease-in-out infinite;
    }

    @keyframes warningPulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.1); }
    }

    .service-warning-content h3 {
        font-size: 1.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }

    .service-warning-content p {
        margin-bottom: 1rem;
        opacity: 0.9;
    }

    .service-warning-content ul {
        text-align: left;
        margin: 1rem 0;
        padding-left: 1.5rem;
    }

    .service-warning-content li {
        margin-bottom: 0.5rem;
        opacity: 0.9;
    }

    .service-warning-actions {
        margin-top: 2rem;
        display: flex;
        gap: 1rem;
        justify-content: center;
    }

    .retry-btn, .dismiss-btn {
        padding: 0.75rem 1.5rem;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .retry-btn {
        background: white;
        color: #dc2626;
    }

    .retry-btn:hover {
        background: #f3f4f6;
        transform: translateY(-2px);
    }

    .dismiss-btn {
        background: rgba(255, 255, 255, 0.2);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.3);
    }

    .dismiss-btn:hover {
        background: rgba(255, 255, 255, 0.3);
        transform: translateY(-2px);
    }

    /* Centered Error Message Overlay Styles */
    .error-message-content {
        background: #fef2f2;
        color: #374151;
        padding: 2rem;
        border-radius: 16px;
        max-width: 600px;
        max-height: 80vh;
        width: 90%;
        text-align: center;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
        border: 1px solid #fecaca;
        animation: errorSlideIn 0.4s ease-out;
        overflow-y: auto;
    }

    @keyframes errorSlideIn {
        from { transform: scale(0.95); opacity: 0; }
        to { transform: scale(1); opacity: 1; }
    }

    .error-message-header {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 1rem;
        margin-bottom: 1.5rem;
        font-size: 1.5rem;
        font-weight: 600;
        color: #dc2626;
    }

    .error-message-header i {
        font-size: 2rem;
        color: #f59e0b;
    }

    .error-message-body {
        margin-bottom: 2rem;
        text-align: left;
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        padding: 1.5rem;
        border-radius: 8px;
        max-height: 300px;
        overflow-y: auto;
        font-family: 'Inter', sans-serif;
        font-size: 0.9rem;
        line-height: 1.5;
        color: #4b5563;
    }

    .error-message-body p {
        margin: 0;
        word-wrap: break-word;
    }

    .error-message-actions {
        margin-top: 1.5rem;
    }

    .error-dismiss-btn {
        padding: 0.75rem 2rem;
        border: 1px solid #d1d5db;
        border-radius: 8px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin: 0 auto;
        background: white;
        color: #374151;
    }

    .error-dismiss-btn:hover {
        background: #f9fafb;
        border-color: #9ca3af;
        transform: translateY(-1px);
    }
`;
document.head.appendChild(style);

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboardManager = new DashboardManager();
});

// Prevent back button after logout
window.addEventListener('pageshow', function(event) {
    if (event.persisted) {
        window.location.reload();
    }
});
