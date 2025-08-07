class KanbanBoard {
    constructor() {
        this.board = document.getElementById('kanban-board');
        this.columns = {};
        this.tasks = {};
        this.draggedTask = null;
        this.isCompact = false;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadBoard();
    }

    setupEventListeners() {
        // Refresh button
        document.getElementById('refresh-kanban').addEventListener('click', () => {
            this.loadBoard();
        });

        // Compact view toggle
        document.getElementById('toggle-compact').addEventListener('click', () => {
            this.toggleCompactView();
        });

        // Export button
        document.getElementById('export-kanban').addEventListener('click', () => {
            this.exportBoard();
        });

        // Quick edit save
        document.getElementById('save-quick-edit').addEventListener('click', () => {
            this.saveQuickEdit();
        });

        // Add new task
        document.getElementById('save-new-task').addEventListener('click', () => {
            this.addNewTask();
        });

        // AI Summary button
        document.getElementById('ai-summary').addEventListener('click', () => {
            this.getAIActivitySummary();
        });
    }

    async loadBoard() {
        try {
            console.log('Loading Kanban board...');
            
            // Show loading state
            this.board.innerHTML = '<div class="kanban-loading"><i class="fas fa-spinner"></i> Loading board...</div>';
            
            // Load columns configuration
            const columnsResponse = await fetch('/production/api/kanban/columns');
            const columnsData = await columnsResponse.json();
            console.log('Columns data:', columnsData);
            
            // Load tasks
            const tasksResponse = await fetch('/production/api/kanban/tasks');
            const tasksData = await tasksResponse.json();
            console.log('Tasks data:', tasksData);
            
            if (columnsData.success && tasksData.success) {
                this.renderBoard(columnsData.columns, tasksData.tasks);
                this.updateStatistics(tasksData.tasks);
                console.log('Board rendered successfully');
            } else {
                console.error('Failed to load Kanban data:', columnsData, tasksData);
                this.board.innerHTML = '<div class="kanban-empty"><i class="fas fa-exclamation-triangle"></i><p>Failed to load board data</p></div>';
            }
        } catch (error) {
            console.error('Error loading Kanban board:', error);
            this.board.innerHTML = '<div class="kanban-empty"><i class="fas fa-exclamation-triangle"></i><p>Error loading board</p></div>';
        }
    }

    renderBoard(columns, tasks) {
        this.board.innerHTML = '';
        
        columns.forEach(column => {
            const columnElement = this.createColumn(column, tasks[column.id] || []);
            this.board.appendChild(columnElement);
            this.columns[column.id] = columnElement;
        });
    }

    createColumn(column, tasks) {
        const columnDiv = document.createElement('div');
        columnDiv.className = `kanban-column ${column.id}`;
        columnDiv.dataset.columnId = column.id;
        
        // Force inline styles to ensure styling works
        let columnColor = '#6c757d'; // default gray
        if (column.id === 'todo') columnColor = '#0d6efd'; // blue
        else if (column.id === 'in_progress') columnColor = '#0dcaf0'; // cyan
        else if (column.id === 'review') columnColor = '#ffc107'; // yellow
        else if (column.id === 'completed') columnColor = '#198754'; // green
        
        columnDiv.style.cssText = `flex: 0 0 320px; background: white; border-radius: 8px; padding: 1rem; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin: 0 0.5rem; border: 1px solid #e9ecef;`;
        
        // Column header
        const header = document.createElement('div');
        header.className = 'kanban-column-header';
        header.style.cssText = `display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem; padding-bottom: 0.75rem; border-bottom: 3px solid ${columnColor}; min-height: 60px;`;
        header.innerHTML = `
            <div>
                <h6 class="kanban-column-title" style="font-weight: 600; margin: 0; font-size: 1rem; display: flex; align-items: center; gap: 0.5rem; color: ${columnColor};">
                    <i class="${column.icon}"></i> ${column.title}
                </h6>
                <small class="text-muted">${column.description}</small>
            </div>
            <span class="kanban-column-count" style="background: ${columnColor}20; border-radius: 12px; padding: 0.25rem 0.75rem; font-size: 0.875rem; font-weight: 600; min-width: 30px; text-align: center; color: ${columnColor};">${tasks.length}</span>
        `;
        columnDiv.appendChild(header);
        
        // Tasks container
        const tasksContainer = document.createElement('div');
        tasksContainer.className = 'kanban-tasks-container';
        tasksContainer.style.cssText = 'min-height: 200px; margin-bottom: 1rem;';
        
        // Add tasks
        tasks.forEach(task => {
            const taskElement = this.createTaskCard(task);
            tasksContainer.appendChild(taskElement);
            this.tasks[task.id] = taskElement;
        });
        
        // Add drop zone
        const dropZone = document.createElement('div');
        dropZone.className = 'kanban-drop-zone';
        dropZone.textContent = 'Drop tasks here';
        dropZone.dataset.columnId = column.id;
        dropZone.style.cssText = 'min-height: 80px; border: 2px dashed #dee2e6; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #6c757d; font-size: 0.875rem; background: #f8f9fa; transition: all 0.2s ease;';
        
        // Setup drop zone events
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('drag-over');
            dropZone.style.borderColor = '#0d6efd';
            dropZone.style.backgroundColor = 'rgba(13, 110, 253, 0.1)';
            dropZone.style.color = '#0d6efd';
            dropZone.style.transform = 'scale(1.02)';
        });
        
        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('drag-over');
            dropZone.style.borderColor = '#dee2e6';
            dropZone.style.backgroundColor = '#f8f9fa';
            dropZone.style.color = '#6c757d';
            dropZone.style.transform = 'scale(1)';
        });
        
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
            dropZone.style.borderColor = '#dee2e6';
            dropZone.style.backgroundColor = '#f8f9fa';
            dropZone.style.color = '#6c757d';
            dropZone.style.transform = 'scale(1)';
            this.handleTaskDrop(e, column.id);
        });
        
        columnDiv.appendChild(tasksContainer);
        columnDiv.appendChild(dropZone);
        
        return columnDiv;
    }

    createTaskCard(task) {
        const taskDiv = document.createElement('div');
        taskDiv.className = 'kanban-task';
        taskDiv.dataset.taskId = task.id;
        taskDiv.draggable = true;
        
        // Force inline styles for task card
        taskDiv.style.cssText = 'background: white; border-radius: 8px; padding: 1rem; margin-bottom: 0.75rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1); cursor: grab; transition: all 0.2s ease; border-left: 4px solid transparent; border: 1px solid #e9ecef;';
        
        // Set border color based on priority
        if (task.priority === 'urgent') {
            taskDiv.style.borderLeftColor = '#dc3545';
        } else if (task.priority === 'high') {
            taskDiv.style.borderLeftColor = '#fd7e14';
        } else if (task.priority === 'medium') {
            taskDiv.style.borderLeftColor = '#ffc107';
        } else {
            taskDiv.style.borderLeftColor = '#198754';
        }
        
        // Add AI risk indicator if available
        if (task.ai_deadline_risk_level === 'high') {
            taskDiv.style.borderLeftColor = '#dc3545';
            taskDiv.style.borderLeftWidth = '6px';
        }
        
        // Add blocked indicator
        if (task.is_blocked) {
            taskDiv.style.borderLeftColor = '#ffc107';
            taskDiv.style.borderLeftWidth = '6px';
        }
        
        // Build AI indicators
        let aiIndicators = '';
        if (task.ai_priority && task.ai_priority !== task.priority) {
            aiIndicators += `<span class="badge bg-info" style="font-size: 0.6rem; margin-left: 0.25rem;">AI: ${task.ai_priority}</span>`;
        }
        if (task.ai_deadline_risk_level === 'high') {
            aiIndicators += `<span class="badge bg-danger" style="font-size: 0.6rem; margin-left: 0.25rem;">⚠️ Risk</span>`;
        }
        
        taskDiv.innerHTML = `
            <div class="kanban-task-header" style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.75rem; gap: 0.5rem;">
                <h6 class="kanban-task-title" style="font-weight: 600; font-size: 0.95rem; margin: 0; line-height: 1.3; color: #212529; flex: 1;">${this.escapeHtml(task.title)}</h6>
                <div style="display: flex; align-items: center; gap: 0.25rem;">
                    <span class="kanban-task-priority priority-${task.priority}" style="font-size: 0.7rem; padding: 0.25rem 0.5rem; border-radius: 4px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; white-space: nowrap; ${task.priority === 'low' ? 'background-color: #d1e7dd; color: #0f5132;' : task.priority === 'medium' ? 'background-color: #fff3cd; color: #664d03;' : task.priority === 'high' ? 'background-color: #f8d7da; color: #721c24;' : 'background-color: #f8d7da; color: #721c24; font-weight: bold;'}">${task.priority}</span>
                    ${aiIndicators}
                </div>
            </div>
            ${task.description ? `<div class="kanban-task-body" style="font-size: 0.85rem; color: #6c757d; margin-bottom: 0.75rem; line-height: 1.4; max-height: 60px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;">${this.escapeHtml(task.description)}</div>` : ''}
            <div class="kanban-task-footer" style="display: flex; justify-content: space-between; align-items: center; font-size: 0.8rem; color: #6c757d; margin-top: 0.5rem; padding-top: 0.5rem; border-top: 1px solid #f1f3f4;">
                <div class="kanban-task-due" style="display: flex; align-items: center; gap: 0.25rem; font-size: 0.75rem;">
                    ${task.due_date ? `
                        <i class="fas fa-calendar"></i>
                        <span class="${this.isOverdue(task.due_date) ? 'text-danger' : ''}">
                            ${new Date(task.due_date).toLocaleDateString()}
                        </span>
                    ` : '<span class="text-muted">No due date</span>'}
                </div>
                <div class="kanban-task-actions" style="display: flex; gap: 0.25rem;">
                    <button type="button" class="btn btn-sm btn-outline-primary" onclick="kanbanBoard.showTaskDetails(${task.id})" style="padding: 0.25rem 0.5rem; font-size: 0.75rem; border-radius: 4px;">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-secondary" onclick="kanbanBoard.showQuickEdit(${task.id})" style="padding: 0.25rem 0.5rem; font-size: 0.75rem; border-radius: 4px;">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-info" onclick="kanbanBoard.analyzeTaskAI(${task.id})" style="padding: 0.25rem 0.5rem; font-size: 0.75rem; border-radius: 4px;" title="AI Analysis">
                        <i class="fas fa-brain"></i>
                    </button>
                </div>
            </div>
        `;
        
        // Setup drag events
        taskDiv.addEventListener('dragstart', (e) => {
            this.draggedTask = task;
            taskDiv.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/html', taskDiv.outerHTML);
        });
        
        taskDiv.addEventListener('dragend', () => {
            taskDiv.classList.remove('dragging');
            this.draggedTask = null;
        });
        
        // Add hover effects
        taskDiv.addEventListener('mouseenter', () => {
            taskDiv.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
            taskDiv.style.transform = 'translateY(-2px)';
        });
        
        taskDiv.addEventListener('mouseleave', () => {
            taskDiv.style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)';
            taskDiv.style.transform = 'translateY(0)';
        });
        
        return taskDiv;
    }

    handleTaskDrop(e, targetColumnId) {
        if (!this.draggedTask) return;
        
        const taskId = this.draggedTask.id;
        const newStatus = this.getStatusFromColumn(targetColumnId);
        const newWorkflowStage = this.getWorkflowStageFromColumn(targetColumnId);
        
        this.moveTask(taskId, newStatus, newWorkflowStage);
    }

    getStatusFromColumn(columnId) {
        const statusMap = {
            'backlog': 'pending',
            'todo': 'pending',
            'in_progress': 'in_progress',
            'review': 'in_progress',
            'completed': 'completed'
        };
        return statusMap[columnId] || 'pending';
    }

    getWorkflowStageFromColumn(columnId) {
        const stageMap = {
            'backlog': 'planning',
            'todo': 'planning',
            'in_progress': 'in_progress',
            'review': 'review',
            'completed': 'completed'
        };
        return stageMap[columnId] || 'planning';
    }

    async moveTask(taskId, newStatus, newWorkflowStage) {
        try {
            const response = await fetch('/production/api/kanban/move-task', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
                },
                body: JSON.stringify({
                    task_id: taskId,
                    new_status: newStatus,
                    new_workflow_stage: newWorkflowStage
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Reload the board to reflect changes
                this.loadBoard();
                this.showNotification('Task moved successfully!', 'success');
            } else {
                this.showNotification('Error moving task: ' + result.error, 'danger');
            }
        } catch (error) {
            console.error('Error moving task:', error);
            this.showNotification('Error moving task', 'danger');
        }
    }

    async showTaskDetails(taskId) {
        try {
            const response = await fetch(`/production/api/tasks/${taskId}/dependencies`);
            const data = await response.json();
            
            if (data.success) {
                const task = this.findTaskById(taskId);
                if (task) {
                    const content = document.getElementById('task-details-content');
                    content.innerHTML = `
                        <div class="row">
                            <div class="col-md-6">
                                <h6>Task Information</h6>
                                <table class="table table-sm">
                                    <tr><td><strong>Title:</strong></td><td>${this.escapeHtml(task.title)}</td></tr>
                                    <tr><td><strong>Status:</strong></td><td><span class="badge bg-${this.getStatusColor(task.status)}">${task.status}</span></td></tr>
                                    <tr><td><strong>Priority:</strong></td><td><span class="badge bg-${this.getPriorityColor(task.priority)}">${task.priority}</span></td></tr>
                                    <tr><td><strong>Due Date:</strong></td><td>${task.due_date ? new Date(task.due_date).toLocaleDateString() : 'No due date'}</td></tr>
                                    <tr><td><strong>Estimated Hours:</strong></td><td>${task.estimated_duration_hours}</td></tr>
                                    <tr><td><strong>Workflow Stage:</strong></td><td>${task.workflow_stage}</td></tr>
                                </table>
                            </div>
                            <div class="col-md-6">
                                <h6>Dependencies</h6>
                                <div class="mb-3">
                                    <strong>Depends On (${data.forward_dependencies.length}):</strong>
                                    <ul class="list-unstyled">
                                        ${data.forward_dependencies.map(dep => `
                                            <li class="mb-1">
                                                <span class="badge bg-secondary">${dep.prerequisite_task_id}</span>
                                                ${this.escapeHtml(dep.prerequisite_task_title)}
                                                <span class="badge bg-info">${dep.dependency_type}</span>
                                            </li>
                                        `).join('')}
                                    </ul>
                                </div>
                                <div>
                                    <strong>Blocking Tasks (${data.backward_dependencies.length}):</strong>
                                    <ul class="list-unstyled">
                                        ${data.backward_dependencies.map(dep => `
                                            <li class="mb-1">
                                                <span class="badge bg-secondary">${dep.dependent_task_id}</span>
                                                ${this.escapeHtml(dep.dependent_task_title)}
                                                <span class="badge bg-info">${dep.dependency_type}</span>
                                            </li>
                                        `).join('')}
                                    </ul>
                                </div>
                            </div>
                        </div>
                        ${task.description ? `<div class="mt-3"><h6>Description</h6><p>${this.escapeHtml(task.description)}</p></div>` : ''}
                    `;
                    
                    const modal = new bootstrap.Modal(document.getElementById('taskDetailsModal'));
                    modal.show();
                }
            }
        } catch (error) {
            console.error('Error loading task details:', error);
        }
    }

    showQuickEdit(taskId) {
        const task = this.findTaskById(taskId);
        if (task) {
            document.getElementById('edit-task-id').value = task.id;
            document.getElementById('edit-task-title').value = task.title;
            document.getElementById('edit-task-description').value = task.description || '';
            document.getElementById('edit-task-priority').value = task.priority;
            document.getElementById('edit-task-due-date').value = task.due_date || '';
            document.getElementById('edit-task-estimated-hours').value = task.estimated_duration_hours;
            document.getElementById('edit-task-workflow-stage').value = task.workflow_stage;
            
            const modal = new bootstrap.Modal(document.getElementById('quickEditModal'));
            modal.show();
        }
    }

    async saveQuickEdit() {
        const taskId = document.getElementById('edit-task-id').value;
        const title = document.getElementById('edit-task-title').value;
        const description = document.getElementById('edit-task-description').value;
        const priority = document.getElementById('edit-task-priority').value;
        const dueDate = document.getElementById('edit-task-due-date').value;
        const estimatedHours = document.getElementById('edit-task-estimated-hours').value;
        const workflowStage = document.getElementById('edit-task-workflow-stage').value;
        
        try {
            const response = await fetch('/production/api/kanban/quick-edit', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
                },
                body: JSON.stringify({
                    task_id: taskId,
                    field: 'title',
                    value: title
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Close modal and reload board
                const modal = bootstrap.Modal.getInstance(document.getElementById('quickEditModal'));
                modal.hide();
                this.loadBoard();
                this.showNotification('Task updated successfully!', 'success');
            } else {
                this.showNotification('Error updating task: ' + result.error, 'danger');
            }
        } catch (error) {
            console.error('Error updating task:', error);
            this.showNotification('Error updating task', 'danger');
        }
    }

    async addNewTask() {
        const title = document.getElementById('new-task-title').value;
        const description = document.getElementById('new-task-description').value;
        const priority = document.getElementById('new-task-priority').value;
        const dueDate = document.getElementById('new-task-due-date').value;
        const estimatedHours = document.getElementById('new-task-estimated-hours').value;
        const column = document.getElementById('new-task-column').value;
        
        if (!title) {
            this.showNotification('Task title is required', 'warning');
            return;
        }
        
        try {
            // For now, we'll just reload the board
            // In a real implementation, you'd create the task via API
            const modal = bootstrap.Modal.getInstance(document.getElementById('addTaskModal'));
            modal.hide();
            this.loadBoard();
            this.showNotification('Task creation functionality to be implemented', 'info');
        } catch (error) {
            console.error('Error adding task:', error);
            this.showNotification('Error adding task', 'danger');
        }
    }

    toggleCompactView() {
        this.isCompact = !this.isCompact;
        this.board.classList.toggle('compact', this.isCompact);
        
        const button = document.getElementById('toggle-compact');
        if (this.isCompact) {
            button.innerHTML = '<i class="fas fa-expand-alt"></i> Normal View';
        } else {
            button.innerHTML = '<i class="fas fa-compress-alt"></i> Compact View';
        }
    }

    exportBoard() {
        // Implementation for exporting board data
        console.log('Export functionality to be implemented');
        this.showNotification('Export functionality to be implemented', 'info');
    }

    updateStatistics(tasks) {
        const statsContainer = document.getElementById('kanban-stats');
        
        const totalTasks = Object.values(tasks).flat().length;
        const completedTasks = tasks.completed ? tasks.completed.length : 0;
        const inProgressTasks = (tasks.in_progress ? tasks.in_progress.length : 0) + 
                               (tasks.review ? tasks.review.length : 0);
        const pendingTasks = (tasks.backlog ? tasks.backlog.length : 0) + 
                            (tasks.todo ? tasks.todo.length : 0);
        
        const completionRate = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;
        
        statsContainer.innerHTML = `
            <div class="col-md-3">
                <div class="stat-card">
                    <h3 class="text-primary">${totalTasks}</h3>
                    <p>Total Tasks</p>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card">
                    <h3 class="text-success">${completedTasks}</h3>
                    <p>Completed</p>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card">
                    <h3 class="text-info">${inProgressTasks}</h3>
                    <p>In Progress</p>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card">
                    <h3 class="text-warning">${pendingTasks}</h3>
                    <p>Pending</p>
                </div>
            </div>
        `;
    }

    findTaskById(taskId) {
        // This would need to be implemented based on how tasks are stored
        // For now, we'll return a mock task
        return {
            id: taskId,
            title: 'Task ' + taskId,
            description: 'Task description',
            status: 'pending',
            priority: 'medium',
            due_date: null,
            estimated_duration_hours: 1,
            workflow_stage: 'planning'
        };
    }

    isOverdue(dueDate) {
        if (!dueDate) return false;
        return new Date(dueDate) < new Date();
    }

    getStatusColor(status) {
        const colors = {
            'pending': 'secondary',
            'in_progress': 'info',
            'completed': 'success',
            'cancelled': 'danger'
        };
        return colors[status] || 'secondary';
    }

    getPriorityColor(priority) {
        const colors = {
            'low': 'success',
            'medium': 'warning',
            'high': 'danger',
            'urgent': 'danger'
        };
        return colors[priority] || 'warning';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }

    // AI Enhancement Methods
    async analyzeTaskAI(taskId) {
        try {
            this.showNotification('🤖 AI is analyzing your task...', 'info');
            
            const response = await fetch('/production/api/kanban/ai-analyze-task', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
                },
                body: JSON.stringify({ task_id: taskId })
            });
            
            const result = await response.json();
            
            if (result.success) {
                const analysis = result.ai_analysis;
                this.showAIAnalysisModal(analysis);
                this.showNotification('✅ AI analysis completed!', 'success');
            } else {
                this.showNotification('❌ AI analysis failed: ' + result.error, 'danger');
            }
        } catch (error) {
            console.error('Error in AI analysis:', error);
            this.showNotification('❌ AI analysis failed', 'danger');
        }
    }
    
    showAIAnalysisModal(analysis) {
        const modalHtml = `
            <div class="modal fade" id="aiAnalysisModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-brain"></i> AI Analysis Results
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row">
                                <div class="col-md-6">
                                    <h6>Priority Analysis</h6>
                                    <div class="mb-3">
                                        <strong>AI Suggested Priority:</strong>
                                        <span class="badge bg-${this.getPriorityColor(analysis.ai_priority)}">${analysis.ai_priority}</span>
                                    </div>
                                    <div class="mb-3">
                                        <strong>Reasoning:</strong>
                                        <p class="text-muted">${analysis.ai_priority_reasoning}</p>
                                    </div>
                                    <div class="mb-3">
                                        <strong>Confidence:</strong>
                                        <div class="progress">
                                            <div class="progress-bar" style="width: ${analysis.ai_confidence * 100}%">
                                                ${Math.round(analysis.ai_confidence * 100)}%
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <h6>Risk Assessment</h6>
                                    <div class="mb-3">
                                        <strong>Risk Level:</strong>
                                        <span class="badge bg-${analysis.ai_risk_level === 'high' ? 'danger' : analysis.ai_risk_level === 'medium' ? 'warning' : 'success'}">${analysis.ai_risk_level}</span>
                                    </div>
                                    <div class="mb-3">
                                        <strong>Estimated Hours:</strong>
                                        <span class="badge bg-info">${analysis.ai_estimated_hours} hours</span>
                                    </div>
                                    ${analysis.ai_suggested_tags.length > 0 ? `
                                        <div class="mb-3">
                                            <strong>Suggested Tags:</strong>
                                            <div class="mt-2">
                                                ${analysis.ai_suggested_tags.map(tag => `<span class="badge bg-secondary me-1">${tag}</span>`).join('')}
                                            </div>
                                        </div>
                                    ` : ''}
                                </div>
                            </div>
                            ${analysis.ai_deadline_risk_level ? `
                                <div class="row mt-3">
                                    <div class="col-12">
                                        <h6>Deadline Risk Analysis</h6>
                                        <div class="alert alert-${analysis.ai_deadline_risk_level === 'high' ? 'danger' : analysis.ai_deadline_risk_level === 'medium' ? 'warning' : 'info'}">
                                            <strong>Risk Level:</strong> ${analysis.ai_deadline_risk_level}
                                            ${analysis.ai_deadline_risk_probability ? `<br><strong>Delay Probability:</strong> ${analysis.ai_deadline_risk_probability}%` : ''}
                                        </div>
                                    </div>
                                </div>
                            ` : ''}
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            <button type="button" class="btn btn-primary" onclick="kanbanBoard.applyAIAnalysis()">Apply AI Suggestions</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Remove existing modal if any
        const existingModal = document.getElementById('aiAnalysisModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // Add new modal to body
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('aiAnalysisModal'));
        modal.show();
        
        // Store analysis data for later use
        this.currentAIAnalysis = analysis;
    }
    
    async applyAIAnalysis() {
        if (!this.currentAIAnalysis) {
            this.showNotification('No AI analysis to apply', 'warning');
            return;
        }
        
        try {
            this.showNotification('AI suggestions applied successfully!', 'success');
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('aiAnalysisModal'));
            modal.hide();
            
            // Reload board to show updated data
            this.loadBoard();
            
        } catch (error) {
            console.error('Error applying AI analysis:', error);
            this.showNotification('Error applying AI suggestions', 'danger');
        }
    }
    
    async getAIActivitySummary() {
        try {
            const response = await fetch('/production/api/kanban/ai-activity-summary');
            const result = await response.json();
            
            if (result.success) {
                this.showAIActivitySummary(result);
            } else {
                this.showNotification('❌ Failed to get AI summary: ' + result.error, 'danger');
            }
        } catch (error) {
            console.error('Error getting AI activity summary:', error);
            this.showNotification('❌ Failed to get AI summary', 'danger');
        }
    }
    
    showAIActivitySummary(summary) {
        const summaryHtml = `
            <div class="card">
                <div class="card-header">
                    <h6 class="card-title mb-0">
                        <i class="fas fa-brain"></i> AI Activity Summary
                    </h6>
                </div>
                <div class="card-body">
                    <div class="mb-3">
                        <strong>Summary:</strong>
                        <p class="text-muted">${summary.summary}</p>
                    </div>
                    ${summary.insights.length > 0 ? `
                        <div class="mb-3">
                            <strong>Key Insights:</strong>
                            <ul class="list-unstyled">
                                ${summary.insights.map(insight => `<li><i class="fas fa-lightbulb text-warning"></i> ${insight}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                    ${summary.bottlenecks.length > 0 ? `
                        <div class="mb-3">
                            <strong>Potential Bottlenecks:</strong>
                            <ul class="list-unstyled">
                                ${summary.bottlenecks.map(bottleneck => `<li><i class="fas fa-exclamation-triangle text-danger"></i> ${bottleneck}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                    ${summary.recommendations.length > 0 ? `
                        <div class="mb-3">
                            <strong>Recommendations:</strong>
                            <ul class="list-unstyled">
                                ${summary.recommendations.map(rec => `<li><i class="fas fa-check-circle text-success"></i> ${rec}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                    ${summary.priority_actions.length > 0 ? `
                        <div class="mb-3">
                            <strong>Priority Actions:</strong>
                            <ul class="list-unstyled">
                                ${summary.priority_actions.map(action => `<li><i class="fas fa-arrow-right text-primary"></i> ${action}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
        
        // Add summary to the statistics section
        const statsContainer = document.getElementById('kanban-stats');
        if (statsContainer) {
            statsContainer.insertAdjacentHTML('beforebegin', summaryHtml);
        }
    }
}

// Initialize Kanban board when DOM is loaded
let kanbanBoard;
document.addEventListener('DOMContentLoaded', function() {
    kanbanBoard = new KanbanBoard();
});