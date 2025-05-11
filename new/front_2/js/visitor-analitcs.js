/**
 * Restaurant Analytics Dashboard - Visitor Analytics Module
 * Загрузка и отображение данных для страницы аналитики посетителей
 */

// Глобальные объекты для хранения графиков
let ageDistributionChart;
let genderDistributionChart;
let visitorTrendsChart;
let visitDurationChart;
let peakHoursDetailedChart;

// Инициализация при загрузке страницы
$(document).ready(function() {
    // Инициализация вкладок
    $('#visitorTabs a').on('click', function(e) {
        e.preventDefault();
        $(this).tab('show');

        // При переключении вкладки обновляем соответствующий график
        const tabId = $(this).attr('href').substr(1);
        refreshTabContent(tabId);
    });
});

/**
 * Загрузка данных для страницы аналитики посетителей
 */
function loadVisitorAnalyticsData() {
    // Определяем активную вкладку
    const activeTab = $('#visitorTabs .nav-link.active').attr('href');
    const tabId = activeTab ? activeTab.substr(1) : 'demographics';

    // Загружаем данные для активной вкладки
    refreshTabContent(tabId);
}

/**
 * Обновление содержимого вкладки
 * @param {string} tabId - ID вкладки для обновления
 */
function refreshTabContent(tabId) {
    switch (tabId) {
        case 'demographics':
            loadDemographicsData();
            break;
        case 'trends':
            loadVisitorTrendsData();
            break;
        case 'top-visitors':
            loadTopVisitorsData();
            break;
        case 'visit-duration':
            loadVisitDurationData();
            break;
        case 'peak-hours':
            loadPeakHoursDetailedData();
            break;
        default:
            console.error('Неизвестная вкладка:', tabId);
    }
}

/**
 * Загрузка демографических данных
 */
function loadDemographicsData() {
    // Загрузка данных о распределении по возрасту
    makeApiRequest('/stats/age-distribution', {}, function(response) {
        updateAgeDistributionChart(response);
    });

    // Загрузка данных о распределении по полу
    makeApiRequest('/stats/gender-distribution', {}, function(response) {
        updateGenderDistributionChart(response);
    });
}

/**
 * Обновление графика распределения по возрасту
 * @param {Object} data - Данные о распределении по возрасту
 */
function updateAgeDistributionChart(data) {
    const ctx = document.getElementById('age-distribution-chart').getContext('2d');

    // Уничтожаем предыдущий экземпляр графика, если он существует
    if (ageDistributionChart) {
        ageDistributionChart.destroy();
    }

    // Подготавливаем данные для графика
    const labels = Object.keys(data.age_groups);
    const values = Object.values(data.age_groups);

    // Создаем цвета с градиентом от синего к красному в зависимости от возраста
    const colors = labels.map((age, index) => {
        const ratio = index / (labels.length - 1);
        const r = Math.round(13 + (220 - 13) * ratio);
        const g = Math.round(110 - 110 * ratio);
        const b = Math.round(253 - 253 * ratio);
        return `rgba(${r}, ${g}, ${b}, 0.8)`;
    });

    // Создаем новый график
    ageDistributionChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Количество посетителей',
                data: values,
                backgroundColor: colors,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        title: function(tooltipItems) {
                            return `Возрастная группа: ${tooltipItems[0].label}`;
                        },
                        label: function(context) {
                            const value = context.raw || 0;
                            const total = context.dataset.data.reduce((acc, val) => acc + val, 0);
                            const percentage = Math.round((value / total) * 100);
                            return `Посетителей: ${value} (${percentage}%)`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Количество посетителей'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Возрастные группы'
                    }
                }
            }
        }
    });
}

/**
 * Обновление графика распределения по полу
 * @param {Object} data - Данные о распределении по полу
 */
function updateGenderDistributionChart(data) {
    const ctx = document.getElementById('gender-distribution-chart').getContext('2d');

    // Уничтожаем предыдущий экземпляр графика, если он существует
    if (genderDistributionChart) {
        genderDistributionChart.destroy();
    }

    // Подготавливаем данные для графика
    const labels = Object.keys(data.gender);
    const values = Object.values(data.gender);

    // Цвета для мужчин и женщин
    const colors = [
        'rgba(13, 110, 253, 0.8)',  // мужчины - синий
        'rgba(214, 51, 132, 0.8)'   // женщины - розовый
    ];

    // Создаем новый график
    genderDistributionChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.raw || 0;
                            const total = context.dataset.data.reduce((acc, val) => acc + val, 0);
                            const percentage = Math.round((value / total) * 100);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Загрузка данных о трендах посещений
 */
function loadVisitorTrendsData() {
    makeApiRequest('/stats/visitor-trends', {}, function(response) {
        updateVisitorTrendsChart(response);
    });
}

/**
 * Обновление графика трендов посещений
 * @param {Object} data - Данные о трендах посещений
 */
function updateVisitorTrendsChart(data) {
    const ctx = document.getElementById('visitor-trends-chart').getContext('2d');

    // Уничтожаем предыдущий экземпляр графика, если он существует
    if (visitorTrendsChart) {
        visitorTrendsChart.destroy();
    }

    // Подготавливаем данные для графика
    const dates = data.trends.map(item => moment(item.date).format('DD.MM.YYYY'));
    const uniqueVisitors = data.trends.map(item => item.unique_visitors);
    const repeatVisitors = data.trends.map(item => item.repeat_visitors);
    const totalVisitors = data.trends.map(item => item.total_visitors);

    // Вычисляем скользящее среднее для общего числа посетителей
    const movingAverage = calculateMovingAverage(totalVisitors, 3);

    // Создаем новый график
    visitorTrendsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [
                {
                    label: 'Общее число посетителей',
                    data: totalVisitors,
                    backgroundColor: 'rgba(13, 110, 253, 0.1)',
                    borderColor: 'rgba(13, 110, 253, 1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true
                },
                {
                    label: 'Уникальные посетители',
                    data: uniqueVisitors,
                    backgroundColor: 'rgba(25, 135, 84, 0)',
                    borderColor: 'rgba(25, 135, 84, 1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: false
                },
                {
                    label: 'Повторные посещения',
                    data: repeatVisitors,
                    backgroundColor: 'rgba(220, 53, 69, 0)',
                    borderColor: 'rgba(220, 53, 69, 1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: false
                },
                {
                    label: 'Тренд (скользящее среднее)',
                    data: movingAverage,
                    backgroundColor: 'rgba(255, 193, 7, 0)',
                    borderColor: 'rgba(255, 193, 7, 1)',
                    borderWidth: 3,
                    borderDash: [5, 5],
                    tension: 0.3,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    position: 'top'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Количество посетителей'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Дата'
                    }
                }
            }
        }
    });
}

/**
 * Расчет скользящего среднего
 * @param {Array} data - Массив значений
 * @param {number} window - Размер окна
 * @returns {Array} Массив скользящих средних значений
 */
function calculateMovingAverage(data, window) {
    const result = [];

    // Для первых (window-1) элементов просто копируем исходные данные
    for (let i = 0; i < window - 1; i++) {
        result.push(data[i]);
    }

    // Вычисляем скользящее среднее
    for (let i = window - 1; i < data.length; i++) {
        let sum = 0;
        for (let j = 0; j < window; j++) {
            sum += data[i - j];
        }
        result.push(sum / window);
    }

    return result;
}

/**
 * Загрузка данных о топ-посетителях
 */
function loadTopVisitorsData() {
    makeApiRequest('/stats/top-visitors', {}, function(response) {
        updateTopVisitorsTable(response);
    });
}

/**
 * Обновление таблицы топ-посетителей
 * @param {Object} data - Данные о топ-посетителях
 */
function updateTopVisitorsTable(data) {
    const tableBody = $('#top-visitors-table');
    tableBody.empty();

    if (!data.visitors || data.visitors.length === 0) {
        tableBody.append('<tr><td colspan="6" class="text-center">Нет данных</td></tr>');
        return;
    }

    // Заполняем таблицу данными
    data.visitors.forEach((visitor, index) => {
        const personTypeClass = getPersonTypeColorClass(visitor.person_type);

        const row = $(`
            <tr>
                <td>${index + 1}</td>
                <td>${visitor.track_id}</td>
                <td>${visitor.name || 'Неизвестно'}</td>
                <td><span class="badge ${personTypeClass}">${visitor.person_type}</span></td>
                <td>${visitor.visit_count}</td>
                <td>${visitor.last_visit ? formatDateTime(visitor.last_visit) : 'Н/Д'}</td>
            </tr>
        `);

        tableBody.append(row);
    });
}

/**
 * Загрузка данных о длительности визитов
 */
function loadVisitDurationData() {
    makeApiRequest('/stats/visit-duration', {}, function(response) {
        updateVisitDurationChart(response);
    });
}

/**
 * Обновление графика длительности визитов
 * @param {Object} data - Данные о длительности визитов
 */
function updateVisitDurationChart(data) {
    const ctx = document.getElementById('visit-duration-chart').getContext('2d');

    // Уничтожаем предыдущий экземпляр графика, если он существует
    if (visitDurationChart) {
        visitDurationChart.destroy();
    }

    // Подготавливаем данные для графика
    const labels = Object.keys(data.duration_groups).map(key => {
        // Преобразуем ключи вида "0-5" в "0-5 минут"
        return `${key} минут`;
    });

    const values = Object.values(data.duration_groups);

    // Создаем цвета с градиентом в зависимости от длительности
    const colors = values.map((value, index) => {
        const ratio = index / (values.length - 1);
        return `rgba(13, ${110 + Math.round(90 * ratio)}, 253, 0.8)`;
    });

    // Создаем новый график
    visitDurationChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Количество посетителей',
                data: values,
                backgroundColor: colors,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        title: function(tooltipItems) {
                            return `Длительность визита: ${tooltipItems[0].label}`;
                        },
                        label: function(context) {
                            const value = context.raw || 0;
                            const total = context.dataset.data.reduce((acc, val) => acc + val, 0);
                            const percentage = Math.round((value / total) * 100);
                            return `Посетителей: ${value} (${percentage}%)`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Количество посетителей'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Длительность визита'
                    }
                }
            }
        }
    });
}

/**
 * Загрузка детальных данных о пиковых часах
 */
function loadPeakHoursDetailedData() {
    makeApiRequest('/stats/peak-hours-detailed', {}, function(response) {
        updatePeakHoursDetailedChart(response);
    });
}

/**
 * Обновление графика пиковых часов (детализированного)
 * @param {Object} data - Детальные данные о пиковых часах
 */
function updatePeakHoursDetailedChart(data) {
    const ctx = document.getElementById('peak-hours-detailed-chart').getContext('2d');

    // Уничтожаем предыдущий экземпляр графика, если он существует
    if (peakHoursDetailedChart) {
        peakHoursDetailedChart.destroy();
    }

    // Подготавливаем данные для графика
    const hours = [];
    for (let i = 0; i < 24; i++) {
        hours.push(`${i.toString().padStart(2, '0')}:00`);
    }

    const weekdays = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'];

    // Создаем наборы данных для каждого дня недели
    const datasets = weekdays.map((day, index) => {
        return {
            label: day,
            data: hours.map(hour => data.hourly_data[day] ? (data.hourly_data[day][hour] || 0) : 0),
            backgroundColor: generateChartColors(1, 0.8)[0],
            borderColor: generateChartColors(1, 1)[0],
            borderWidth: 1,
            hidden: index > 0 // По умолчанию показываем только Понедельник
        };
    });

    // Создаем новый график
    peakHoursDetailedChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: hours,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    onClick: function(e, legendItem, legend) {
                        // Изменено стандартное поведение легенды, чтобы допускать отображение только одного дня
                        const index = legendItem.datasetIndex;
                        const ci = legend.chart;

                        // Скрываем все наборы данных
                        for (let i = 0; i < ci.data.datasets.length; i++) {
                            ci.data.datasets[i].hidden = true;
                        }

                        // Показываем выбранный набор данных
                        ci.data.datasets[index].hidden = false;

                        ci.update();
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Количество посетителей'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Время (часы)'
                    }
                }
            }
        }
    });
}