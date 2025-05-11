/**
 * Restaurant Analytics Dashboard - Main JavaScript
 * Управление навигацией, инициализация компонентов, общие функции
 */

// Глобальные настройки и переменные
const API_BASE_URL = '/api';
const DEFAULT_DATE_RANGE = {
    startDate: moment().subtract(7, 'days').toDate(),
    endDate: moment().toDate()
};
let currentPersonType = 'all';
let currentDateRange = DEFAULT_DATE_RANGE;
let currentPage = 'dashboard';
let filtersApplied = false;

// Инициализация при загрузке страницы
$(document).ready(function() {
    // Инициализация выбора даты
    initDatePickers();

    // Инициализация навигации
    initNavigation();

    // Обработчик кнопки применения фильтров
    $('#apply-filters').on('click', function() {
        filtersApplied = true;
        applyFilters();
    });

    // Загрузка данных для дашборда по умолчанию
    loadPageData('dashboard');
});

/**
 * Инициализация элементов выбора даты
 */
function initDatePickers() {
    // Основной выбор диапазона дат
    $('#date-range-picker').datepicker({
        format: 'dd.mm.yyyy',
        language: 'ru',
        autoclose: true,
        clearBtn: true,
        todayHighlight: true,
        orientation: 'bottom',
        range: true
    });

    // Установка значения по умолчанию
    $('#date-range-picker').datepicker('setDate', [DEFAULT_DATE_RANGE.startDate, DEFAULT_DATE_RANGE.endDate]);

    // Специальные выборщики дат для сравнения периодов
    $('#period-1-date-range, #period-2-date-range').datepicker({
        format: 'dd.mm.yyyy',
        language: 'ru',
        autoclose: true,
        clearBtn: true,
        todayHighlight: true,
        orientation: 'bottom',
        range: true
    });

    // Обработчик события изменения даты
    $('#date-range-picker').on('changeDate', function(e) {
        if (e.dates.length >= 2) {
            currentDateRange = {
                startDate: e.dates[0],
                endDate: e.dates[1]
            };

            // Если включено автоматическое обновление при изменении фильтров
            if (filtersApplied) {
                applyFilters();
            }
        }
    });
}

/**
 * Инициализация навигации между страницами
 */
function initNavigation() {
    // Обработчик кликов по ссылкам навигации
    $('.nav-link[data-page]').on('click', function(e) {
        e.preventDefault();

        // Получаем ID страницы, на которую нужно перейти
        const targetPage = $(this).data('page');

        // Если это та же страница, не делаем ничего
        if (targetPage === currentPage) {
            return;
        }

        // Обновляем активный элемент навигации
        $('.nav-link').removeClass('active');
        $(this).addClass('active');

        // Скрываем текущую страницу и показываем целевую
        $('.page-content').addClass('d-none');
        $(`#page-${targetPage}`).removeClass('d-none');

        // Обновляем заголовок страницы
        $('#page-title').text($(this).text().trim());

        // Обновляем текущую страницу
        currentPage = targetPage;

        // Загружаем данные для новой страницы
        loadPageData(targetPage);
    });
}

/**
 * Применение выбранных фильтров и перезагрузка данных текущей страницы
 */
function applyFilters() {
    // Получаем значение фильтра типа персоны
    currentPersonType = $('#person-type-filter').val();

    // Перезагружаем данные для текущей страницы с новыми фильтрами
    loadPageData(currentPage);

    // Выводим информацию о применённых фильтрах
    console.log('Фильтры применены:', {
        dateRange: {
            startDate: moment(currentDateRange.startDate).format('DD.MM.YYYY'),
            endDate: moment(currentDateRange.endDate).format('DD.MM.YYYY')
        },
        personType: currentPersonType
    });
}

/**
 * Загрузка данных для определённой страницы
 * @param {string} page - ID страницы для загрузки данных
 */
function loadPageData(page) {
    // В зависимости от страницы вызываем соответствующие функции загрузки данных
    switch (page) {
        case 'dashboard':
            loadDashboardData();
            break;
        case 'video-analysis':
            // Для страницы видеоанализа инициализация уже происходит в video-analysis.js
            break;
        case 'visitor-analytics':
            loadVisitorAnalyticsData();
            break;
        case 'staff-performance':
            loadStaffPerformanceData();
            break;
        case 'special-reports':
            loadSpecialReportsData();
            break;
        default:
            console.error('Неизвестная страница:', page);
    }
}

/**
 * Общая функция для выполнения запросов к API
 * @param {string} endpoint - Эндпоинт API
 * @param {Object} params - Параметры запроса
 * @param {function} successCallback - Функция обратного вызова при успехе
 * @param {function} errorCallback - Функция обратного вызова при ошибке
 */
function makeApiRequest(endpoint, params = {}, successCallback, errorCallback) {
    // Добавляем общие параметры фильтрации к запросу
    if (currentDateRange) {
        params.start_date = moment(currentDateRange.startDate).format('YYYY-MM-DD');
        params.end_date = moment(currentDateRange.endDate).format('YYYY-MM-DD');
    }

    if (currentPersonType !== 'all') {
        params.person_type = currentPersonType;
    }

    // Выполняем AJAX запрос
    $.ajax({
        url: `${API_BASE_URL}${endpoint}`,
        method: 'GET',
        data: params,
        dataType: 'json',
        success: function(response) {
            if (typeof successCallback === 'function') {
                successCallback(response);
            }
        },
        error: function(xhr, status, error) {
            console.error('API Error:', error, xhr);

            if (typeof errorCallback === 'function') {
                errorCallback(xhr, status, error);
            } else {
                // Показываем уведомление об ошибке, если нет специальной функции
                showNotification('Ошибка при загрузке данных', 'danger');
            }
        }
    });
}

/**
 * Функция для отображения уведомлений
 * @param {string} message - Текст уведомления
 * @param {string} type - Тип уведомления (success, warning, danger, info)
 * @param {number} duration - Длительность показа в миллисекундах
 */
function showNotification(message, type = 'info', duration = 3000) {
    // Создаём элемент уведомления
    const notification = $(`<div class="alert alert-${type} alert-dismissible fade show position-fixed top-0 end-0 m-3" style="z-index: 1050;">
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    </div>`);

    // Добавляем в DOM
    $('body').append(notification);

    // Авто-скрытие через заданное время
    setTimeout(function() {
        notification.alert('close');
    }, duration);
}

/**
 * Функция для форматирования даты и времени
 * @param {Date|string} date - Дата для форматирования
 * @param {string} format - Формат даты (default: 'DD.MM.YYYY HH:mm')
 * @returns {string} Отформатированная дата
 */
function formatDateTime(date, format = 'DD.MM.YYYY HH:mm') {
    return moment(date).format(format);
}

/**
 * Функция для получения цвета по типу персоны
 * @param {string} personType - Тип персоны (customer, waiter, celebrity)
 * @returns {string} CSS класс для цвета
 */
function getPersonTypeColorClass(personType) {
    switch (personType) {
        case 'customer':
            return 'customer-badge';
        case 'waiter':
            return 'waiter-badge';
        case 'celebrity':
            return 'celebrity-badge';
        default:
            return 'bg-secondary';
    }
}

/**
 * Функция для получения цвета по эмоции
 * @param {string} emotion - Эмоция
 * @returns {string} CSS класс для цвета
 */
function getEmotionColorClass(emotion) {
    if (!emotion) return 'emotion-neutral';

    switch (emotion.toLowerCase()) {
        case 'happy':
        case 'happiness':
        case 'joy':
            return 'emotion-happy';
        case 'sad':
        case 'sadness':
            return 'emotion-sad';
        case 'angry':
        case 'anger':
            return 'emotion-angry';
        case 'surprised':
        case 'surprise':
            return 'emotion-surprised';
        default:
            return 'emotion-neutral';
    }
}

/**
 * Функция для создания цветов диаграмм
 * @param {number} count - Количество цветов
 * @param {number} opacity - Прозрачность (0-1)
 * @returns {Array} Массив цветов в формате rgba
 */
function generateChartColors(count, opacity = 0.8) {
    const baseColors = [
        [13, 110, 253],   // Primary
        [25, 135, 84],    // Success
        [220, 53, 69],    // Danger
        [255, 193, 7],    // Warning
        [13, 202, 240],   // Info
        [108, 117, 125],  // Secondary
        [214, 51, 132],   // Pink
        [253, 126, 20],   // Orange
        [111, 66, 193],   // Purple
        [32, 201, 151]    // Teal
    ];

    let colors = [];

    for (let i = 0; i < count; i++) {
        const colorIndex = i % baseColors.length;
        const [r, g, b] = baseColors[colorIndex];
        colors.push(`rgba(${r}, ${g}, ${b}, ${opacity})`);
    }

    return colors;
}

/**
 * Функция для обработки ошибок при загрузке данных диаграмм
 * @param {string} chartId - ID элемента canvas диаграммы
 * @param {string} message - Сообщение об ошибке
 */
function handleChartError(chartId, message = 'Не удалось загрузить данные') {
    const canvas = document.getElementById(chartId);

    if (!canvas) {
        console.error(`Canvas с ID "${chartId}" не найден`);
        return;
    }

    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.font = '16px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = '#dc3545';
    ctx.fillText(message, canvas.width / 2, canvas.height / 2);
}