// Shared Failure Report JavaScript

// Colors for charts
const reportColors = [
    'rgba(255, 99, 132, 0.8)',
    'rgba(54, 162, 235, 0.8)',
    'rgba(255, 206, 86, 0.8)',
    'rgba(75, 192, 192, 0.8)',
    'rgba(153, 102, 255, 0.8)',
    'rgba(255, 159, 64, 0.8)',
    'rgba(199, 199, 199, 0.8)',
    'rgba(83, 102, 255, 0.8)',
];

const reportBorderColors = [
    'rgba(255, 99, 132, 1)',
    'rgba(54, 162, 235, 1)',
    'rgba(255, 206, 86, 1)',
    'rgba(75, 192, 192, 1)',
    'rgba(153, 102, 255, 1)',
    'rgba(255, 159, 64, 1)',
    'rgba(199, 199, 199, 1)',
    'rgba(83, 102, 255, 1)',
];

let dailyTrendChartInstance = null;
let paretoChartInstances = {};
let selectedSection = '';

// Display daily trend chart
function displayDailyTrendChart(data) {
    const dailyData = data.daily_data || {};
    const dates = Object.keys(dailyData).sort();
    const machineTypeNames = data.machine_type_names || [];

    if (dates.length === 0) {
        document.getElementById('dailyTrendChart').parentElement.innerHTML = '<p style="text-align: center; color: #999; padding: 20px;">No daily data available</p>';
        return;
    }

    const datasets = [];
    machineTypeNames.forEach((mtName, index) => {
        const seriesData = dates.map(date => dailyData[date][mtName] || 0);
        datasets.push({
            label: mtName,
            data: seriesData,
            backgroundColor: reportColors[index % reportColors.length],
            borderColor: reportBorderColors[index % reportBorderColors.length],
            borderWidth: 1
        });
    });

    const ctx = document.getElementById('dailyTrendChart').getContext('2d');
    
    if (dailyTrendChartInstance) {
        dailyTrendChartInstance.destroy();
    }

    dailyTrendChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: dates,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'x',
            scales: {
                x: {
                    stacked: true,
                    title: {
                        display: true,
                        text: 'Date'
                    }
                },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    },
                    title: {
                        display: true,
                        text: 'Number of Failures'
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: false,
                        padding: 15,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            label += context.parsed.y;
                            return label;
                        },
                        afterLabel: function(context) {
                            let total = 0;
                            context.chart.data.datasets.forEach(dataset => {
                                const value = dataset.data[context.dataIndex];
                                if (typeof value !== 'undefined') {
                                    total += value;
                                }
                            });
                            return 'Total: ' + total;
                        }
                    }
                }
            }
        }
    });
}



// Display daily details table
function displayDailyDetailsTable(data) {
    const dailyData = data.daily_data || {};
    const dates = Object.keys(dailyData).sort();
    const tableBody = document.getElementById('dailyDetailsTableBody');

    if (dates.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No daily data available.</td></tr>';
        return;
    }

    // Group failures by date
    const failuresByDate = {};
    data.failures.forEach(failure => {
        const date = failure.start_date.split(' ')[0]; // Get date part
        if (!failuresByDate[date]) {
            failuresByDate[date] = { day: 0, night: 0, categories: {} };
        }
        
        // Check shift
        const hour = parseInt(failure.start_date.split(' ')[1].split(':')[0]);
        if (hour >= 6 && hour < 18) {
            failuresByDate[date].day += 1;
        } else {
            failuresByDate[date].night += 1;
        }
        
        // Track top category
        const category = failure.category_level_0 || 'Uncategorized';
        failuresByDate[date].categories[category] = (failuresByDate[date].categories[category] || 0) + 1;
    });

    let htmlContent = '';
    dates.forEach(date => {
        const dayOfWeek = new Date(date).toLocaleDateString('en-US', { weekday: 'long' });
        const dayData = failuresByDate[date] || { day: 0, night: 0, categories: {} };
        const totalFailures = dayData.day + dayData.night;
        
        // Get top category
        let topCategory = 'N/A';
        let topCount = 0;
        Object.entries(dayData.categories).forEach(([category, count]) => {
            if (count > topCount) {
                topCount = count;
                topCategory = category;
            }
        });

        htmlContent += `
            <tr class="daily-detail-row">
                <td><strong>${date}</strong></td>
                <td>${dayOfWeek}</td>
                <td>
                    <span class="clickable-number" onclick="showDailyFailures('${date}', 'all')">
                        ${totalFailures}
                    </span>
                </td>
                <td>
                    <span class="clickable-number" onclick="showDailyFailures('${date}', 'Day')">
                        ${dayData.day}
                    </span>
                </td>
                <td>
                    <span class="clickable-number" onclick="showDailyFailures('${date}', 'Night')">
                        ${dayData.night}
                    </span>
                </td>
                <td>
                    ${totalFailures > 0 ? `<span class="badge bg-info">${topCategory}</span> (${topCount})` : '<span class="badge bg-secondary">No Failures</span>'}
                </td>
            </tr>
        `;
    });

    tableBody.innerHTML = htmlContent;
}

// Show daily failures modal
function showDailyFailures(date, shift) {
    const modal = new bootstrap.Modal(document.getElementById('failureModal'));
    const title = document.getElementById('failureModalTitle');
    const body = document.getElementById('failureModalBody');

    let shiftLabel = 'All Shifts';
    if (shift === 'Day') shiftLabel = 'Day Shift';
    if (shift === 'Night') shiftLabel = 'Night Shift';

    title.textContent = `Failures - ${date} (${shiftLabel})`;
    body.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>';

    let apiUrl = `/maintenance/api/report/daily-failures/${date}/?shift=${shift}`;
    if (selectedSection) {
        apiUrl += `&section=${encodeURIComponent(selectedSection)}`;
    }

    fetch(apiUrl)
        .then(response => response.json())
        .then(data => {
            let htmlContent = '';

            if (!data.failures || data.failures.length === 0) {
                htmlContent = '<div class="alert alert-warning">No failures found for this date and shift.</div>';
            } else {
                let sectionLabel = data.section ? ` (${data.section})` : '';
                htmlContent = `
                    <div class="alert alert-info mb-3">
                        <strong>📅 Date:</strong> ${data.date} | 
                        <strong>📊 Total Failures:</strong> ${data.total_count}${sectionLabel}
                    </div>
                    <div class="failure-table-container">
                        <table class="failure-modal-table">
                            <thead>
                                <tr>
                                    <th style="width: 15%;">Machine & Time</th>
                                    <th style="width: 10%;">Category</th>
                                    <th style="width: 15%;">Failure Type</th>
                                    <th style="width: 25%;">Details</th>
                                    <th style="width: 30%;">Root Cause & Action</th>
                                    <th style="width: 5%;">Status</th>
                                </tr>
                            </thead>
                            <tbody>
                `;
                
                data.failures.forEach((failure) => {
                    const statusClass = failure.status === 'OPEN' ? 'open' : 'closed';
                    const rootcauseHtml = failure.rootcause ? 
                        `<div class="rootcause-label">🔍 Root Cause:</div><div class="rootcause-text">${failure.rootcause}</div>` : '';
                    const actionHtml = failure.repair_action ? 
                        `<div class="action-label" style="margin-top: 8px;">🔧 Action:</div><div class="action-text">${failure.repair_action}</div>` : '';
                    const rootcauseAction = rootcauseHtml || actionHtml ? `${rootcauseHtml}${actionHtml}` : '<em>No details</em>';
                    
                    htmlContent += `
                        <tr>
                            <td class="machine-datetime-cell">
                                <a href="/maintenance/reports/machine/${failure.machine_name}/" class="machine-name" target="_blank">
                                    ${failure.machine_name}
                                </a>
                                <div class="machine-datetime">
                                    ⏰ ${failure.start_date}
                                </div>
                            </td>
                            <td>
                                <span class="failure-category-badge">${failure.category_level_0}</span>
                            </td>
                            <td class="details-text">
                                ${failure.failure_category || '<em>N/A</em>'}
                            </td>
                            <td class="details-text">
                                ${failure.details || '<em>No details</em>'}
                            </td>
                            <td>
                                ${rootcauseAction}
                            </td>
                            <td>
                                <span class="failure-status ${statusClass}">${failure.status}</span>
                            </td>
                        </tr>
                    `;
                });

                htmlContent += `
                            </tbody>
                        </table>
                    </div>
                    <div class="alert alert-success mt-3">
                        <strong>✅ Total Failures on ${data.date}:</strong> ${data.total_count} failure(s)
                    </div>
                `;
            }

            body.innerHTML = htmlContent;
            modal.show();
        })
        .catch(error => {
            body.innerHTML = '<div class="alert alert-danger">Error loading failure data: ' + error.message + '</div>';
            modal.show();
        });
}

// Display pareto charts
function displayParetoCharts(data) {
    const paretoData = data.pareto_data || {};
    const machineTypeNames = data.machine_type_names || [];
    const failures = data.failures || [];
    const container = document.getElementById('paretoChartsContainer');

    container.innerHTML = '';

    machineTypeNames.forEach((mtName, mtIndex) => {
        const mtParetoData = paretoData[mtName] || [];
        
        const cardDiv = document.createElement('div');
        cardDiv.className = 'pareto-card';
        cardDiv.innerHTML = `
            <div class="pareto-card-title">${mtName}</div>
            <div class="pareto-mini-chart">
                <canvas id="pareto-chart-${mtName}"></canvas>
            </div>
        `;
        container.appendChild(cardDiv);

        if (mtParetoData.length === 0) {
            cardDiv.querySelector('.pareto-mini-chart').innerHTML = '<p style="text-align: center; color: #999; padding: 20px;">No data available</p>';
            return;
        }

        const categories = mtParetoData.map(item => item.category);
        const counts = mtParetoData.map(item => item.count);
        const cumulativePercentages = mtParetoData.map(item => item.cumulative_percentage);

        const ctx = document.getElementById(`pareto-chart-${mtName}`).getContext('2d');
        
        paretoChartInstances[mtName] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: categories,
                datasets: [
                    {
                        label: 'Failures',
                        data: counts,
                        backgroundColor: reportColors[mtIndex % reportColors.length],
                        borderColor: reportBorderColors[mtIndex % reportBorderColors.length],
                        borderWidth: 1,
                        yAxisID: 'y',
                        order: 2
                    },
                    {
                        label: 'Cumulative %',
                        data: cumulativePercentages,
                        borderColor: '#e74c3c',
                        borderWidth: 2,
                        type: 'line',
                        fill: false,
                        yAxisID: 'y1',
                        order: 1,
                        pointRadius: 5,
                        pointHoverRadius: 7,
                        pointBackgroundColor: '#e74c3c',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                onClick: function(event, activeElements) {
                    // Handle click on pareto chart
                    if (activeElements.length > 0) {
                        const elementIndex = activeElements[0].index;
                        const categoryName = categories[elementIndex];
                        showCategoryFailuresModal(categoryName, mtName, failures);
                    }
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Failure Count'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Cumulative %'
                        },
                        grid: {
                            drawOnChartArea: false
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                if (context.dataset.label === 'Failures') {
                                    return context.dataset.label + ': ' + context.parsed.y;
                                } else {
                                    return context.dataset.label + ': ' + context.parsed.y.toFixed(1) + '%';
                                }
                            }
                        }
                    }
                }
            }
        });
    });
}


// Update displaySharedReport to add search listener
function displaySharedReport(data, summaryData) {
    // Store failures globally for searching
    allFailures = data.failures || [];
    
    // Update summary cards
    document.getElementById('totalFailuresDisplay').textContent = data.total_count || 0;
    document.getElementById('avgMTTRDisplay').textContent = (data.avg_mttr_hours || 0).toFixed(1) + 'h';
    document.getElementById('dateRangeDisplay').textContent = summaryData.dateRange;
    document.getElementById('sectionDisplay').textContent = summaryData.section || 'All';

    // Display charts and table
    displayDailyTrendChart(data);
    displayParetoCharts(data);
    displayDailyDetailsTable(data);
    
    // Add search listener to base search box
    addMachineSearchListener();
}

// Add search listener
function addMachineSearchListener() {
    const searchBox = document.getElementById('machineSearchBox');
    if (searchBox) {
        searchBox.addEventListener('input', function(e) {
            searchMachinesByName(e.target.value);
        });
    }
}

// Search machines by name - FROM ENTIRE SYSTEM
function searchMachinesByName(searchText) {
    const searchLower = searchText.toLowerCase().trim();
    
    if (!searchLower || searchLower.length < 2) {
        // Clear search results
        document.getElementById('machineSearchResults').style.display = 'none';
        return;
    }
    
    // Show loading state
    const resultsDiv = document.getElementById('machineSearchResults');
    const listDiv = document.getElementById('matchingMachinesList');
    listDiv.innerHTML = '<div class="text-center"><div class="spinner-border spinner-border-sm" role="status"><span class="visually-hidden">Loading...</span></div> Searching...</div>';
    resultsDiv.style.display = 'block';
    
    // Fetch from API - search entire system
    fetch(`/maintenance/api/search-machines/?q=${encodeURIComponent(searchText)}`)
        .then(response => response.json())
        .then(data => {
            const machines = data.machines || [];
            
            if (machines.length === 0) {
                listDiv.innerHTML = '<div class="alert alert-warning mb-0">No machines found matching "<strong>' + searchText + '</strong>"</div>';
                resultsDiv.style.display = 'block';
            } else {
                let html = '<div class="row">';
                
                machines.forEach(machine => {
                    html += `
                        <div class="col-md-3 mb-2">
                            <div class="card border-info h-100">
                                <div class="card-body p-3">
                                    <h6 class="card-title text-info mb-2">
                                        <a href="/maintenance/reports/machine/${machine.name}/" target="_blank" class="text-info" style="text-decoration: none;">
                                            <strong>${machine.name}</strong> 🔗
                                        </a>
                                    </h6>
                                    <small class="text-muted d-block">
                                        <strong>Machine Type:</strong> ${machine.machine_type}
                                    </small>
                                    <small class="text-muted d-block">
                                        <strong>Section:</strong> ${machine.section}
                                    </small>
                                    <div class="mt-2">
                                        <button class="btn btn-sm btn-outline-info w-100" onclick="window.open('/maintenance/reports/machine/${machine.name}/', '_blank')">
                                            View Report
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                });
                
                html += '</div>';
                listDiv.innerHTML = html;
                resultsDiv.style.display = 'block';
            }
        })
        .catch(error => {
            listDiv.innerHTML = '<div class="alert alert-danger mb-0">Error searching machines: ' + error.message + '</div>';
            resultsDiv.style.display = 'block';
        });
}

// Clear search
function clearMachineSearch() {
    document.getElementById('machineSearchBox').value = '';
    document.getElementById('machineSearchResults').style.display = 'none';
}

// Show category failures in modal
function showCategoryFailuresModal(categoryName, machineTypeName, failures) {
    // Filter failures for this category and machine type
    const categoryFailures = failures.filter(f => 
        f.category_level_0 === categoryName && f.machine_type === machineTypeName
    );

    const modal = new bootstrap.Modal(document.getElementById('failureModal'));
    const body = document.getElementById('failureModalBody');
    const title = document.getElementById('failureModalTitle');

    title.textContent = `Failures - ${machineTypeName} / ${categoryName}`;

    let htmlContent = `
        <div class="summary-section">
            <strong>🔧 Machine Type:</strong> ${machineTypeName} | 
            <strong>📋 Category:</strong> ${categoryName} | 
            <strong>📊 Total Failures:</strong> ${categoryFailures.length}
        </div>
    `;

    if (categoryFailures.length === 0) {
        htmlContent += '<div class="alert alert-info">No failures found for this category.</div>';
        body.innerHTML = htmlContent;
        modal.show();
        return;
    }

    // Calculate failure type distribution for pie chart
    const failureTypeCount = {};
    categoryFailures.forEach(f => {
        const fType = f.failure_category || 'N/A';
        failureTypeCount[fType] = (failureTypeCount[fType] || 0) + 1;
    });

    const failureTypes = Object.keys(failureTypeCount);
    const failureTypeCounts = Object.values(failureTypeCount);

    // Generate random colors for pie chart
    const colors = generateChartColors(failureTypes.length);

    htmlContent += `
        <div class="row mb-4">
            <div class="col-md-6">
                <h6 class="mb-3">📊 Failure Type Distribution</h6>
                <canvas id="failureTypePieChart" style="max-height: 250px;"></canvas>
            </div>
            <div class="col-md-6">
                <h6 class="mb-3">📋 Failure Type Summary</h6>
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>Failure Type</th>
                            <th>Count</th>
                            <th>%</th>
                        </tr>
                    </thead>
                    <tbody>
    `;

    failureTypes.forEach((fType, idx) => {
        const count = failureTypeCount[fType];
        const percentage = ((count / categoryFailures.length) * 100).toFixed(1);
        htmlContent += `
            <tr>
                <td>
                    <span class="badge" style="background-color: ${colors[idx]};">${fType}</span>
                </td>
                <td><strong>${count}</strong></td>
                <td>${percentage}%</td>
            </tr>
        `;
    });

    htmlContent += `
                    </tbody>
                </table>
            </div>
        </div>

        <hr>

        <div class="failure-table-container">
            <table class="failure-modal-table">
                <thead>
                    <tr>
                        <th style="width: 15%;">Machine & Time</th>
                        <th style="width: 10%;">Category</th>
                        <th style="width: 15%;">Failure Type</th>
                        <th style="width: 25%;">Details</th>
                        <th style="width: 30%;">Root Cause & Action</th>
                        <th style="width: 5%;">Status</th>
                    </tr>
                </thead>
                <tbody>
    `;

    categoryFailures.forEach((failure) => {
        const statusClass = failure.status === 'OPEN' ? 'open' : 'closed';
        const rootcauseHtml = failure.rootcause ? 
            `<div class="rootcause-label">🔍 Root Cause:</div><div class="rootcause-text">${failure.rootcause}</div>` : '';
        const actionHtml = failure.repair_action ? 
            `<div class="action-label" style="margin-top: 8px;">🔧 Action:</div><div class="action-text">${failure.repair_action}</div>` : '';
        const rootcauseAction = rootcauseHtml || actionHtml ? `${rootcauseHtml}${actionHtml}` : '<em>No details</em>';

        htmlContent += `
            <tr>
                <td class="machine-datetime-cell">
                    <a href="/maintenance/reports/machine/${failure.machine_name}/" class="machine-name" target="_blank">
                        ${failure.machine_name}
                    </a>
                    <div class="machine-datetime">
                        ⏰ ${failure.start_date}
                    </div>
                </td>
                <td>
                    <span class="failure-category-badge">${failure.category_level_0}</span>
                </td>
                <td class="details-text">
                    ${failure.failure_category || '<em>N/A</em>'}
                </td>
                <td class="details-text">
                    ${failure.details || '<em>No details</em>'}
                </td>
                <td>
                    ${rootcauseAction}
                </td>
                <td>
                    <span class="failure-status ${statusClass}">${failure.status}</span>
                </td>
            </tr>
        `;
    });

    htmlContent += `
                </tbody>
            </table>
        </div>
        <div class="alert alert-success mt-3">
            <strong>✅ Total Failures:</strong> ${categoryFailures.length} failure(s)
        </div>
    `;

    body.innerHTML = htmlContent;
    modal.show();

    // Draw the pie chart after modal is shown
    setTimeout(() => {
        drawFailureTypePieChart(failureTypes, failureTypeCounts, colors);
    }, 100);
}

// Draw failure type pie chart
function drawFailureTypePieChart(failureTypes, failureTypeCounts, colors) {
    const ctx = document.getElementById('failureTypePieChart');
    if (!ctx) {
        console.log('DEBUG: failureTypePieChart canvas not found');
        return;
    }

    // Destroy existing chart if it exists
    if (window.failureTypePieChartInstance) {
        window.failureTypePieChartInstance.destroy();
    }

    window.failureTypePieChartInstance = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: failureTypes,
            datasets: [{
                data: failureTypeCounts,
                backgroundColor: colors,
                borderColor: '#fff',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        font: {
                            size: 11
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return label + ': ' + value + ' (' + percentage + '%)';
                        }
                    }
                }
            }
        }
    });
}

// Generate chart colors
function generateChartColors(count) {
    const baseColors = [
        '#667eea', '#764ba2', '#f093fb', '#4facfe', '#00f2fe',
        '#43e97b', '#38f9d7', '#fa709a', '#fee140', '#30b0fe',
        '#e0b0ff', '#a8edea', '#fed6e3', '#ffeaa7', '#fab1a0'
    ];

    const colors = [];
    for (let i = 0; i < count; i++) {
        colors.push(baseColors[i % baseColors.length]);
    }
    return colors;
}