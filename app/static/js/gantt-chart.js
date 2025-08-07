class GanttChart {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = d3.select(containerId);
        this.data = { tasks: [], dependencies: [] };
        this.filters = {};
        this.zoom = 1;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadData();
    }

    setupEventListeners() {
        // Filter changes
        document.getElementById('status-filter').addEventListener('change', (e) => {
            this.filters.status = e.target.value;
            this.applyFilters();
        });

        document.getElementById('priority-filter').addEventListener('change', (e) => {
            this.filters.priority = e.target.value;
            this.applyFilters();
        });

        document.getElementById('assignee-filter').addEventListener('change', (e) => {
            this.filters.assignee = e.target.value;
            this.applyFilters();
        });

        document.getElementById('project-filter').addEventListener('change', (e) => {
            this.filters.project = e.target.value;
            this.applyFilters();
        });

        // Zoom controls
        document.getElementById('zoom-in').addEventListener('click', () => {
            this.zoom = Math.min(this.zoom * 1.2, 3);
            this.updateChart();
        });

        document.getElementById('zoom-out').addEventListener('click', () => {
            this.zoom = Math.max(this.zoom / 1.2, 0.3);
            this.updateChart();
        });

        document.getElementById('fit-to-screen').addEventListener('click', () => {
            this.zoom = 1;
            this.updateChart();
        });

        // Quick actions
        document.getElementById('add-dependency').addEventListener('click', () => {
            this.showAddDependencyModal();
        });

        document.getElementById('show-critical-path').addEventListener('click', () => {
            this.toggleCriticalPath();
        });

        document.getElementById('export-gantt').addEventListener('click', () => {
            this.exportChart();
        });

        // Modal events
        document.getElementById('save-dependency').addEventListener('click', () => {
            this.saveDependency();
        });
    }

    async loadData() {
        try {
            const response = await fetch('/production/api/tasks/gantt-data');
            const data = await response.json();
            
            if (data.success) {
                this.data = data;
                this.populateFilters();
                this.renderChart();
            } else {
                console.error('Failed to load Gantt data:', data.error);
            }
        } catch (error) {
            console.error('Error loading Gantt data:', error);
        }
    }

    populateFilters() {
        // Populate assignee filter
        const assignees = [...new Set(this.data.tasks.map(task => task.assigned_to_name))];
        const assigneeSelect = document.getElementById('assignee-filter');
        assigneeSelect.innerHTML = '<option value="">All Assignees</option>';
        assignees.forEach(assignee => {
            if (assignee && assignee !== 'Unassigned') {
                const option = document.createElement('option');
                option.value = assignee;
                option.textContent = assignee;
                assigneeSelect.appendChild(option);
            }
        });

        // Populate project filter
        const projects = [...new Set(this.data.tasks.map(task => task.project_id).filter(Boolean))];
        const projectSelect = document.getElementById('project-filter');
        projectSelect.innerHTML = '<option value="">All Projects</option>';
        projects.forEach(project => {
            const option = document.createElement('option');
            option.value = project;
            option.textContent = project;
            projectSelect.appendChild(option);
        });
    }

    applyFilters() {
        let filteredTasks = this.data.tasks;

        if (this.filters.status) {
            filteredTasks = filteredTasks.filter(task => task.status === this.filters.status);
        }

        if (this.filters.priority) {
            filteredTasks = filteredTasks.filter(task => task.priority === this.filters.priority);
        }

        if (this.filters.assignee) {
            filteredTasks = filteredTasks.filter(task => task.assigned_to_name === this.filters.assignee);
        }

        if (this.filters.project) {
            filteredTasks = filteredTasks.filter(task => task.project_id === this.filters.project);
        }

        this.renderChart(filteredTasks);
    }

    renderChart(tasks = null) {
        const chartData = tasks || this.data.tasks;
        
        // Clear existing chart
        this.container.selectAll('*').remove();

        if (chartData.length === 0) {
            this.container.append('div')
                .attr('class', 'text-center text-muted py-5')
                .html('<i class="fas fa-chart-bar fa-3x mb-3"></i><br>No tasks to display');
            return;
        }

        // Calculate chart dimensions
        const margin = { top: 20, right: 20, bottom: 30, left: 200 };
        const width = this.container.node().clientWidth - margin.left - margin.right;
        const height = 600 - margin.top - margin.bottom;

        // Create SVG
        const svg = this.container.append('svg')
            .attr('width', width + margin.left + margin.right)
            .attr('height', height + margin.top + margin.bottom)
            .append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);

        // Parse dates and calculate time range
        const tasksWithDates = chartData.map(task => ({
            ...task,
            start: new Date(task.start_date),
            end: task.completed_at ? new Date(task.completed_at) : 
                 task.due_date ? new Date(task.due_date) : 
                 new Date(task.start_date + 'T23:59:59')
        }));

        const timeExtent = d3.extent(tasksWithDates.flatMap(d => [d.start, d.end]));
        const timeRange = timeExtent[1] - timeExtent[0];

        // Scales
        const xScale = d3.scaleTime()
            .domain(timeExtent)
            .range([0, width]);

        const yScale = d3.scaleBand()
            .domain(chartData.map(d => d.id))
            .range([0, height])
            .padding(0.1);

        // Add axes
        const xAxis = d3.axisBottom(xScale);
        const yAxis = d3.axisLeft(yScale);

        svg.append('g')
            .attr('class', 'x-axis')
            .attr('transform', `translate(0,${height})`)
            .call(xAxis);

        svg.append('g')
            .attr('class', 'y-axis')
            .call(yAxis);

        // Add task bars
        const taskGroups = svg.selectAll('.task-group')
            .data(chartData)
            .enter()
            .append('g')
            .attr('class', 'task-group')
            .attr('transform', d => `translate(0,${yScale(d.id)})`);

        // Task bars
        taskGroups.append('rect')
            .attr('x', d => xScale(new Date(d.start_date)))
            .attr('y', 0)
            .attr('width', d => {
                const start = new Date(d.start_date);
                const end = d.completed_at ? new Date(d.completed_at) : 
                           d.due_date ? new Date(d.due_date) : 
                           new Date(d.start_date + 'T23:59:59');
                return Math.max(xScale(end) - xScale(start), 1);
            })
            .attr('height', yScale.bandwidth())
            .attr('class', d => `task-bar task-${d.status}`)
            .attr('fill', d => this.getTaskColor(d))
            .attr('stroke', d => d.is_blocked ? '#ffc107' : 'none')
            .attr('stroke-width', d => d.is_blocked ? 2 : 0)
            .style('cursor', 'pointer')
            .on('click', (event, d) => this.showTaskDetails(d))
            .on('mouseover', function(event, d) {
                d3.select(this).attr('opacity', 0.8);
                showTooltip(event, d);
            })
            .on('mouseout', function(event, d) {
                d3.select(this).attr('opacity', 1);
                hideTooltip();
            });

        // Task labels
        taskGroups.append('text')
            .attr('x', -5)
            .attr('y', yScale.bandwidth() / 2)
            .attr('dy', '0.35em')
            .attr('text-anchor', 'end')
            .attr('class', 'task-label')
            .text(d => d.title.length > 20 ? d.title.substring(0, 20) + '...' : d.title)
            .style('font-size', '12px')
            .style('fill', '#333');

        // Add dependency arrows
        this.renderDependencies(svg, xScale, yScale);

        // Add today line
        const today = new Date();
        if (today >= timeExtent[0] && today <= timeExtent[1]) {
            svg.append('line')
                .attr('x1', xScale(today))
                .attr('x2', xScale(today))
                .attr('y1', 0)
                .attr('y2', height)
                .attr('stroke', '#dc3545')
                .attr('stroke-width', 2)
                .attr('stroke-dasharray', '5,5');

            svg.append('text')
                .attr('x', xScale(today) + 5)
                .attr('y', 15)
                .attr('class', 'today-label')
                .text('Today')
                .style('font-size', '12px')
                .style('fill', '#dc3545');
        }

        // Tooltip functions
        function showTooltip(event, d) {
            const tooltip = d3.select('body').append('div')
                .attr('class', 'tooltip')
                .style('position', 'absolute')
                .style('background', 'rgba(0,0,0,0.8)')
                .style('color', 'white')
                .style('padding', '8px')
                .style('border-radius', '4px')
                .style('font-size', '12px')
                .style('pointer-events', 'none')
                .style('z-index', '1000');

            tooltip.html(`
                <strong>${d.title}</strong><br>
                Status: ${d.status}<br>
                Priority: ${d.priority}<br>
                Assignee: ${d.assigned_to_name}<br>
                Start: ${new Date(d.start_date).toLocaleDateString()}<br>
                ${d.due_date ? `Due: ${new Date(d.due_date).toLocaleDateString()}<br>` : ''}
                ${d.is_blocked ? '<span style="color: #ffc107;">⚠️ Blocked</span>' : ''}
            `);

            tooltip.style('left', (event.pageX + 10) + 'px')
                   .style('top', (event.pageY - 10) + 'px');
        }

        function hideTooltip() {
            d3.selectAll('.tooltip').remove();
        }
    }

    renderDependencies(svg, xScale, yScale) {
        const dependencyData = this.data.dependencies.filter(dep => {
            const dependentTask = this.data.tasks.find(t => t.id === dep.to);
            const prerequisiteTask = this.data.tasks.find(t => t.id === dep.from);
            return dependentTask && prerequisiteTask;
        });

        dependencyData.forEach(dep => {
            const dependentTask = this.data.tasks.find(t => t.id === dep.to);
            const prerequisiteTask = this.data.tasks.find(t => t.id === dep.from);

            if (!dependentTask || !prerequisiteTask) return;

            const x1 = xScale(new Date(prerequisiteTask.start_date)) + 
                      (xScale(new Date(prerequisiteTask.due_date || prerequisiteTask.start_date)) - 
                       xScale(new Date(prerequisiteTask.start_date)));
            const y1 = yScale(prerequisiteTask.id) + yScale.bandwidth() / 2;
            const x2 = xScale(new Date(dependentTask.start_date));
            const y2 = yScale(dependentTask.id) + yScale.bandwidth() / 2;

            // Draw arrow
            svg.append('defs').append('marker')
                .attr('id', `arrowhead-${dep.id}`)
                .attr('viewBox', '0 -5 10 10')
                .attr('refX', 8)
                .attr('refY', 0)
                .attr('markerWidth', 6)
                .attr('markerHeight', 6)
                .attr('orient', 'auto')
                .append('path')
                .attr('d', 'M0,-5L10,0L0,5')
                .attr('fill', '#6c757d');

            svg.append('line')
                .attr('x1', x1)
                .attr('y1', y1)
                .attr('x2', x2)
                .attr('y2', y2)
                .attr('stroke', '#6c757d')
                .attr('stroke-width', 2)
                .attr('marker-end', `url(#arrowhead-${dep.id})`)
                .style('opacity', 0.6);
        });
    }

    getTaskColor(task) {
        const statusColors = {
            'pending': '#6c757d',
            'in_progress': '#0d6efd',
            'completed': '#198754',
            'cancelled': '#dc3545'
        };

        let color = statusColors[task.status] || '#6c757d';

        // Add priority overlay
        if (task.priority === 'urgent') {
            color = '#dc3545';
        } else if (task.priority === 'high') {
            color = '#fd7e14';
        }

        return color;
    }

    updateChart() {
        this.container.style('transform', `scale(${this.zoom})`);
    }

    showAddDependencyModal() {
        // Populate task dropdowns
        const taskSelect = document.getElementById('dependent-task');
        const prerequisiteSelect = document.getElementById('prerequisite-task');
        
        taskSelect.innerHTML = '<option value="">Select a task</option>';
        prerequisiteSelect.innerHTML = '<option value="">Select prerequisite task</option>';
        
        this.data.tasks.forEach(task => {
            const option1 = document.createElement('option');
            option1.value = task.id;
            option1.textContent = `${task.id}: ${task.title}`;
            taskSelect.appendChild(option1);
            
            const option2 = document.createElement('option');
            option2.value = task.id;
            option2.textContent = `${task.id}: ${task.title}`;
            prerequisiteSelect.appendChild(option2);
        });

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('addDependencyModal'));
        modal.show();
    }

    async saveDependency() {
        const dependentTaskId = document.getElementById('dependent-task').value;
        const prerequisiteTaskId = document.getElementById('prerequisite-task').value;
        const dependencyType = document.getElementById('dependency-type').value;
        const lagHours = parseFloat(document.getElementById('lag-hours').value) || 0;

        if (!dependentTaskId || !prerequisiteTaskId) {
            alert('Please select both tasks');
            return;
        }

        if (dependentTaskId === prerequisiteTaskId) {
            alert('A task cannot depend on itself');
            return;
        }

        try {
            const response = await fetch(`/production/api/tasks/${dependentTaskId}/dependencies`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
                },
                body: JSON.stringify({
                    prerequisite_task_id: prerequisiteTaskId,
                    dependency_type: dependencyType,
                    lag_hours: lagHours
                })
            });

            const result = await response.json();
            
            if (result.success) {
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('addDependencyModal'));
                modal.hide();
                
                // Reload data and chart
                await this.loadData();
                
                // Show success message
                this.showNotification('Dependency added successfully!', 'success');
            } else {
                alert('Error: ' + result.error);
            }
        } catch (error) {
            console.error('Error adding dependency:', error);
            alert('Error adding dependency');
        }
    }

    toggleCriticalPath() {
        // Implementation for showing critical path
        console.log('Critical path functionality to be implemented');
    }

    exportChart() {
        // Implementation for exporting chart
        console.log('Export functionality to be implemented');
    }

    async showTaskDetails(task) {
        try {
            const response = await fetch(`/production/api/tasks/${task.id}/dependencies`);
            const data = await response.json();
            
            if (data.success) {
                const content = document.getElementById('task-details-content');
                content.innerHTML = `
                    <div class="row">
                        <div class="col-md-6">
                            <h6>Task Information</h6>
                            <table class="table table-sm">
                                <tr><td><strong>Title:</strong></td><td>${task.title}</td></tr>
                                <tr><td><strong>Status:</strong></td><td><span class="badge bg-${this.getStatusColor(task.status)}">${task.status}</span></td></tr>
                                <tr><td><strong>Priority:</strong></td><td><span class="badge bg-${this.getPriorityColor(task.priority)}">${task.priority}</span></td></tr>
                                <tr><td><strong>Assignee:</strong></td><td>${task.assigned_to_name}</td></tr>
                                <tr><td><strong>Start Date:</strong></td><td>${new Date(task.start_date).toLocaleDateString()}</td></tr>
                                ${task.due_date ? `<tr><td><strong>Due Date:</strong></td><td>${new Date(task.due_date).toLocaleDateString()}</td></tr>` : ''}
                                <tr><td><strong>Estimated Duration:</strong></td><td>${task.estimated_duration_hours} hours</td></tr>
                                ${task.actual_duration_hours ? `<tr><td><strong>Actual Duration:</strong></td><td>${task.actual_duration_hours} hours</td></tr>` : ''}
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
                                            ${dep.prerequisite_task_title}
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
                                            ${dep.dependent_task_title}
                                            <span class="badge bg-info">${dep.dependency_type}</span>
                                        </li>
                                    `).join('')}
                                </ul>
                            </div>
                        </div>
                    </div>
                    ${task.description ? `<div class="mt-3"><h6>Description</h6><p>${task.description}</p></div>` : ''}
                `;
                
                const modal = new bootstrap.Modal(document.getElementById('taskDetailsModal'));
                modal.show();
            }
        } catch (error) {
            console.error('Error loading task details:', error);
        }
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
}

// Initialize Gantt chart when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    const ganttChart = new GanttChart('#gantt-chart');
}); 