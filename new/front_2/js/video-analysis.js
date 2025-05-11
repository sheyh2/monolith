/**
 * Restaurant Analytics Dashboard - Video Analysis Module
 * Обработка видео, отправка кадров на бэкенд, отображение результатов
 */

// Глобальные переменные для работы с видео
let videoElement;           // HTML элемент видео
let canvasElement;          // HTML элемент canvas для визуализации
let canvasContext;          // Контекст рисования canvas
let videoUploadElement;     // HTML элемент загрузки видео
let videoFile;              // Загруженный файл видео
let videoURL;               // URL объекта загруженного видео

// Данные обработки видео
let taskId = null;                  // ID задачи обработки
let processingStatus = 'idle';      // Статус обработки
let totalFrames = 0;                // Общее количество кадров
let processedFrames = 0;            // Обработанные кадры
let currentFrameId = 0;             // Текущий кадр
let framesData = {};                // Данные по кадрам
let videoFPS = 0;                   // Кадров в секунду в видео
let statisticsData = {};            // Статистика до текущего кадра
let captureInterval = 5;            // Интервал захвата кадров (каждый N-ый кадр)
let processingInProgress = false;   // Флаг процесса обработки

// Инициализация при загрузке страницы
$(document).ready(function() {
    // Назначаем элементы
    videoElement = document.getElementById('video-player');
    canvasElement = document.getElementById('video-canvas');
    canvasContext = canvasElement.getContext('2d');
    videoUploadElement = document.getElementById('video-upload');

    // Инициализация обработчиков событий
    initVideoEvents();
});

/**
 * Инициализация обработчиков событий для видео
 */
function initVideoEvents() {
    // Обработчик события загрузки видео
    videoUploadElement.addEventListener('change', handleVideoUpload);

    // События видео
    videoElement.addEventListener('loadedmetadata', handleVideoMetadataLoaded);
    videoElement.addEventListener('timeupdate', handleVideoTimeUpdate);
    videoElement.addEventListener('play', handleVideoPlay);
    videoElement.addEventListener('pause', handleVideoPause);
    videoElement.addEventListener('ended', handleVideoEnded);
}

/**
 * Обработчик загрузки видеофайла
 * @param {Event} event - Событие изменения файла
 */
function handleVideoUpload(event) {
    // Получаем загруженный файл
    videoFile = event.target.files[0];

    if (!videoFile) {
        return;
    }

    // Создаем URL для видео
    if (videoURL) {
        URL.revokeObjectURL(videoURL);
    }
    videoURL = URL.createObjectURL(videoFile);

    // Устанавливаем видео в плеер
    videoElement.src = videoURL;

    // Сбрасываем данные предыдущего видео
    resetVideoProcessingData();

    // Добавляем сообщение в лог
    addToProcessingLog(`Видео "${videoFile.name}" загружено. Готово к обработке.`);

    // Обновляем статус
    updateProcessingStatus('ready', 'Готово к обработке');
}

/**
 * Сброс данных обработки видео
 */
function resetVideoProcessingData() {
    taskId = null;
    processingStatus = 'idle';
    totalFrames = 0;
    processedFrames = 0;
    currentFrameId = 0;
    framesData = {};
    statisticsData = {};
    processingInProgress = false;

    // Очищаем канвас
    updateCanvasSize();
    canvasContext.clearRect(0, 0, canvasElement.width, canvasElement.height);

    // Обновляем UI
    $('#processed-frames').text('0');
    $('#total-frames').text('0');
    $('#current-frame-id').text('0');
    $('#faces-in-frame').text('0');
    $('#faces-list').empty();
    $('#processing-progress').css('width', '0%').text('0%');

    // Очищаем статистику до текущего кадра
    $('#frame-total-visitors').text('0');
    $('#frame-unique-visitors').text('0');
    $('#frame-waiters').text('0');
    $('#frame-celebrities').text('0');
}

/**
 * Обработчик события загрузки метаданных видео
 */
function handleVideoMetadataLoaded() {
    // Обновляем размер canvas по размеру видео
    updateCanvasSize();

    // Определяем количество кадров в видео
    videoFPS = getVideoFPS();
    totalFrames = Math.floor(videoElement.duration * videoFPS);

    // Обновляем UI
    $('#total-frames').text(totalFrames);

    // Инициализируем задачу обработки видео
    initVideoProcessingTask();
}

/**
 * Получение частоты кадров видео
 * @returns {number} Частота кадров в секунду
 */
function getVideoFPS() {
    // По умолчанию считаем, что частота кадров 25 fps
    // В реальном проекте можно получить из метаданных видео
    return 25;
}

/**
 * Обновление размеров canvas в соответствии с размером видео
 */
function updateCanvasSize() {
    if (!videoElement || !canvasElement) return;

    const videoWidth = videoElement.videoWidth || videoElement.clientWidth;
    const videoHeight = videoElement.videoHeight || videoElement.clientHeight;

    canvasElement.width = videoWidth;
    canvasElement.height = videoHeight;
}

/**
 * Инициализация задачи обработки видео
 */
function initVideoProcessingTask() {
    // Отправляем запрос на создание задачи обработки
    $.ajax({
        url: `${API_BASE_URL}/video/init-task`,
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            total_frames: totalFrames
        }),
        success: function(response) {
            // Сохраняем ID задачи
            taskId = response.task_id;

            // Обновляем статус
            updateProcessingStatus('initialized', 'Задача инициализирована');

            // Добавляем сообщение в лог
            addToProcessingLog(`Задача обработки видео создана (ID: ${taskId})`);
        },
        error: function(xhr, status, error) {
            console.error('Ошибка инициализации задачи:', error);
            updateProcessingStatus('error', 'Ошибка инициализации');
            addToProcessingLog(`Ошибка инициализации задачи: ${error}`);
        }
    });
}

/**
 * Обработчик обновления времени видео
 */
function handleVideoTimeUpdate() {
    // Вычисляем текущий кадр на основе времени воспроизведения
    currentFrameId = Math.floor(videoElement.currentTime * videoFPS);

    // Обновляем информацию о текущем кадре в UI
    $('#current-frame-id').text(currentFrameId);

    // Отображаем данные текущего кадра (если они есть)
    displayCurrentFrameData();

    // Обновляем статистику до текущего кадра
    updateStatisticsToCurrentFrame();

    // Отрисовка информации на canvas (рамки вокруг лиц и т.д.)
    drawFrameInfo();
}

/**
 * Обработчик начала воспроизведения видео
 */
function handleVideoPlay() {
    // Если обработка ещё не начата и задача инициализирована, начинаем захват кадров
    if (!processingInProgress && taskId && processingStatus === 'initialized') {
        processingInProgress = true;
        updateProcessingStatus('processing', 'Обработка видео');
        captureFrames();
    }
}

/**
 * Обработчик паузы видео
 */
function handleVideoPause() {
    // Можно добавить дополнительную логику при паузе видео
}

/**
 * Обработчик завершения видео
 */
function handleVideoEnded() {
    // Если видео закончилось, завершаем задачу обработки
    if (taskId && processingStatus === 'processing') {
        completeVideoProcessingTask();
    }
}

/**
 * Захват и отправка кадров видео на сервер
 */
function captureFrames() {
    if (!processingInProgress || !taskId) return;

    // Создаем временный элемент canvas для захвата кадра
    const tempCanvas = document.createElement('canvas');
    const tempContext = tempCanvas.getContext('2d');

    // Устанавливаем размеры canvas по размеру видео
    tempCanvas.width = videoElement.videoWidth;
    tempCanvas.height = videoElement.videoHeight;

    // Функция для захвата и отправки одного кадра
    function captureAndSendFrame(frameId) {
        // Проверяем, нужно ли захватывать этот кадр (согласно интервалу)
        if (frameId % captureInterval !== 0) {
            return Promise.resolve();
        }

        // Проверяем, был ли уже отправлен этот кадр
        if (framesData[frameId] && framesData[frameId].processed) {
            return Promise.resolve();
        }

        // Устанавливаем время видео для соответствующего кадра
        videoElement.currentTime = frameId / videoFPS;

        // Возвращаем Promise для последовательной обработки
        return new Promise((resolve, reject) => {
            // Ожидаем, пока видео установится на нужный кадр
            videoElement.onseeked = function() {
                // Рисуем текущий кадр на canvas
                tempContext.drawImage(videoElement, 0, 0, tempCanvas.width, tempCanvas.height);

                // Получаем данные кадра в формате base64
                const frameData = tempCanvas.toDataURL('image/jpeg', 0.8);

                // Отправляем кадр на сервер
                $.ajax({
                    url: `${API_BASE_URL}/video/frame/${taskId}`,
                    method: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({
                        frame_number: frameId,
                        frame_data: frameData
                    }),
                    success: function(response) {
                        // Сохраняем данные об обработанном кадре
                        framesData[frameId] = {
                            processed: true,
                            status: response.status,
                            progress: response.progress
                        };

                        // Обновляем счетчик обработанных кадров
                        processedFrames++;

                        // Обновляем прогресс
                        const progress = Math.round((processedFrames / (totalFrames / captureInterval)) * 100);
                        $('#processing-progress').css('width', `${progress}%`).text(`${progress}%`);
                        $('#processed-frames').text(processedFrames);

                        // Если это текущий отображаемый кадр, обновляем данные
                        if (currentFrameId === frameId) {
                            displayCurrentFrameData();
                        }

                        // Добавляем сообщение в лог
                        addToProcessingLog(`Кадр ${frameId} обработан`);

                        // Завершаем Promise
                        resolve();
                    },
                    error: function(xhr, status, error) {
                        console.error(`Ошибка обработки кадра ${frameId}:`, error);
                        addToProcessingLog(`Ошибка обработки кадра ${frameId}: ${error}`);

                        // Отмечаем кадр как необработанный с ошибкой
                        framesData[frameId] = {
                            processed: false,
                            error: true,
                            errorMessage: error
                        };

                        // Завершаем Promise с ошибкой
                        reject(error);
                    }
                });
            };
        });
    }

    // Последовательная обработка кадров
    async function processFramesSequentially() {
        // Создаем массив кадров для обработки (с учетом интервала)
        const frameIds = [];
        for (let i = 0; i < totalFrames; i += captureInterval) {
            frameIds.push(i);
        }

        // Получаем данные об уже обработанных кадрах
        const processedFrameIds = Object.keys(framesData)
            .filter(id => framesData[id].processed)
            .map(id => parseInt(id));

        // Фильтруем только необработанные кадры
        const framesToProcess = frameIds.filter(id => !processedFrameIds.includes(id));

        // Последовательно обрабатываем кадры
        for (let i = 0; i < framesToProcess.length && processingInProgress; i++) {
            try {
                await captureAndSendFrame(framesToProcess[i]);
            } catch (error) {
                console.error('Ошибка в последовательной обработке кадров:', error);
                // Продолжаем со следующим кадром
            }
        }

        // После обработки всех кадров завершаем задачу
        if (processingInProgress) {
            completeVideoProcessingTask();
        }
    }

    // Запускаем последовательную обработку кадров
    processFramesSequentially();
}

/**
 * Завершение задачи обработки видео
 */
function completeVideoProcessingTask() {
    if (!taskId) return;

    $.ajax({
        url: `${API_BASE_URL}/video/complete-task/${taskId}`,
        method: 'POST',
        success: function(response) {
            processingInProgress = false;
            updateProcessingStatus('completed', 'Обработка завершена');

            // Добавляем сообщение в лог
            addToProcessingLog(`Обработка видео завершена. Всего обработано ${response.processed_frames} кадров.`);
            addToProcessingLog(`Обнаружено лиц: ${response.faces_detected}`);

            // Загружаем финальную статистику
            fetchStatisticsData(totalFrames);
        },
        error: function(xhr, status, error) {
            updateProcessingStatus('error', 'Ошибка при завершении');
            addToProcessingLog(`Ошибка при завершении обработки: ${error}`);
        }
    });
}

/**
 * Отображение данных текущего кадра
 */
function displayCurrentFrameData() {
    // Проверяем, есть ли данные для текущего кадра
    if (!framesData[currentFrameId]) {
        $('#faces-in-frame').text('0');
        $('#faces-list').empty();
        return;
    }

    // Получаем данные о лицах для текущего кадра
    $.ajax({
        url: `${API_BASE_URL}/frame-data`,
        method: 'GET',
        data: {
            frame_id: currentFrameId
        },
        success: function(response) {
            // Обновляем счетчик лиц
            const facesCount = response.faces.length;
            $('#faces-in-frame').text(facesCount);

            // Очищаем список лиц
            $('#faces-list').empty();

            // Заполняем список лиц
            response.faces.forEach(face => {
                const personTypeClass = getPersonTypeColorClass(face.person_type);
                const emotionClass = getEmotionColorClass(face.emotion);

                const faceItem = $(`
                    <div class="list-group-item">
                        <div class="d-flex justify-content-between align-items-center">
                            <span>ID: ${face.track_id}</span>
                            <span class="badge ${personTypeClass}">${face.person_type}</span>
                        </div>
                        <div>Имя: ${face.name || 'неизвестно'}</div>
                        <div>
                            <span>Возраст: ${face.age || 'н/д'}</span> |
                            <span>Пол: ${face.gender || 'н/д'}</span>
                        </div>
                        <div>Эмоция: <span class="${emotionClass}">${face.emotion || 'н/д'}</span></div>
                    </div>
                `);

                $('#faces-list').append(faceItem);
            });
        },
        error: function(xhr, status, error) {
            console.error('Ошибка загрузки данных кадра:', error);
        }
    });
}

/**
 * Обновление статистики до текущего кадра
 */
function updateStatisticsToCurrentFrame() {
    // Запрашиваем статистику до текущего кадра
    fetchStatisticsData(currentFrameId);
}

/**
 * Загрузка статистики до указанного кадра
 * @param {number} maxFrameId - Максимальный ID кадра для статистики
 */
function fetchStatisticsData(maxFrameId) {
    $.ajax({
        url: `${API_BASE_URL}/stats/frame`,
        method: 'GET',
        data: {
            max_frame_id: maxFrameId,
            task_id: taskId
        },
        success: function(response) {
            statisticsData = response;

            // Обновляем статистику в интерфейсе
            $('#frame-total-visitors').text(response.total_visitors || 0);
            $('#frame-unique-visitors').text(response.unique_visitors || 0);
            $('#frame-waiters').text(response.waiters_count || 0);
            $('#frame-celebrities').text(response.celebrities_count || 0);
        },
        error: function(xhr, status, error) {
            console.error('Ошибка загрузки статистики:', error);
        }
    });
}

/**
 * Отрисовка информации на canvas (рамки вокруг лиц и т.д.)
 */
function drawFrameInfo() {
    // Очищаем canvas
    canvasContext.clearRect(0, 0, canvasElement.width, canvasElement.height);

    // Проверяем, есть ли данные для текущего кадра
    if (!framesData[currentFrameId]) {
        return;
    }

    // Загружаем данные о лицах для текущего кадра
    $.ajax({
        url: `${API_BASE_URL}/frame-data`,
        method: 'GET',
        data: {
            frame_id: currentFrameId
        },
        success: function(response) {
            // Отрисовываем рамки вокруг лиц
            response.faces.forEach(face => {
                // Определяем цвет рамки в зависимости от типа персоны
                let strokeColor;
                switch (face.person_type) {
                    case 'customer':
                        strokeColor = '#0d6efd'; // синий
                        break;
                    case 'waiter':
                        strokeColor = '#fd7e14'; // оранжевый
                        break;
                    case 'celebrity':
                        strokeColor = '#d63384'; // пурпурный
                        break;
                    default:
                        strokeColor = '#6c757d'; // серый
                }

                // Определяем толщину рамки в зависимости от видимости лица
                const lineWidth = face.is_frontal ? 3 : 1;

                // Рисуем рамку вокруг лица
                if (face.face_top && face.face_right && face.face_bottom && face.face_left) {
                    canvasContext.beginPath();
                    canvasContext.rect(
                        face.face_left,
                        face.face_top,
                        face.face_right - face.face_left,
                        face.face_bottom - face.face_top
                    );
                    canvasContext.strokeStyle = strokeColor;
                    canvasContext.lineWidth = lineWidth;
                    canvasContext.stroke();

                    // Рисуем информацию над рамкой
                    canvasContext.font = '12px Arial';
                    canvasContext.fillStyle = 'rgba(0, 0, 0, 0.7)';
                    canvasContext.fillRect(
                        face.face_left,
                        face.face_top - 40,
                        200,
                        35
                    );

                    // Отображаем имя и тип персоны
                    canvasContext.fillStyle = 'white';
                    canvasContext.fillText(
                        `ID: ${face.track_id} | ${face.name || 'неизвестно'}`,
                        face.face_left + 5,
                        face.face_top - 25
                    );

                    // Отображаем возраст, пол и эмоцию, если они известны
                    if (face.age || face.gender || face.emotion) {
                        canvasContext.fillText(
                            `${face.age || 'н/д'} | ${face.gender || 'н/д'} | ${face.emotion || 'н/д'}`,
                            face.face_left + 5,
                            face.face_top - 10
                        );
                    }
                }

                // Рисуем рамку вокруг тела, если есть данные
                if (face.body_top && face.body_right && face.body_bottom && face.body_left) {
                    canvasContext.beginPath();
                    canvasContext.rect(
                        face.body_left,
                        face.body_top,
                        face.body_right - face.body_left,
                        face.body_bottom - face.body_top
                    );
                    canvasContext.strokeStyle = strokeColor;
                    canvasContext.lineWidth = 1;
                    canvasContext.stroke();
                }
            });
        }
    });
}

/**
 * Обновление статуса обработки видео
 * @param {string} status - Статус обработки
 * @param {string} message - Сообщение о статусе
 */
function updateProcessingStatus(status, message) {
    processingStatus = status;

    // Обновляем индикатор статуса
    $('#processing-status').text(message);

    // Обновляем цвет прогресс-бара в зависимости от статуса
    let progressBarClass = 'bg-primary';

    switch (status) {
        case 'idle':
        case 'ready':
            progressBarClass = 'bg-secondary';
            break;
        case 'initialized':
            progressBarClass = 'bg-info';
            break;
        case 'processing':
            progressBarClass = 'bg-primary';
            break;
        case 'completed':
            progressBarClass = 'bg-success';
            break;
        case 'error':
            progressBarClass = 'bg-danger';
            break;
    }

    // Удаляем все классы bg-* и добавляем нужный
    $('#processing-progress')
        .removeClass('bg-primary bg-secondary bg-info bg-success bg-danger')
        .addClass(progressBarClass);
}

/**
 * Добавление сообщения в лог обработки
 * @param {string} message - Сообщение для логирования
 */
function addToProcessingLog(message) {
    const timestamp = moment().format('HH:mm:ss');
    const logEntry = $(`<div>[${timestamp}] ${message}</div>`);

    // Добавляем сообщение в начало лога
    $('#processing-log').prepend(logEntry);

    // Ограничиваем количество сообщений в логе
    const maxLogEntries = 100;
    const logEntries = $('#processing-log').children();

    if (logEntries.length > maxLogEntries) {
        logEntries.slice(maxLogEntries).remove();
    }
}