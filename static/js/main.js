// Основные JavaScript функции для системы мониторинга

document.addEventListener('DOMContentLoaded', function() {
    // Инициализация tooltips Bootstrap
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Автоматическое скрытие alert через 5 секунд
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            if (alert) {
                bootstrap.Alert.getInstance(alert)?.close();
            }
        }, 5000);
    });
});

// Функция для копирования JSON в буфер обмена
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        showToast('Текст скопирован в буфер обмена');
    }, function(err) {
        console.error('Ошибка копирования: ', err);
    });
}

// Функция показа уведомления
function showToast(message, type = 'info') {
    // Создаем простой toast уведомление
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    toast.style.cssText = 'top: 20px; right: 20px; z-index: 1050; min-width: 300px;';
    toast.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(toast);
    
    // Автоматическое скрытие через 3 секунды
    setTimeout(() => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }, 3000);
}

// Функция для экспорта данных в JSON
function exportToJson(data, filename) {
    const dataStr = JSON.stringify(data, null, 2);
    const dataBlob = new Blob([dataStr], {type: 'application/json'});
    
    const link = document.createElement('a');
    link.href = URL.createObjectURL(dataBlob);
    link.download = filename;
    link.click();
    
    URL.revokeObjectURL(link.href);
}

// Функция для загрузки отчета через API
async function loadReport(clientId, hours, date) {
    try {
        const response = await fetch(`/api/reports?client_id=${clientId}&hours=${hours}&date=${date}`);
        const data = await response.json();
        
        if (data.status === 'success') {
            return data.data;
        } else {
            throw new Error(data.message);
        }
    } catch (error) {
        console.error('Ошибка загрузки отчета:', error);
        showToast('Ошибка загрузки отчета: ' + error.message, 'danger');
        return [];
    }
}