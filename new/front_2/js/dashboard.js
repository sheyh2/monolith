/**
 * Restaurant Analytics Dashboard - Dashboard Module
 * Загрузка и отображение данных для главной страницы дашборда
 */

// Глобальные объекты для хранения графиков
let visitorsTrendChart;
let emotionsChart;
let peakHoursChart;
let demographicsChart;

// Инициализация при загрузке страницы
$(document).ready(function() {
    // Графики инициализируются при первой загрузке данных
});

/**
 * Загрузка данных для дашборда
 */
function loadDashboardData() {
    // Загрузка основных статистических данных
    loadOverallStats();

    // Загрузка данных для графиков
    loadVisitorsTrendData();
    loadEmotionsDistributionData();
    loadPeakHoursData();
    loadDemographicsData();
}

/**
 * Загрузка общей статистики
 */
function loadOverallStats() {
    makeApiRequest('/stats/overall', {}, function(response) {
        // Обновляем KPI карточки
        $('#total-visitors').text(response.total_visitors || 0);
        $('#unique-visitors').text(response.unique_visitors || 0);
        $('#avg-age').text(response.average_age ? response.average_age.toFixed(1) : 0);
        $('#common-emotion').text(response.most_common_emotion || '-');
    });
}

/**
 * Загрузка данных тренда посетителей
 */
function loadVisitorsTrendData() {
    // Получаем данные временного ряда
    makeApiRequest('/stats/timeseries', {}, function(response) {
        // Преобразуем данные для графика
        const labels = response.data.map(item => moment(item.date).format('DD.MM'));
        const visitorData = response.data.map(item => item.visitors_count);

        // Обновляем или создаем график
        updateVisitorsTrendChart(labels, visitorData);
    });
}

/**
 * Обновление или создание графика тренда посетителей
 * @param {Array} labels - Метки оси X (даты)
 * @param {Array} data - Данные о количестве посетителей
 */
function updateVisitorsTrendChart(labels, data) {
    const ctx = document.getElementById('visitors-trend-chart').getContext('2d');

    // Уничтожаем предыдущий экземпляр графика, если он существует
    if (visitorsTrendChart) {
        visitorsTrendChart.destroy();
    }

    // Создаем новый график
    visitorsTrendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Количество посетителей',
                data: data,
                backgroundColor: 'rgba(13, 110, 253, 0.2)',
                borderColor: 'rgba(13, 110, 253, 1)',
                borderWidth: 2,
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
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
 * Загрузка данных о распределении эмоций посетителей
 */
function loadEmotionsDistributionData() {
    makeApiRequest('/stats/emotions', {}, function(response) {
        // Преобразуем данные для графика
        const labels = [];
        const data = [];
        const colors = [];

        // Цвета для разных эмоций
        const emotionColors = {
            'happy': 'rgba(25, 135, 84, 0.8)',
            'neutral': 'rgba(108, 117, 125, 0.8)',
            'sad': 'rgba(13, 202, 240, 0.8)',
            'angry': 'rgba(220, 53, 69, 0.8)',
            'surprised': 'rgba(255, 193, 7, 0.8)'
        };

        // Заполняем данные для графика
        for (const emotion in response.emotions) {
            labels.push(emotion);
            data.push(response.emotions[emotion]);
            colors.push(emotionColors[emotion.toLowerCase()] || 'rgba(108, 117, 125, 0.8)');
        }

        // Обновляем или создаем график
        updateEmotionsChart(labels, data, colors);
    });
}

/**
 * Обновление или создание графика распределения эмоций
 * @param {Array} labels - Названия эмоций
 * @param {Array} data - Количество каждой эмоции
 * @param {Array} colors - Цвета для каждой эмоции
 */
function updateEmotionsChart(labels, data, colors) {
    const ctx = document.getElementById('emotions-chart').getContext('2d');

    // Уничтожаем предыдущий экземпляр графика, если он существует
    if (emotionsChart) {
        emotionsChart.destroy();
    }

    // Создаем новый график
    emotionsChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
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
 * Загрузка данных о пиковых часах посещений
 */
function loadPeakHoursData() {
    makeApiRequest('/stats/peak-hours', {}, function(response) {
        const labels = [];
        const data = [];

        // Преобразуем данные для графика
        for (let hour = 0; hour < 24; hour++) {
            const hourString = hour.toString().padStart(2, '0') + ':00';
            labels.push(hourString);
            data.push(response.hours[hour] || 0);
        }

        // Обновляем или создаем график
        updatePeakHoursChart(labels, data);
    });
}

/**
 * Обновление или создание графика пиковых часов
 * @param {Array} labels - Метки времени (часы)
 * @param {Array} data - Количество посетителей по часам
 */
function updatePeakHoursChart(labels, data) {
    const ctx = document.getElementById('peak-hours-chart').getContext('2d');

    // Уничтожаем предыдущий экземпляр графика, если он существует
    if (peakHoursChart) {
        peakHoursChart.destroy();
    }

    // Находим максимальное значение для выделения пиковых часов
    const maxValue = Math.max(...data);
    const colors = data.map(value => value === maxValue ? 'rgba(220, 53, 69, 0.8)' : 'rgba(13, 110, 253, 0.8)');

    // Создаем новый график
    peakHoursChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Количество посетителей',
                data: data,
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
                            return tooltipItems[0].label;
                        },
                        label: function(context) {
                            return `Посетителей: ${context.raw}`;
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
                        text: 'Время (часы)'
                    }
                }
            }
        }
    });
}

/**
 * Загрузка демографических данных о посетителях
 */
function loadDemographicsData() {
    makeApiRequest('/stats/demographics', {}, function(response) {
        // Получаем данные о поле посетителей
        const genderLabels = Object.keys(response.gender);
        const genderData = genderLabels.map(key => response.gender[key]);

        // Получаем данные о возрастных группах
        const ageLabels = Object.keys(response.age_groups);
        const ageData = ageLabels.map(key => response.age_groups[key]);

        // Обновляем или создаем график
        updateDemographicsChart(genderLabels, genderData, ageLabels, ageData);
    });
}

/**
 * Обновление или создание графика демографических данных
 * @param {Array} genderLabels - Метки пола
 * @param {Array} genderData - Данные по полу
 * @param {Array} ageLabels - Метки возрастных групп
 * @param {Array} ageData - Данные по возрастным группам
 */
function updateDemographicsChart(genderLabels, genderData, ageLabels, ageData) {
    const ctx = document.getElementById('demographics-chart').getContext('2d');

    // Уничтожаем предыдущий экземпляр графика, если он существует
    if (demographicsChart) {
        demographicsChart.destroy();
    }

    // Создаем новый график
    demographicsChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ageLabels,
            datasets: [{
                label: 'Мужчины',
                data: ageData.map(value => value * (genderData[0] / (genderData[0] + genderData[1]))),
                backgroundColor: 'rgba(13, 110, 253, 0.8)',
                borderWidth: 1,
                stack: 'Stack 0'
            }, {
                label: 'Женщины',
                data: ageData.map(value => value * (genderData[1] / (genderData[0] + genderData[1]))),
                backgroundColor: 'rgba(214, 51, 132, 0.8)',
                borderWidth: 1,
                stack: 'Stack 0'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top'
                },
                tooltip: {
                    callbacks: {
                        title: function(tooltipItems) {
                            return `Возрастная группа: ${tooltipItems[0].label}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    stacked: true,
                    title: {
                        display: true,
                        text: 'Количество посетителей'
                    }
                },
                x: {
                    stacked: true,
                    title: {
                        display: true,
                        text: 'Возрастные группы'
                    }
                }
            }
        }
    });
}