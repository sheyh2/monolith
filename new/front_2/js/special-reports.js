/**
 * Restaurant Analytics Dashboard - Special Reports Module
 * Загрузка и отображение данных для страницы специальных отчетов
 */

// Глобальные объекты для хранения графиков
let celebrityImpactChart;
let satisfactionCorrelationChart;
let periodComparisonChart;

// Инициализация при загрузке страницы
$(document).ready(function() {
    // Инициализация вкладок
    $('#specialReportsTabs a').on('click', function(e) {
        e.preventDefault();
        $(this).tab('show');

        // При переключении вкладки обновляем соответствующий график
        const tabId = $(this).attr('href').substr(1);
        refreshTabContent(tabId);
    });

    // Инициализация выборщиков дат для сравнения периодов
    $('#period-1-date-range, #period-2-date-range').datepicker({
        format: 'dd.mm.yyyy',
        language: 'ru',
        autoclose: true,
        clearBtn: true,
        todayHighlight: true,
        orientation: 'bottom',
        range: true
    });

    // Устанавливаем значения по умолчанию для периодов сравнения
    const twoWeeksAgo = moment().subtract(14, 'days').toDate();
    const oneWeekAgo = moment().subtract(7, 'days').toDate();
    const today = moment().toDate();

    $('#period-1-date-range').datepicker('setDate', [twoWeeksAgo, oneWeekAgo]);
    $('#period-2-date-range').datepicker('setDate', [oneWeekAgo, today]);

    // Обработчик кнопки сравнения периодов
    $('#compare-periods').on('click', function() {
        loadPeriodComparisonData();
    });
});

/**
 * Загрузка данных для страницы специальных отчетов
 */
function loadSpecialReportsData() {
    // Определяем активную вкладку
    const activeTab = $('#specialReportsTabs .nav-link.active').attr('href');
    const tabId = activeTab ? activeTab.substr(1) : 'celebrity-impact';

    // Загружаем данные для активной вкладки
    refreshTabContent(tabId);
}

/**
 * Обновление содержимого вкладки
 * @param {string} tabId - ID вкладки для обновления
 */
function refreshTabContent(tabId) {
    switch (tabId) {
        case 'celebrity-impact':
            loadCelebrityImpactData();
            break;
        case 'satisfaction-correlation':
            loadSatisfactionCorrelationData();
            break;
        case 'period-comparison':
            loadPeriodComparisonData();
            break;
        default:
            console.error('Неизвестная вкладка:', tabId);
    }
}

/**
 * Загрузка данных о влиянии знаменитостей
 */
function loadCelebrityImpactData() {
    // Загрузка данных для графика
    makeApiRequest('/stats/celebrity-impact', {}, function(response) {
        updateCelebrityImpactChart(response);
    });

    // Загрузка данных для таблицы визитов знаменитостей
    makeApiRequest('/stats/celebrity-visits', {}, function(response) {
        updateCelebrityVisitsTable(response);
    });
}

/**
 * Обновление графика влияния знаменитостей
 * @param {Object} data - Данные о влиянии знаменитостей
 */
function updateCelebrityImpactChart(data) {
    const ctx = document.getElementById('celebrity-impact-chart').getContext('2d');

    // Уничтожаем предыдущий экземпляр графика, если он существует
    if (celebrityImpactChart) {
        celebrityImpactChart.destroy();
    }

    // Подготавливаем данные для графика
    const labels = data.timeline.map(item => moment(item.date).format('DD.MM'));
    const visitorCounts = data.timeline.map(item => item.visitor_count);

    // Создаем отметки для визитов знаменитостей
    const celebrityVisits = [];

    for (let i = 0; i < data.timeline.length; i++) {
        const timelineItem = data.timeline[i];

        if (timelineItem.celebrity_visit) {
            celebrityVisits.push({
                x: labels[i],
                y: visitorCounts[i],
                celebrity: timelineItem.celebrity_name
            });
        }
    }

    // Создаем новый график
    celebrityImpactChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Количество посетителей',
                    data: visitorCounts,
                    backgroundColor: 'rgba(13, 110, 253, 0.2)',
                    borderColor: 'rgba(13, 110, 253, 1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true
                },
                {
                    label: 'Визиты знаменитостей',
                    data: celebrityVisits,
                    backgroundColor: 'rgba(214, 51, 132, 1)',
                    borderColor: 'rgba(214, 51, 132, 1)',
                    borderWidth: 0,
                    pointStyle: 'star',
                    pointRadius: 8,
                    pointHoverRadius: 12,
                    showLine: false
                }
            ]
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
                        label: function(context) {
                            const datasetLabel = context.dataset.label || '';
                            const value = context.raw;

                            if (context.datasetIndex === 1) {
                                return [
                                    `${datasetLabel}: ${value.celebrity}`,
                                    `Посетителей: ${value.y}`
                                ];
                            }

                            return `${datasetLabel}: ${value}`;
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
                        text: 'Дата'
                    }
                }
            }
        }
    });
}

/**
 * Обновление таблицы визитов знаменитостей
 * @param {Object} data - Данные о визитах знаменитостей
 */
function updateCelebrityVisitsTable(data) {
    const tableBody = $('#celebrity-visits-table');
    tableBody.empty();

    if (!data.visits || data.visits.length === 0) {
        tableBody.append('<tr><td colspan="5" class="text-center">Нет данных о визитах знаменитостей</td></tr>');
        return;
    }

    // Заполняем таблицу данными
    data.visits.forEach(visit => {
        const visitDate = moment(visit.date).format('DD.MM.YYYY');

        const row = $(`
            <tr>
                <td>${visitDate}</td>
                <td>${visit.celebrity_name}</td>
                <td>${visit.duration} мин.</td>
                <td>${visit.visitor_count}</td>
                <td>
                    <span class="${visit.growth >= 0 ? 'text-success' : 'text-danger'}">
                        ${visit.growth >= 0 ? '+' : ''}${visit.growth}%
                    </span>
                </td>
            </tr>
        `);

        tableBody.append(row);
    });
}

/**
 * Загрузка данных о корреляции эмоций с удовлетворенностью
 */
function loadSatisfactionCorrelationData() {
    makeApiRequest('/stats/satisfaction-correlation', {}, function(response) {
        updateSatisfactionCorrelationChart(response);
    });
}

/**
 * Обновление графика корреляции эмоций с удовлетворенностью
 * @param {Object} data - Данные о корреляции эмоций с удовлетворенностью
 */
function updateSatisfactionCorrelationChart(data) {
    const ctx = document.getElementById('satisfaction-correlation-chart').getContext('2d');

    // Уничтожаем предыдущий экземпляр графика, если он существует
    if (satisfactionCorrelationChart) {
        satisfactionCorrelationChart.destroy();
    }

    // Подготавливаем данные для графика
    const dates = data.correlation.map(item => moment(item.date).format('DD.MM'));
    const emotions = data.correlation.map(item => item.average_emotion_score);
    const satisfaction = data.correlation.map(item => item.satisfaction_score);

    // Создаем новый график
    satisfactionCorrelationChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [
                {
                    label: 'Средняя оценка эмоций',
                    data: emotions,
                    backgroundColor: 'rgba(13, 110, 253, 0.2)',
                    borderColor: 'rgba(13, 110, 253, 1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: false,
                    yAxisID: 'y'
                },
                {
                    label: 'Оценка удовлетворенности',
                    data: satisfaction,
                    backgroundColor: 'rgba(25, 135, 84, 0.2)',
                    borderColor: 'rgba(25, 135, 84, 1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: false,
                    yAxisID: 'y1'
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
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Средняя оценка эмоций (1-5)'
                    },
                    min: 0,
                    max: 5
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Оценка удовлетворенности (1-10)'
                    },
                    min: 0,
                    max: 10,
                    grid: {
                        drawOnChartArea: false
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

    // Добавляем информацию о корреляции
    const correlationCoefficient = data.correlation_coefficient || 0;
    const correlationInfo = $(`
        <div class="alert ${correlationCoefficient > 0.7 ? 'alert-success' : correlationCoefficient > 0.4 ? 'alert-info' : 'alert-warning'} mt-3">
            <strong>Коэффициент корреляции: ${correlationCoefficient.toFixed(2)}</strong>
            <p>${getCorrelationDescription(correlationCoefficient)}</p>
        </div>
    `);

    // Добавляем после графика
    $(ctx.canvas).parent().append(correlationInfo);
}

/**
 * Получение описания корреляции по коэффициенту
 * @param {number} coefficient - Коэффициент корреляции
 * @returns {string} Описание корреляции
 */
function getCorrelationDescription(coefficient) {
    const absCoefficient = Math.abs(coefficient);

    if (absCoefficient > 0.9) {
        return 'Очень сильная корреляция между эмоциями и удовлетворенностью';
    } else if (absCoefficient > 0.7) {
        return 'Сильная корреляция между эмоциями и удовлетворенностью';
    } else if (absCoefficient > 0.5) {
        return 'Средняя корреляция между эмоциями и удовлетворенностью';
    } else if (absCoefficient > 0.3) {
        return 'Слабая корреляция между эмоциями и удовлетворенностью';
    } else {
        return 'Очень слабая корреляция или ее отсутствие';
    }
}

/**
 * Загрузка данных для сравнения периодов
 */
function loadPeriodComparisonData() {
    // Получаем выбранные периоды
    const period1Dates = $('#period-1-date-range').datepicker('getDate');
    const period2Dates = $('#period-2-date-range').datepicker('getDate');

    // Проверяем, что выбраны оба периода
    if (!period1Dates || period1Dates.length < 2 || !period2Dates || period2Dates.length < 2) {
        showNotification('Пожалуйста, выберите оба периода для сравнения', 'warning');
        return;
    }

    // Форматируем даты для API
    const period1 = {
        start_date: moment(period1Dates[0]).format('YYYY-MM-DD'),
        end_date: moment(period1Dates[1]).format('YYYY-MM-DD')
    };

    const period2 = {
        start_date: moment(period2Dates[0]).format('YYYY-MM-DD'),
        end_date: moment(period2Dates[1]).format('YYYY-MM-DD')
    };

    // Отправляем запрос на API
    $.ajax({
        url: `${API_BASE_URL}/stats/period-comparison`,
        method: 'GET',
        data: {
            period1_start: period1.start_date,
            period1_end: period1.end_date,
            period2_start: period2.start_date,
            period2_end: period2.end_date,
            person_type: currentPersonType !== 'all' ? currentPersonType : undefined
        },
        dataType: 'json',
        success: function(response) {
            updatePeriodComparisonChart(response, period1, period2);
        },
        error: function(xhr, status, error) {
            console.error('Ошибка при загрузке данных сравнения периодов:', error);
            showNotification('Ошибка при загрузке данных сравнения периодов', 'danger');
        }
    });
}

/**
 * Обновление графика сравнения периодов
 * @param {Object} data - Данные сравнения периодов
 * @param {Object} period1 - Первый период сравнения
 * @param {Object} period2 - Второй период сравнения
 */
function updatePeriodComparisonChart(data, period1, period2) {
    const ctx = document.getElementById('period-comparison-chart').getContext('2d');

    // Уничтожаем предыдущий экземпляр графика, если он существует
    if (periodComparisonChart) {
        periodComparisonChart.destroy();
    }

    // Форматирование периодов для отображения
    const period1Label = `${moment(period1.start_date).format('DD.MM.YYYY')} - ${moment(period1.end_date).format('DD.MM.YYYY')}`;
    const period2Label = `${moment(period2.start_date).format('DD.MM.YYYY')} - ${moment(period2.end_date).format('DD.MM.YYYY')}`;

    // Получаем метрики для сравнения
    const metrics = [
        'Посетители',
        'Уникальные посетители',
        'Средний возраст',
        'Мужчины (%)',
        'Женщины (%)',
        'Счастливые (%)',
        'Грустные (%)',
        'Злые (%)',
        'Удивленные (%)',
        'Нейтральные (%)'
    ];

    // Получаем значения для каждого периода
    const period1Values = [
        data.period1.total_visitors,
        data.period1.unique_visitors,
        data.period1.average_age,
        data.period1.gender_distribution.male,
        data.period1.gender_distribution.female,
        data.period1.emotion_distribution.happy,
        data.period1.emotion_distribution.sad,
        data.period1.emotion_distribution.angry,
        data.period1.emotion_distribution.surprised,
        data.period1.emotion_distribution.neutral
    ];

    const period2Values = [
        data.period2.total_visitors,
        data.period2.unique_visitors,
        data.period2.average_age,
        data.period2.gender_distribution.male,
        data.period2.gender_distribution.female,
        data.period2.emotion_distribution.happy,
        data.period2.emotion_distribution.sad,
        data.period2.emotion_distribution.angry,
        data.period2.emotion_distribution.surprised,
        data.period2.emotion_distribution.neutral
    ];

    // Вычисляем процентное изменение
    const percentChange = period1Values.map((value, index) => {
        if (value === 0) return 0;
        return ((period2Values[index] - value) / value) * 100;
    });

    // Создаем цвета для процентного изменения
    const changeColors = percentChange.map(change => {
        return change >= 0 ? 'rgba(25, 135, 84, 0.8)' : 'rgba(220, 53, 69, 0.8)';
    });

    // Создаем новый график
    periodComparisonChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: metrics,
            datasets: [
                {
                    label: period1Label,
                    data: period1Values,
                    backgroundColor: 'rgba(13, 110, 253, 0.8)',
                    borderWidth: 1
                },
                {
                    label: period2Label,
                    data: period2Values,
                    backgroundColor: 'rgba(108, 117, 125, 0.8)',
                    borderWidth: 1
                },
                {
                    label: 'Изменение (%)',
                    data: percentChange,
                    backgroundColor: changeColors,
                    borderWidth: 1,
                    type: 'line',
                    yAxisID: 'y1'
                }
            ]
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
                        label: function(context) {
                            const datasetLabel = context.dataset.label || '';
                            const value = context.dataset.type === 'line'
                                ? `${context.raw.toFixed(1)}%`
                                : context.raw;
                            return `${datasetLabel}: ${value}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Значение'
                    },
                    beginAtZero: true
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Изменение (%)'
                    },
                    grid: {
                        drawOnChartArea: false
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Метрики'
                    }
                }
            }
        }
    });

    // Добавляем сводную информацию о сравнении
    const summaryInfo = $(`
        <div class="row mt-4">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5 class="card-title mb-0">Ключевые изменения</h5>
                    </div>
                    <div class="card-body">
                        <ul class="list-group">
                            <li class="list-group-item d-flex justify-content-between align-items-center">
                                Изменение числа посетителей
                                <span class="badge ${percentChange[0] >= 0 ? 'bg-success' : 'bg-danger'} rounded-pill">
                                    ${percentChange[0] >= 0 ? '+' : ''}${percentChange[0].toFixed(1)}%
                                </span>
                            </li>
                            <li class="list-group-item d-flex justify-content-between align-items-center">
                                Изменение числа уникальных посетителей
                                <span class="badge ${percentChange[1] >= 0 ? 'bg-success' : 'bg-danger'} rounded-pill">
                                    ${percentChange[1] >= 0 ? '+' : ''}${percentChange[1].toFixed(1)}%
                                </span>
                            </li>
                            <li class="list-group-item d-flex justify-content-between align-items-center">
                                Изменение среднего возраста
                                <span class="badge bg-info rounded-pill">
                                    ${percentChange[2] >= 0 ? '+' : ''}${percentChange[2].toFixed(1)}%
                                </span>
                            </li>
                            <li class="list-group-item d-flex justify-content-between align-items-center">
                                Наибольший рост эмоции
                                <span class="badge bg-success rounded-pill">
                                    ${getMaxChangeEmotion(percentChange.slice(5, 10), metrics.slice(5, 10))}
                                </span>
                            </li>
                        </ul>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5 class="card-title mb-0">Выводы</h5>
                    </div>
                    <div class="card-body">
                        ${generateComparisonInsights(data, percentChange)}
                    </div>
                </div>
            </div>
        </div>
    `);

    // Добавляем после графика
    $(ctx.canvas).parent().after(summaryInfo);
}

/**
 * Получение эмоции с максимальным изменением
 * @param {Array} changes - Массив изменений эмоций
 * @param {Array} emotions - Массив названий эмоций
 * @returns {string} Строка с названием эмоции и процентом изменения
 */
function getMaxChangeEmotion(changes, emotions) {
    let maxIndex = 0;
    let maxChange = Math.abs(changes[0]);

    for (let i = 1; i < changes.length; i++) {
        if (Math.abs(changes[i]) > maxChange) {
            maxChange = Math.abs(changes[i]);
            maxIndex = i;
        }
    }

    return `${emotions[maxIndex]}: ${changes[maxIndex] >= 0 ? '+' : ''}${changes[maxIndex].toFixed(1)}%`;
}

/**
 * Генерация выводов на основе сравнения периодов
 * @param {Object} data - Данные сравнения периодов
 * @param {Array} percentChange - Массив процентных изменений
 * @returns {string} HTML-строка с выводами
 */
function generateComparisonInsights(data, percentChange) {
    let insights = '';

    // Анализируем изменения в количестве посетителей
    if (percentChange[0] > 20) {
        insights += '<p><i class="fas fa-arrow-up text-success"></i> <strong>Значительный рост</strong> числа посетителей во втором периоде.</p>';
    } else if (percentChange[0] > 5) {
        insights += '<p><i class="fas fa-arrow-up text-success"></i> <strong>Умеренный рост</strong> числа посетителей во втором периоде.</p>';
    } else if (percentChange[0] < -20) {
        insights += '<p><i class="fas fa-arrow-down text-danger"></i> <strong>Значительное снижение</strong> числа посетителей во втором периоде.</p>';
    } else if (percentChange[0] < -5) {
        insights += '<p><i class="fas fa-arrow-down text-danger"></i> <strong>Умеренное снижение</strong> числа посетителей во втором периоде.</p>';
    } else {
        insights += '<p><i class="fas fa-equals text-info"></i> <strong>Стабильное</strong> число посетителей в обоих периодах.</p>';
    }

    // Анализируем изменения в эмоциях
    if (percentChange[5] > 10) {
        insights += '<p><i class="fas fa-smile text-success"></i> <strong>Рост положительных эмоций</strong> во втором периоде.</p>';
    } else if (percentChange[6] > 10 || percentChange[7] > 10) {
        insights += '<p><i class="fas fa-frown text-danger"></i> <strong>Рост отрицательных эмоций</strong> во втором периоде.</p>';
    }

    // Анализируем изменения в гендерном распределении
    if (Math.abs(percentChange[3] - percentChange[4]) > 10) {
        insights += '<p><i class="fas fa-venus-mars text-info"></i> <strong>Изменение в гендерном балансе</strong> посетителей.</p>';
    }

    // Анализируем изменения возраста
    if (Math.abs(percentChange[2]) > 5) {
        const ageDirection = percentChange[2] > 0 ? 'увеличился' : 'уменьшился';
        insights += `<p><i class="fas fa-user-clock text-info"></i> <strong>Средний возраст</strong> посетителей ${ageDirection}.</p>`;
    }

    // Общие рекомендации
    insights += '<p><strong>Рекомендации:</strong></p>';
    insights += '<ul>';

    if (percentChange[0] < 0) {
        insights += '<li>Провести акции для привлечения посетителей</li>';
    }

    if (percentChange[6] > 10 || percentChange[7] > 10) {
        insights += '<li>Обратить внимание на причины негативных эмоций</li>';
    }

    insights += '<li>Продолжать анализировать тренды посещаемости</li>';
    insights += '</ul>';

    return insights;
}