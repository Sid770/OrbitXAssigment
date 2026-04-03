// ============================================================================
// AI DOCUMENT PROCESSOR - FRONTEND LOGIC
// ============================================================================

// Global state
let uploadedFiles = [];
let processingResults = {};
let processedDocuments = {};
let isProcessing = false;

// API configuration
const API_BASE = 'http://localhost:8000';
const UPLOAD_ENDPOINT = `${API_BASE}/upload-and-process`;
const HEALTH_ENDPOINT = `${API_BASE}/health`;

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    initializeUploadArea();
    initializeEventListeners();
    checkBackendHealth();
});

// ============================================================================
// UPLOAD AREA - DRAG & DROP
// ============================================================================

function initializeUploadArea() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');

    // Click to upload
    uploadArea.addEventListener('click', () => fileInput.click());

    // Drag over
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    // Drop files
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');

        const files = Array.from(e.dataTransfer.files);
        handleFiles(files);
    });

    // File input change
    fileInput.addEventListener('change', (e) => {
        const files = Array.from(e.target.files);
        handleFiles(files);
        // Reset input so same file can be selected again
        e.target.value = '';
    });
}

// ============================================================================
// FILE HANDLING
// ============================================================================

function handleFiles(files) {
    const validExtensions = ['.pdf', '.txt'];

    files.forEach((file) => {
        const ext = '.' + file.name.split('.').pop().toLowerCase();

        // Validate file type
        if (!validExtensions.includes(ext)) {
            showAlert(`❌ ${file.name} - Unsupported format. Use PDF or TXT.`, 'error');
            return;
        }

        // Validate file size (max 50MB)
        const maxSize = 50 * 1024 * 1024;
        if (file.size > maxSize) {
            showAlert(`❌ ${file.name} - File too large (max 50MB).`, 'error');
            return;
        }

        // Check if already added
        if (uploadedFiles.find((f) => f.name === file.name && f.size === file.size)) {
            showAlert(`⚠️ ${file.name} - Already added.`, 'warning');
            return;
        }

        uploadedFiles.push(file);
    });

    renderFileList();
    updateProcessButton();
}

function renderFileList() {
    const fileList = document.getElementById('fileList');
    fileList.innerHTML = '';

    uploadedFiles.forEach((file, index) => {
        const fileSize = formatFileSize(file.size);
        const item = document.createElement('div');
        item.className = 'file-item';
        item.innerHTML = `
            <div class="file-item-name">
                <strong>${escapeHtml(file.name)}</strong>
                <span class="file-item-size">${fileSize}</span>
            </div>
            <button class="file-item-remove" onclick="removeFile(${index})">✕</button>
        `;
        fileList.appendChild(item);
    });
}

function removeFile(index) {
    uploadedFiles.splice(index, 1);
    renderFileList();
    updateProcessButton();
}

function clearAllFiles() {
    uploadedFiles = [];
    renderFileList();
    updateProcessButton();
}

function updateProcessButton() {
    const processBtn = document.getElementById('processBtn');
    processBtn.disabled = uploadedFiles.length === 0;
}

// ============================================================================
// FILE UPLOAD & PROCESSING
// ============================================================================

async function processFiles() {
    if (uploadedFiles.length === 0) {
        showAlert('❌ Please select files to process.', 'error');
        return;
    }

    if (isProcessing) {
        showAlert('⚠️ Processing in progress. Please wait.', 'warning');
        return;
    }

    isProcessing = true;
    showLoadingSpinner(true);

    try {
        // Create FormData with files
        const formData = new FormData();
        uploadedFiles.forEach((file) => {
            formData.append('files', file);
        });

        // Show status section
        document.getElementById('statusSection').style.display = 'block';
        document.getElementById('resultsSection').style.display = 'none';
        document.getElementById('errorSection').style.display = 'none';

        // Initialize progress tracking
        const totalFiles = uploadedFiles.length;
        updateStatusStats(totalFiles, 0, 0);
        renderProgressBars();

        // Upload files
        console.log(`Uploading ${totalFiles} files...`);

        const response = await fetch(UPLOAD_ENDPOINT, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Upload failed');
        }

        const result = await response.json();
        console.log('Upload result:', result);

        // Process and display results
        handleProcessingResults(result);

    } catch (error) {
        console.error('Error:', error);
        showAlert(`❌ Processing failed: ${error.message}`, 'error');
        isProcessing = false;
        showLoadingSpinner(false);
    }
}

function handleProcessingResults(result) {
    const uploadSection = document.querySelector('.upload-section');
    uploadSection.style.display = 'none';

    document.getElementById('statusSection').style.display = 'none';
    document.getElementById('resultsSection').style.display = 'block';

    // Extract results from pipeline report
    const results = result.documents || [];
    const stats = result.pipeline_report?.statistics || {};

    // Store results
    processedDocuments = results;

    // Update results display
    updateResultsDisplay(results, stats);

    // Show errors if any
    const errors = results.filter((doc) => doc.errors && doc.errors.length > 0);
    if (errors.length > 0) {
        showErrorSection(errors);
    }

    isProcessing = false;
    showLoadingSpinner(false);

    // Update stats
    updateStatusStats(
        stats.total_files || uploadedFiles.length,
        stats.successful || 0,
        stats.failed || 0
    );
}

// ============================================================================
// RESULTS DISPLAY
// ============================================================================

function renderProgressBars() {
    const progressList = document.getElementById('progressList');
    progressList.innerHTML = '';

    uploadedFiles.forEach((file) => {
        const item = document.createElement('div');
        item.className = 'progress-item';
        item.id = `progress-${file.name}`;
        item.innerHTML = `
            <div class="progress-label">
                <span class="progress-label-name">${escapeHtml(file.name)}</span>
                <span class="progress-label-status">Processing...</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: 50%;"></div>
            </div>
        `;
        progressList.appendChild(item);
    });
}

function updateStatusStats(total, completed, failed) {
    document.getElementById('totalCount').textContent = total;
    document.getElementById('completedCount').textContent = completed;
    document.getElementById('failedCount').textContent = failed;
}

function updateResultsDisplay(results, stats) {
    const tbody = document.getElementById('resultsBody');
    tbody.innerHTML = '';

    let successCount = 0;
    let failCount = 0;

    results.forEach((doc) => {
        const hasErrors = doc.errors && doc.errors.length > 0;
        const isSuccess = !hasErrors;

        if (isSuccess) {
            successCount++;
        } else {
            failCount++;
        }

        const fieldCount = Object.keys(doc.extracted_fields || {}).length;
        const confidenceClass =
            doc.confidence === 'high' ? 'confidence-high' : 'confidence-low';
        const statusClass = isSuccess ? 'status-success' : 'status-error';
        const statusText = isSuccess ? '✓ Success' : '✗ Failed';

        const row = document.createElement('tr');
        row.innerHTML = `
            <td><strong>${escapeHtml(doc.file)}</strong></td>
            <td><span class="doc-type">${escapeHtml(doc.doc_type)}</span></td>
            <td><span class="${confidenceClass}">${doc.confidence}</span></td>
            <td><span class="field-count">${fieldCount} fields</span></td>
            <td><span class="${statusClass}">${statusText}</span></td>
            <td class="actions">
                <button class="action-btn" onclick="showDetails('${escapeHtml(doc.file)}')">View</button>
            </td>
        `;
        tbody.appendChild(row);
    });

    // Update summary
    const summary = `${successCount} successful, ${failCount} failed`;
    document.getElementById('resultsSummary').textContent = summary;
}

function showErrorSection(errors) {
    const errorSection = document.getElementById('errorSection');
    const errorList = document.getElementById('errorList');
    errorList.innerHTML = '';

    errors.forEach((doc) => {
        if (!doc.errors || doc.errors.length === 0) return;

        doc.errors.forEach((error) => {
            const item = document.createElement('div');
            item.className = 'error-item';
            item.innerHTML = `
                <div class="error-item-file">${escapeHtml(doc.file)}</div>
                <div class="error-item-message">${escapeHtml(error)}</div>
            `;
            errorList.appendChild(item);
        });
    });

    errorSection.style.display = 'block';
}

// ============================================================================
// DETAILS MODAL
// ============================================================================

function showDetails(fileName) {
    const doc = processedDocuments.find((d) => d.file === fileName);
    if (!doc) return;

    // Populate modal
    document.getElementById('detailsTitle').textContent = escapeHtml(doc.file);
    document.getElementById('detailDocType').textContent = escapeHtml(doc.doc_type);
    document.getElementById('detailConfidence').textContent = doc.confidence.toUpperCase();
    document.getElementById('detailSummary').textContent =
        doc.summary || 'No summary available';

    // Format extracted fields as JSON
    const fieldsJson =
        Object.keys(doc.extracted_fields).length > 0
            ? JSON.stringify(doc.extracted_fields, null, 2)
            : '{}';
    document.getElementById('detailFields').textContent = fieldsJson;

    // Show errors if any
    const errorSection = document.getElementById('detailErrors');
    if (doc.errors && doc.errors.length > 0) {
        errorSection.style.display = 'block';
        const errorList = document.getElementById('detailErrorList');
        errorList.innerHTML = doc.errors
            .map((error) => `<li>${escapeHtml(error)}</li>`)
            .join('');
    } else {
        errorSection.style.display = 'none';
    }

    // Show modal
    document.getElementById('detailsModal').style.display = 'flex';
}

function closeModal() {
    document.getElementById('detailsModal').style.display = 'none';
}

// Close modal when clicking outside
document.addEventListener('click', (e) => {
    const modal = document.getElementById('detailsModal');
    if (e.target === modal) {
        closeModal();
    }
});

// ============================================================================
// EVENT LISTENERS
// ============================================================================

function initializeEventListeners() {
    document.getElementById('processBtn').addEventListener('click', processFiles);
    document.getElementById('clearBtn').addEventListener('click', clearAllFiles);
    document.getElementById('newUploadBtn').addEventListener('click', resetUploadForm);
}

function resetUploadForm() {
    uploadedFiles = [];
    processedDocuments = {};
    renderFileList();
    updateProcessButton();

    document.querySelector('.upload-section').style.display = 'block';
    document.getElementById('statusSection').style.display = 'none';
    document.getElementById('resultsSection').style.display = 'none';
    document.getElementById('errorSection').style.display = 'none';
}

// ============================================================================
// UTILITIES
// ============================================================================

function showLoadingSpinner(show) {
    document.getElementById('loadingSpinner').style.display = show ? 'flex' : 'none';
}

function showAlert(message, type = 'info') {
    // Simple alert - you can enhance this with a toast notification
    console.log(`[${type.toUpperCase()}] ${message}`);

    // Show in a temporary notification
    const alert = document.createElement('div');
    alert.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 16px 20px;
        background: ${type === 'error' ? '#ef4444' : type === 'warning' ? '#f59e0b' : '#10b981'};
        color: white;
        border-radius: 6px;
        z-index: 3000;
        max-width: 400px;
        animation: slideUp 0.3s;
    `;
    alert.textContent = message;
    document.body.appendChild(alert);

    setTimeout(() => {
        alert.remove();
    }, 5000);
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================================================
// BACKEND HEALTH CHECK
// ============================================================================

async function checkBackendHealth() {
    try {
        const response = await fetch(HEALTH_ENDPOINT);
        if (response.ok) {
            const data = await response.json();
            console.log('Backend is healthy:', data);

            if (!data.api_key_configured) {
                showAlert('⚠️ API key not configured. Processing may fail.', 'warning');
            }
        } else {
            console.warn('Backend health check failed:', response.status);
        }
    } catch (error) {
        console.warn('Backend unreachable:', error);
        showAlert(
            '⚠️ Backend server not found. Make sure FastAPI is running on port 8000.',
            'warning'
        );
    }
}
