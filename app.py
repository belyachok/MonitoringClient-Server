from flask import Flask, render_template, request, jsonify, send_file
from datetime import datetime, timedelta
import json
import os
import uuid
from database import Database
from config import config
from flask import send_from_directory




app = Flask(__name__)
app.config.from_object(config)
app.config['SECRET_KEY'] = 'your-secret-key-here'
MAX_HOURS = 4  # Максимальный разрешенный период

# Инициализация базы данных
db = Database()

pending_requests = {}

# ==================== API ENDPOINTS ====================



@app.route('/api/request-report', methods=['POST'])
def request_report():
    """Сервер запрашивает отчет у клиента"""
    try:
        data = request.json
        client_id = data.get('client_id')
        
        if not client_id:
            return jsonify({
                "status": "error",
                "message": "Не указан client_id"
            }), 400
        
        # Создаем уникальный ID запроса
        request_id = str(uuid.uuid4())
        
        # Сохраняем запрос в ожидании
        pending_requests[request_id] = {
            'client_id': client_id,
            'status': 'pending',  # pending, completed, timeout
            'created_at': datetime.now(),
            'data_received': None
        }
        
        print(f"📤 Запрос отчета отправлен клиенту {client_id}, ID: {request_id}")
        
        return jsonify({
            "status": "success",
            "message": "Запрос отправлен клиенту",
            "request_id": request_id,
            "client_id": client_id
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    

@app.route('/api/check-report-status/<request_id>', methods=['GET'])
def check_report_status(request_id):
    """Проверяет статус запроса отчета"""
    try:
        if request_id not in pending_requests:
            return jsonify({
                "status": "error",
                "message": "Запрос не найден"
            }), 404
        
        request_data = pending_requests[request_id]
        
        # Проверяем timeout (5 минут)
        if (datetime.now() - request_data['created_at']).total_seconds() > 300:
            request_data['status'] = 'timeout'
        
        return jsonify({
            "status": "success",
            "request_status": request_data['status'],
            "client_id": request_data['client_id'],
            "data_received": request_data['data_received'] is not None
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/client-response', methods=['POST'])
def client_response():
    """Клиент отправляет данные в ответ на запрос"""
    try:
        data = request.json
        request_id = data.get('request_id')
        client_data = data.get('data', {})
        
        if not request_id:
            return jsonify({
                "status": "error",
                "message": "Не указан request_id"
            }), 400
        
        if request_id not in pending_requests:
            return jsonify({
                "status": "error",
                "message": "Запрос не найден"
            }), 404
        
        # Обновляем статус запроса
        pending_requests[request_id]['status'] = 'completed'
        pending_requests[request_id]['data_received'] = client_data
        pending_requests[request_id]['completed_at'] = datetime.now()
        
        print(f"✅ Клиент отправил данные для запроса {request_id}")
        
        # Сохраняем данные в базу (опционально)
        if client_data:
            try:
                db.save_event(
                    pending_requests[request_id]['client_id'],
                    'manual_report',
                    datetime.now(),
                    client_data
                )
            except Exception as e:
                print(f"⚠️ Ошибка сохранения данных: {e}")
        
        return jsonify({
            "status": "success",
            "message": "Данные успешно получены"
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/get-report-data/<request_id>', methods=['GET'])
def get_report_data(request_id):
    """Получает данные отчета после ответа клиента"""
    try:
        if request_id not in pending_requests:
            return jsonify({
                "status": "error",
                "message": "Запрос не найден"
            }), 404
        
        request_data = pending_requests[request_id]
        
        if request_data['status'] != 'completed':
            return jsonify({
                "status": "error",
                "message": "Данные еще не получены от клиента"
            }), 400
        
        return jsonify({
            "status": "success",
            "client_id": request_data['client_id'],
            "data": request_data['data_received'],
            "requested_at": request_data['created_at'].isoformat(),
            "completed_at": request_data['completed_at'].isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/favicon.ico')
def favicon():
    """Обработка favicon чтобы не было ошибки 404"""
    return send_from_directory('static', 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/api/test-data')
def create_test_data():
    """Создание тестовых данных для отладки"""
    try:
        test_client_id = "DESKTOP-V9FDTAD"  # Используем реальный ID
        
        # Тестовые события с реальными данными
        test_events = [
            {
                'client_id': test_client_id,
                'data_type': 'website',
                'timestamp': datetime.now(),
                'payload': {'url': 'https://google.com', 'title': 'Google', 'browser': 'Chrome'}
            },
            {
                'client_id': test_client_id, 
                'data_type': 'process',
                'timestamp': datetime.now() - timedelta(minutes=30),
                'payload': {'process_name': 'chrome.exe', 'memory_mb': 250}
            },
            {
                'client_id': test_client_id,
                'data_type': 'website', 
                'timestamp': datetime.now() - timedelta(hours=1),
                'payload': {'url': 'https://yandex.ru', 'title': 'Yandex', 'browser': 'Firefox'}
            },
            {
                'client_id': test_client_id,
                'data_type': 'hardware',
                'timestamp': datetime.now() - timedelta(hours=2),
                'payload': {'computer_name': 'DESKTOP-V9FDTAD', 'cpu': 'Intel i7', 'ram': '16GB'}
            }
        ]
        
        for event in test_events:
            db.save_event(
                event['client_id'],
                event['data_type'], 
                event['timestamp'],
                event['payload']
            )
        
        return jsonify({
            "status": "success", 
            "message": "Тестовые данные созданы", 
            "client_id": test_client_id,
            "events_count": len(test_events)
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_data():
    """Прием данных от клиентов"""
    try:
        data = request.json
        
        # Валидация обязательных полей
        required_fields = ['client_id', 'data_type', 'timestamp', 'payload']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "status": "error", 
                    "message": f"Отсутствует обязательное поле: {field}"
                }), 400
        
        # Парсинг timestamp
        try:
            event_timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify({
                "status": "error", 
                "message": "Неверный формат timestamp"
            }), 400
        
        # ✅ ИСПРАВЛЕНИЕ: Сохраняем hardware данные в правильную таблицу
        if data['data_type'] == 'hardware':
            payload = data['payload']
            # Извлекаем hardware и software из payload
            hardware_info = payload.get('hardware', {})
            software_info = payload.get('software', {})
            
            if hardware_info or software_info:
                success = db.save_hardware_snapshot(
                    data['client_id'],
                    hardware_info,
                    software_info
                )
                if success:
                    print(f"✅ Снимок конфигурации сохранен для {data['client_id']}")
        
        # Сохранение события (оригинальный код)
        success = db.save_event(
            data['client_id'],
            data['data_type'],
            event_timestamp,
            data['payload']
        )
        
        if success:
            return jsonify({
                "status": "success",
                "message": "Данные успешно сохранены"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Ошибка сохранения данных"
            }), 500
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Внутренняя ошибка сервера: {str(e)}"
        }), 500

@app.route('/api/clients', methods=['GET'])
def get_clients():
    """Получение списка клиентов"""
    try:
        clients = db.get_available_clients()
        return jsonify({
            "status": "success",
            "clients": clients
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/reports', methods=['GET'])
def get_reports_api():
    """API для получения отчетов с выбором периода"""
    try:
        client_id = request.args.get('client_id')
        start_time = request.args.get('start')
        end_time = request.args.get('end')
        
        # Валидация обязательных параметров
        if not client_id:
            return jsonify({
                "status": "error",
                "message": "Не указан client_id"
            }), 400
        
        if not start_time or not end_time:
            return jsonify({
                "status": "error",
                "message": "Не указаны start и end параметры времени"
            }), 400
        
        # Валидация формата времени и периода
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        except ValueError:
            return jsonify({
                "status": "error",
                "message": "Неверный формат времени. Используйте ISO формат: YYYY-MM-DDTHH:MM"
            }), 400
        
        # Проверка что период не превышает MAX_HOURS
        time_diff = end_dt - start_dt
        hours_diff = time_diff.total_seconds() / 3600
        
        if hours_diff > MAX_HOURS:
            return jsonify({
                "status": "error", 
                "message": f"Период не может превышать {MAX_HOURS} часов"
            }), 400
        
        if hours_diff <= 0:
            return jsonify({
                "status": "error",
                "message": "Конец периода должен быть после начала"
            }), 400
        
        # Получение данных за указанный период
        report_data = db.get_events_report_by_period(client_id, start_dt, end_dt)
        
        return jsonify({
            "status": "success",
            "client_id": client_id,
            "period": f"{start_time} - {end_time}",
            "duration_hours": round(hours_diff, 2),
            "events_count": len(report_data),
            "data": report_data
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """Получение статистики системы"""
    try:
        stats = db.get_statistics()
        return jsonify({
            "status": "success",
            "statistics": stats
        })
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 500




@app.context_processor
def inject_datetime():
    """Добавляет datetime и timedelta во все шаблоны"""
    return {
        'datetime': datetime,
        'timedelta': timedelta,
        'now': datetime.now
    }

# ==================== WEB INTERFACE ====================

@app.route('/')
def index():
    """Главная страница"""
    try:
        stats = db.get_statistics()
        clients = db.get_available_clients()
        return render_template('index.html', stats=stats, clients=clients)
    except Exception as e:
        return f"Ошибка: {str(e)}", 500

@app.route('/reports')
def reports_page():
    """Страница отчетов с кнопкой запроса"""
    client_id = request.args.get('client_id')
    start_time = request.args.get('start')
    end_time = request.args.get('end')
    
    # Установка периода по умолчанию
    if not start_time or not end_time:
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(hours=MAX_HOURS)
        start_time = start_dt.strftime('%Y-%m-%dT%H:%M')
        end_time = end_dt.strftime('%Y-%m-%dT%H:%M')
    
    report_data = []
    duration_hours = 0
    error_message = None
    
    # Получаем данные из базы (как раньше)
    if client_id and start_time and end_time:
        try:
            start_dt = datetime.fromisoformat(start_time)
            end_dt = datetime.fromisoformat(end_time)
            
            time_diff = end_dt - start_dt
            duration_hours = time_diff.total_seconds() / 3600
            
            if 0 < duration_hours <= MAX_HOURS:
                report_data = db.get_events_report_by_period(client_id, start_dt, end_dt)
            else:
                error_message = f"Период не может превышать {MAX_HOURS} часов"
            
        except ValueError as e:
            error_message = f"Неверный формат времени: {str(e)}"
        except Exception as e:
            error_message = f"Ошибка при получении данных: {str(e)}"
    
    clients = db.get_available_clients()
    
    return render_template('reports.html', 
                         clients=clients,
                         selected_client=client_id,
                         start_time=start_time,
                         end_time=end_time,
                         report_data=report_data,
                         duration_hours=round(duration_hours, 2),
                         max_hours=MAX_HOURS,
                         error_message=error_message)

@app.route('/clients')
def clients_page():
    """Страница управления клиентами"""
    try:
        clients = db.get_available_clients()
        return render_template('clients.html', clients=clients)
    except Exception as e:
        return f"Ошибка: {str(e)}", 500




@app.route('/hardware')
def hardware_page():
    """Страница сравнения конфигураций"""
    client_id = request.args.get('client_id')
    days = int(request.args.get('days', 7))
    
    snapshots = []
    if client_id:
        snapshots = db.get_hardware_snapshots(client_id, days)
    
    clients = db.get_available_clients()
    
    return render_template('hardware.html',
                         clients=clients,
                         selected_client=client_id,
                         days=days,
                         snapshots=snapshots)



# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found_error(error):
    return "Страница не найдена", 404

@app.errorhandler(500)
def internal_error(error):
    return "Внутренняя ошибка сервера", 500





# ==================== MAIN ====================

if __name__ == '__main__':
    # Создаем папки если их нет
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    print("🚀 Запуск сервера мониторинга...")
    print(f"📊 База данных: {config.DB_NAME}")
    print(f"🌐 Веб-интерфейс: http://localhost:5000")
    print(f"⏰ Максимальный период отчета: {MAX_HOURS} часов")
    
    app.run(
        host='0.0.0.0', 
        port=5000, 
        debug=True,
        threaded=True
    )