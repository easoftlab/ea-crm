class AIInsights {
    constructor() {
        this.insightsContainer = document.getElementById('ai-insights-content');
        this.analysisData = null;
        this.init();
    }
    
    init() {
        this.loadAuditAnalysis();
        this.loadProductivityAnalysis();
    }
    
    async loadAuditAnalysis() {
        try {
            const response = await fetch('/production/api/ai/audit-analysis');
            const data = await response.json();
            
            if (data.success) {
                this.displayAuditInsights(data.analysis);
            } else {
                this.showError('Failed to load audit analysis');
            }
        } catch (error) {
            console.error('Error loading audit analysis:', error);
            this.showError('Error loading AI insights');
        }
    }
    
    async loadProductivityAnalysis() {
        try {
            const response = await fetch('/production/api/ai/productivity-analysis');
            const data = await response.json();
            
            if (data.success) {
                this.displayProductivityInsights(data.analysis);
            } else {
                this.showError('Failed to load productivity analysis');
            }
        } catch (error) {
            console.error('Error loading productivity analysis:', error);
            this.showError('Error loading productivity insights');
        }
    }
    
    displayAuditInsights(analysis) {
        if (!this.insightsContainer) return;
        
        const insightsHtml = `
            <div class="ai-insights-section">
                <h6 class="text-primary mb-3">
                    <i class="fas fa-chart-line"></i> Activity Summary
                </h6>
                <p class="text-muted small mb-3">${analysis.summary || 'No recent activity to analyze'}</p>
                
                ${analysis.insights && analysis.insights.length > 0 ? `
                    <h6 class="text-success mb-2">
                        <i class="fas fa-lightbulb"></i> Key Insights
                    </h6>
                    <ul class="list-unstyled small mb-3">
                        ${analysis.insights.map(insight => `<li><i class="fas fa-check text-success me-2"></i>${insight}</li>`).join('')}
                    </ul>
                ` : ''}
                
                ${analysis.recommendations && analysis.recommendations.length > 0 ? `
                    <h6 class="text-info mb-2">
                        <i class="fas fa-arrow-up"></i> Recommendations
                    </h6>
                    <ul class="list-unstyled small mb-3">
                        ${analysis.recommendations.map(rec => `<li><i class="fas fa-star text-info me-2"></i>${rec}</li>`).join('')}
                    </ul>
                ` : ''}
                
                ${analysis.anomalies && analysis.anomalies.length > 0 ? `
                    <h6 class="text-warning mb-2">
                        <i class="fas fa-exclamation-triangle"></i> Anomalies
                    </h6>
                    <ul class="list-unstyled small mb-3">
                        ${analysis.anomalies.map(anomaly => `<li><i class="fas fa-warning text-warning me-2"></i>${anomaly}</li>`).join('')}
                    </ul>
                ` : ''}
                
                <div class="mt-3">
                    <div class="d-flex justify-content-between align-items-center">
                        <span class="text-muted small">Productivity Score</span>
                        <span class="badge bg-${this.getProductivityColor(analysis.productivity_score || 0)}">
                            ${analysis.productivity_score || 0}%
                        </span>
                    </div>
                    <div class="progress mt-1" style="height: 6px;">
                        <div class="progress-bar bg-${this.getProductivityColor(analysis.productivity_score || 0)}" 
                             style="width: ${analysis.productivity_score || 0}%"></div>
                    </div>
                </div>
            </div>
        `;
        
        this.insightsContainer.innerHTML = insightsHtml;
    }
    
    displayProductivityInsights(analysis) {
        if (!this.insightsContainer) return;
        
        // Append productivity insights to existing content
        const productivityHtml = `
            <div class="ai-insights-section mt-4">
                <h6 class="text-primary mb-3">
                    <i class="fas fa-clock"></i> Productivity Patterns
                </h6>
                
                ${analysis.patterns && analysis.patterns.length > 0 ? `
                    <h6 class="text-success mb-2">
                        <i class="fas fa-chart-bar"></i> Patterns
                    </h6>
                    <ul class="list-unstyled small mb-3">
                        ${analysis.patterns.map(pattern => `<li><i class="fas fa-chart-line text-success me-2"></i>${pattern}</li>`).join('')}
                    </ul>
                ` : ''}
                
                ${analysis.bottlenecks && analysis.bottlenecks.length > 0 ? `
                    <h6 class="text-warning mb-2">
                        <i class="fas fa-tachometer-alt"></i> Bottlenecks
                    </h6>
                    <ul class="list-unstyled small mb-3">
                        ${analysis.bottlenecks.map(bottleneck => `<li><i class="fas fa-exclamation-circle text-warning me-2"></i>${bottleneck}</li>`).join('')}
                    </ul>
                ` : ''}
                
                ${analysis.peak_hours && analysis.peak_hours.length > 0 ? `
                    <h6 class="text-info mb-2">
                        <i class="fas fa-clock"></i> Peak Hours
                    </h6>
                    <div class="small text-muted mb-3">
                        ${analysis.peak_hours.map(hour => `<span class="badge bg-info me-1">${hour}</span>`).join('')}
                    </div>
                ` : ''}
            </div>
        `;
        
        this.insightsContainer.innerHTML += productivityHtml;
    }
    
    getProductivityColor(score) {
        if (score >= 80) return 'success';
        if (score >= 60) return 'info';
        if (score >= 40) return 'warning';
        return 'danger';
    }
    
    showError(message) {
        if (this.insightsContainer) {
            this.insightsContainer.innerHTML = `
                <div class="text-center text-muted">
                    <i class="fas fa-exclamation-triangle fa-2x mb-2"></i>
                    <p>${message}</p>
                    <button class="btn btn-sm btn-outline-primary" onclick="aiInsights.init()">
                        <i class="fas fa-redo"></i> Retry
                    </button>
                </div>
            `;
        }
    }
}

// Smart Search functionality
class SmartSearch {
    constructor() {
        this.searchInput = document.getElementById('smart-search-input');
        this.searchResults = document.getElementById('smart-search-results');
        this.init();
    }
    
    init() {
        if (this.searchInput) {
            this.searchInput.addEventListener('input', this.debounce(this.performSearch.bind(this), 500));
        }
    }
    
    async performSearch() {
        const query = this.searchInput.value.trim();
        if (query.length < 2) {
            this.clearResults();
            return;
        }
        
        try {
            const response = await fetch('/production/api/ai/smart-search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
                },
                body: JSON.stringify({ query: query })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.displayResults(data);
            } else {
                this.showError(data.error || 'Search failed');
            }
        } catch (error) {
            console.error('Search error:', error);
            this.showError('Search failed');
        }
    }
    
    displayResults(data) {
        if (!this.searchResults) return;
        
        const resultsHtml = `
            <div class="search-results-header">
                <h6 class="mb-2">
                    <i class="fas fa-search"></i> Search Results
                </h6>
                <p class="text-muted small mb-3">${data.reason}</p>
            </div>
            <div class="search-results-list">
                ${this.generateTaskResults(data.matching_task_ids)}
            </div>
        `;
        
        this.searchResults.innerHTML = resultsHtml;
        this.searchResults.style.display = 'block';
    }
    
    generateTaskResults(taskIds) {
        // This would need to be populated with actual task data
        // For now, show a placeholder
        if (taskIds.length === 0) {
            return '<p class="text-muted">No tasks found matching your query.</p>';
        }
        
        return `
            <div class="list-group list-group-flush">
                ${taskIds.map(id => `
                    <a href="/production/tasks/${id}" class="list-group-item list-group-item-action">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <h6 class="mb-1">Task #${id}</h6>
                                <small class="text-muted">Click to view details</small>
                            </div>
                            <i class="fas fa-chevron-right text-muted"></i>
                        </div>
                    </a>
                `).join('')}
            </div>
        `;
    }
    
    clearResults() {
        if (this.searchResults) {
            this.searchResults.innerHTML = '';
            this.searchResults.style.display = 'none';
        }
    }
    
    showError(message) {
        if (this.searchResults) {
            this.searchResults.innerHTML = `
                <div class="text-center text-muted">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>${message}</p>
                </div>
            `;
            this.searchResults.style.display = 'block';
        }
    }
    
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// Task Assignment Suggestions
class TaskAssignmentAI {
    constructor() {
        this.init();
    }
    
    init() {
        // Add event listeners for task assignment forms
        document.addEventListener('DOMContentLoaded', () => {
            this.setupAssignmentSuggestions();
        });
    }
    
    setupAssignmentSuggestions() {
        const assignButtons = document.querySelectorAll('[data-action="suggest-assignee"]');
        assignButtons.forEach(button => {
            button.addEventListener('click', this.handleAssignmentSuggestion.bind(this));
        });
    }
    
    async handleAssignmentSuggestion(event) {
        event.preventDefault();
        
        const button = event.target;
        const taskId = button.dataset.taskId;
        const taskData = this.getTaskData(taskId);
        
        try {
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing...';
            
            const response = await fetch('/production/api/ai/suggest-assignee', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
                },
                body: JSON.stringify({ task: taskData })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.displayAssignmentSuggestion(data.suggestion, data.available_users);
            } else {
                this.showAssignmentError(data.error || 'Failed to get suggestion');
            }
        } catch (error) {
            console.error('Assignment suggestion error:', error);
            this.showAssignmentError('Failed to get suggestion');
        } finally {
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-brain"></i> AI Suggest';
        }
    }
    
    getTaskData(taskId) {
        // Get task data from the DOM or make an API call
        const taskElement = document.querySelector(`[data-task-id="${taskId}"]`);
        if (taskElement) {
            return {
                id: taskId,
                title: taskElement.dataset.taskTitle || '',
                priority: taskElement.dataset.taskPriority || 'medium',
                type: taskElement.dataset.taskType || 'general'
            };
        }
        return { id: taskId };
    }
    
    displayAssignmentSuggestion(suggestion, availableUsers) {
        // Create a modal or notification to show the suggestion
        const modalHtml = `
            <div class="modal fade" id="assignmentSuggestionModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-brain"></i> AI Assignment Suggestion
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="alert alert-info">
                                <i class="fas fa-lightbulb"></i>
                                <strong>AI Recommendation:</strong> ${suggestion.reason}
                            </div>
                            <div class="d-flex justify-content-between align-items-center">
                                <span>Confidence Score:</span>
                                <span class="badge bg-${this.getConfidenceColor(suggestion.confidence_score)}">
                                    ${suggestion.confidence_score}%
                                </span>
                            </div>
                            ${suggestion.suggested_user_id ? `
                                <div class="mt-3">
                                    <button class="btn btn-primary" onclick="taskAssignmentAI.assignToSuggestedUser(${suggestion.suggested_user_id})">
                                        <i class="fas fa-user-plus"></i> Assign to Suggested User
                                    </button>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Remove existing modal if any
        const existingModal = document.getElementById('assignmentSuggestionModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // Add new modal to DOM
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('assignmentSuggestionModal'));
        modal.show();
    }
    
    getConfidenceColor(score) {
        if (score >= 80) return 'success';
        if (score >= 60) return 'info';
        if (score >= 40) return 'warning';
        return 'danger';
    }
    
    showAssignmentError(message) {
        // Show error notification
        const alertHtml = `
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                <i class="fas fa-exclamation-triangle"></i> ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        // Add to page
        const container = document.querySelector('.container') || document.body;
        container.insertAdjacentHTML('afterbegin', alertHtml);
    }
    
    async assignToSuggestedUser(userId) {
        // Implementation for assigning task to suggested user
        console.log('Assigning to user:', userId);
        // This would integrate with your existing task assignment logic
    }
}

// Initialize AI features when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize AI Insights
    if (document.getElementById('ai-insights-content')) {
        window.aiInsights = new AIInsights();
    }
    
    // Initialize Smart Search
    if (document.getElementById('smart-search-input')) {
        window.smartSearch = new SmartSearch();
    }
    
    // Initialize Task Assignment AI
    window.taskAssignmentAI = new TaskAssignmentAI();
}); 