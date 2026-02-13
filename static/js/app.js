// ---------- CSRF-токен ----------
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
const csrftoken = getCookie('csrftoken');

$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    }
});

// ---------- Глобальные настройки пользователя ----------
window.userSettings = {
    sound_enabled: true,
    volume: 100,
    dark_theme: false
};

// ---------- Загрузка настроек при старте ----------
function loadUserSettings() {
    $.get('/api/settings/')
        .done(function(data) {
            window.userSettings = {
                sound_enabled: data.sound_enabled,
                volume: data.volume,
                dark_theme: data.dark_theme
            };
            applyTheme(data.dark_theme);
        })
        .fail(function() {
            console.warn('Не удалось загрузить настройки, используем значения по умолчанию');
            window.userSettings = {
                sound_enabled: true,
                volume: 100,
                dark_theme: false
            };
            applyTheme(false);
        });
}

// ---------- Применение тёмной темы ----------
window.applyTheme = function(isDark) {
    if (isDark) {
        document.body.classList.add('dark-theme');
        localStorage.setItem('dark_theme', 'true');
    } else {
        document.body.classList.remove('dark-theme');
        localStorage.setItem('dark_theme', 'false');
    }
};

// ---------- Проверка localStorage при загрузке ----------
(function() {
    const savedTheme = localStorage.getItem('dark_theme');
    if (savedTheme === 'true') {
        document.body.classList.add('dark-theme');
    }
})();

// ---------- ФЛАГ РАЗРЕШЕНИЯ ЗВУКА (первый клик пользователя) ----------
window.audioAllowed = false;

// ---------- ИНИЦИАЛИЗАЦИЯ ЗВУКА ПРИ ПЕРВОМ ВЗАИМОДЕЙСТВИИ ----------
function enableAudio() {
    if (window.audioAllowed) return;
    window.audioAllowed = true;
    console.log('🔊 Звук активирован');
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        audioCtx.resume();
        setTimeout(() => audioCtx.close(), 100);
    } catch (e) {
        console.warn('Не удалось активировать аудио', e);
    }
}

// ---------- Воспроизведение звука ----------
function playNotificationSound() {
    if (!window.userSettings.sound_enabled) return;
    if (!window.audioAllowed) {
        console.warn('🔇 Звук не активирован (нужен клик по странице)');
        return;
    }
    try {
        const audio = new Audio('/static/sounds/notification.mp3');
        audio.volume = window.userSettings.volume / 100;
        audio.play().catch(e => {
            console.warn('Не удалось воспроизвести MP3, пробуем Web Audio', e);
            playWebAudio();
        });
    } catch(e) {
        console.warn('Ошибка воспроизведения MP3, пробуем Web Audio', e);
        playWebAudio();
    }
}

// ---------- Воспроизведение через Web Audio (запасной вариант) ----------
function playWebAudio() {
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const gainNode = audioCtx.createGain();
        gainNode.gain.value = window.userSettings.volume / 100;
        gainNode.connect(audioCtx.destination);
        
        const oscillator = audioCtx.createOscillator();
        oscillator.type = 'sine';
        oscillator.frequency.setValueAtTime(440, audioCtx.currentTime);
        oscillator.connect(gainNode);
        oscillator.start();
        oscillator.stop(audioCtx.currentTime + 0.3);
        
        setTimeout(() => audioCtx.close(), 500);
    } catch(e) {
        console.warn('Web Audio не поддерживается', e);
    }
}

// ---------- ВСПЛЫВАЮЩЕЕ СООБЩЕНИЕ (TOAST) - ГЛОБАЛЬНОЕ ----------
window.showToast = function(message, isError = false) {
    let toastContainer = $('#toast-container');
    if (toastContainer.length === 0) {
        $('body').append('<div id="toast-container" style="position: fixed; top: 20px; right: 20px; z-index: 9999;"></div>');
        toastContainer = $('#toast-container');
    }
    const id = 'toast-' + Date.now();
    const bgColor = isError ? '#d32f2f' : '#333';
    const toast = `
        <div id="${id}" style="background: ${bgColor}; color: white; padding: 12px 20px; border-radius: 30px; margin-bottom: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); display: flex; align-items: center; gap: 8px; animation: slideIn 0.3s ease;">
            <span>${isError ? '❌' : '✅'}</span>
            <span>${escapeHtml(message)}</span>
        </div>
    `;
    toastContainer.append(toast);
    setTimeout(function() {
        $('#' + id).fadeOut(300, function() { $(this).remove(); });
    }, 2000);
};

// ---------- КОПИРОВАНИЕ ТЕЛЕФОНА (ГЛОБАЛЬНОЕ) ----------
window.copyPhoneNumber = function(phone, source = 'unknown') {
    const cleanPhone = phone.replace(/[^\d+]/g, '');
    navigator.clipboard.writeText(cleanPhone).then(function() {
        window.showToast(`📋 Номер скопирован: ${cleanPhone}`);
        if (source === 'table') {
            setTimeout(() => {
                const activeElement = document.activeElement;
                if (activeElement && activeElement.tagName === 'SPAN') {
                    activeElement.style.backgroundColor = '#d4edda';
                    setTimeout(() => { activeElement.style.backgroundColor = ''; }, 200);
                }
            }, 10);
        }
    }).catch(function(err) {
        console.error('Ошибка копирования: ', err);
        window.showToast('Не удалось скопировать номер', true);
    });
};

// ---------- ЗВОНОК ЧЕРЕЗ UIS (ГЛОБАЛЬНОЕ) ----------
window.callUIS = function(phone) {
    let digits = phone.replace(/\D/g, '');
    if (digits.length === 11 && digits[0] === '8') {
        digits = '7' + digits.slice(1);
    } else if (digits.length === 10) {
        digits = '7' + digits;
    } else if (digits.length === 11 && digits[0] === '7') {
        // уже в формате 7XXXXXXXXXX
    } else {
        window.showToast('❌ Неверный формат номера для звонка', true);
        return;
    }
    const uisUrl = `tel:${digits}`;
    try {
        window.location.href = uisUrl;
        window.showToast('📞 Звонок инициирован: ' + digits);
    } catch (e) {
        window.showToast('❌ Не удалось инициировать звонок', true);
    }
};

// ---------- ЛИМИТ ОДНОВРЕМЕННЫХ УВЕДОМЛЕНИЙ ----------
const MAX_NOTIFICATIONS = 10;

// ---------- ПОКАЗ УВЕДОМЛЕНИЯ ----------
window.showNotification = function(call) {
    if (!call || !call.id) {
        console.error('showNotification: некорректные данные', call);
        return;
    }

    if ($(`.notification[data-call-id="${call.id}"]`).length > 0) {
        return;
    }

    try {
        if ($('#notification-container').length === 0) {
            $('body').append('<div id="notification-container"></div>');
        }

        if ($('#notification-container').children().length >= MAX_NOTIFICATIONS) {
            $('#notification-container').children().last().remove();
        }

        const id = 'notif-' + call.id + '-' + Date.now();
        const html = `
            <div id="${id}" class="notification" data-call-id="${call.id}" data-notification-id="${id}">
                <div class="notification-header">
                    <div class="notification-icon">🔔</div>
                    <div class="notification-title">📞 Скоро звонок!</div>
                    <button class="notification-close" onclick="window.closeNotification('${id}')">×</button>
                </div>
                <div class="notification-body">
                    <div><strong>${escapeHtml(call.comment || '')}</strong></div>
                    <div>${escapeHtml(call.phone || '')}</div>
                    <div>⏰ Время: ${escapeHtml(call.next_attempt || '')}</div>
                </div>
                <div class="notification-actions">
                    <button class="btn btn-sm btn-primary" onclick="window.callUIS('${call.phone}'); window.closeNotification('${id}')" title="Позвонить через UIS">📞 Позвонить</button>
                    <button class="btn btn-sm btn-warning" onclick="window.handleNedozvon(${call.id}, '${id}')">📞 Недозвон</button>
                    <button class="btn btn-sm btn-success" onclick="window.handleDozvon(${call.id}, '${id}')">✅ Дозвон</button>
                    <button class="btn btn-sm btn-info" onclick="window.handlePostpone(${call.id}, '${id}')">⏳ +10 мин</button>
                    <button class="btn btn-sm btn-secondary" onclick="window.copyPhoneNumber('${call.phone}', 'notification'); window.closeNotification('${id}')">📋 Копировать</button>
                </div>
            </div>
        `;
        
        $('#notification-container').append(html);
        playNotificationSound();
        
        // Автоматическое скрытие через 15 минут
        setTimeout(() => {
            const notif = $(`#${id}`);
            if (notif.length && !notif.hasClass('fade-out')) {
                window.closeNotification(id);
            }
        }, 900000);
    } catch (e) {
        console.error('Ошибка при показе уведомления:', e);
    }
};

// ---------- ОБРАБОТЧИКИ КНОПОК УВЕДОМЛЕНИЙ ----------
window.handleNedozvon = function(callId, notificationId) {
    $.post('/api/calls/update/', {id: callId})
        .done(function() {
            window.closeNotification(notificationId);
            if (typeof loadCalls === 'function') loadCalls();
        })
        .fail(function(xhr) {
            alert('Ошибка: ' + xhr.responseText);
        });
};

window.handleDozvon = function(callId, notificationId) {
    if (confirm('Отметить звонок как успешный и удалить запись?')) {
        $.post('/api/calls/complete/', {id: callId})
            .done(function() {
                window.closeNotification(notificationId);
                if (typeof loadCalls === 'function') loadCalls();
                if (typeof loadTracking === 'function') loadTracking();
            })
            .fail(function(xhr) {
                alert('Ошибка: ' + xhr.responseText);
            });
    }
};

window.handlePostpone = function(callId, notificationId) {
    $.post('/api/calls/postpone/', {id: callId})
        .done(function() {
            window.closeNotification(notificationId);
            if (typeof loadCalls === 'function') loadCalls();
        })
        .fail(function(xhr) {
            alert('Ошибка: ' + xhr.responseText);
        });
};

// ---------- ЗАКРЫТИЕ УВЕДОМЛЕНИЯ ----------
window.closeNotification = function(id) {
    const el = $('#' + id);
    if (el.length) {
        el.addClass('fade-out');
        setTimeout(() => el.remove(), 300);
    }
};

// ---------- ПРОВЕРКА НОВЫХ УВЕДОМЛЕНИЙ ----------
function checkNotifications() {
    $.get('/api/notifications/')
        .done(function(data) {
            if (data && Array.isArray(data.notifications)) {
                data.notifications.forEach(function(call) {
                    setTimeout(function() {
                        window.showNotification(call);
                    }, 0);
                });
            }
        })
        .fail(function(xhr) {
            console.error('Ошибка проверки уведомлений:', xhr.responseText);
        });
}

// ---------- ЗАГРУЗКА ВКЛАДОК ----------
function loadTab(tabName) {
    $.ajax({
        url: '/api/tab/' + tabName + '/',
        method: 'GET',
        success: function(data) {
            $('#tab-content').html(data);
            if (typeof window['init_' + tabName] === 'function') {
                window['init_' + tabName]();
            }
        },
        error: function() {
            $('#tab-content').html('<div class="alert alert-danger">Ошибка загрузки вкладки</div>');
        }
    });
}

// ---------- ИНИЦИАЛИЗАЦИЯ ПРИ ЗАГРУЗКЕ ----------
$(document).ready(function() {
    loadUserSettings();
    
    // Активируем звук при первом клике на страницу
    $(document).one('click', enableAudio);
    
    $('.nav-link[data-tab]').click(function(e) {
        e.preventDefault();
        var tab = $(this).data('tab');
        loadTab(tab);
        $('.nav-link').removeClass('active');
        $(this).addClass('active');
    });
    
    loadTab('calls');
    
    // Проверка уведомлений каждые 5 секунд (синхронизация со статусом)
    checkNotifications();
    setInterval(checkNotifications, 2000); // изменено с 30000 на 5000
});

// ---------- ОБНОВЛЕНИЕ ГЛОБАЛЬНЫХ НАСТРОЕК ----------
window.updateUserSettings = function(settings) {
    window.userSettings = {
        sound_enabled: settings.sound_enabled,
        volume: settings.volume,
        dark_theme: settings.dark_theme
    };
    applyTheme(settings.dark_theme);
};

// ---------- ЭКРАНИРОВАНИЕ HTML ----------
function escapeHtml(text) {
    var map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, function(m) { return map[m]; });
}

// ---------- ПОЛУЧЕНИЕ ВЫБРАННЫХ ID ----------
function getSelectedIds(checkboxClass) {
    var ids = [];
    $(checkboxClass + ':checked').each(function() {
        ids.push($(this).val());
    });
    return ids;
}