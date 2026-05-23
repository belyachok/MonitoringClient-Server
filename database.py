import psycopg2
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from config import config

class Database:
    def __init__(self):
        self.connection = None
        self.connect()
    
    def connect(self):
        """Установка подключения к PostgreSQL"""
        try:
            self.connection = psycopg2.connect(
                host=config.DB_HOST,
                database=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASSWORD,
                port=config.DB_PORT
            )
            print("✅ Успешное подключение к PostgreSQL")
        except Exception as e:
            print(f"❌ Ошибка подключения к PostgreSQL: {e}")
            raise
    
    def ensure_connection(self):
        """Проверка и восстановление подключения"""
        try:
            if self.connection is None or self.connection.closed:
                self.connect()
        except Exception as e:
            print(f"Ошибка восстановления подключения: {e}")
            raise
    
    def save_event(self, client_id: str, data_type: str, timestamp: datetime, payload: Dict[str, Any]) -> bool:
        """Сохраняет событие в базу данных"""
        self.ensure_connection()
        
        try:
            with self.connection.cursor() as cursor:
                # Обновляем время последнего контакта клиента
                cursor.execute("""
                    INSERT INTO clients (client_id, computer_name, last_seen) 
                    VALUES (%s, %s, %s)
                    ON CONFLICT (client_id) 
                    DO UPDATE SET 
                        last_seen = EXCLUDED.last_seen,
                        computer_name = EXCLUDED.computer_name
                """, (client_id, payload.get('computer_name', 'Unknown'), timestamp))
                
                # Сохраняем событие
                cursor.execute("""
                    INSERT INTO events (client_id, data_type, timestamp, payload)
                    VALUES (%s, %s, %s, %s)
                """, (client_id, data_type, timestamp, json.dumps(payload, ensure_ascii=False)))
                
                self.connection.commit()
                print(f"✅ Событие сохранено: {client_id} - {data_type}")
                return True
                
        except Exception as e:
            print(f"❌ Ошибка сохранения события: {e}")
            self.connection.rollback()
            return False
    
    # В методе get_events_report_by_period добавьте обработку данных для красивого отображения:

    def get_events_report_by_period(self, client_id: str, start_dt: datetime, end_dt: datetime) -> List[Dict]:
        """Получает события за указанный период времени"""
        self.ensure_connection()
        
        try:
            print(f"🔍 Поиск событий для: {client_id}")
            print(f"⏰ Период: {start_dt} - {end_dt}")
            
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        id,
                        client_id,
                        data_type,
                        timestamp,
                        payload,
                        created_at
                    FROM events 
                    WHERE client_id = %s 
                    AND timestamp BETWEEN %s AND %s
                    ORDER BY timestamp DESC
                """, (client_id, start_dt, end_dt))
                
                columns = [desc[0] for desc in cursor.description]
                results = []
                
                for row in cursor.fetchall():
                    row_dict = dict(zip(columns, row))
                    # Парсим JSON payload и форматируем для красивого отображения
                    if isinstance(row_dict['payload'], str):
                        try:
                            payload_data = json.loads(row_dict['payload'])
                            # Форматируем данные для лучшего отображения
                            row_dict['payload'] = self.format_payload_for_display(payload_data, row_dict['data_type'])
                        except json.JSONDecodeError:
                            row_dict['payload'] = {"raw_data": row_dict['payload']}
                    results.append(row_dict)
                
                print(f"📊 Найдено событий: {len(results)}")
                return results
                
        except Exception as e:
            print(f"❌ Ошибка получения отчета по периоду: {e}")
            return []

    def format_payload_for_display(self, payload: Dict, data_type: str) -> Dict:
        """Форматирует данные для красивого отображения в отчете"""
        formatted = payload.copy()
        
        if data_type == 'website':
            # Упрощаем URL для отображения
            if 'url' in formatted:
                url = formatted['url']
                if url.startswith(('http://', 'https://')):
                    formatted['url'] = url.split('//', 1)[1]
            
            # Улучшаем название браузера
            if 'browser' in formatted:
                browser = formatted['browser'].lower()
                if 'chrome' in browser:
                    formatted['browser'] = 'Chrome'
                elif 'firefox' in browser:
                    formatted['browser'] = 'Firefox'
                elif 'edge' in browser:
                    formatted['browser'] = 'Edge'
                elif 'safari' in browser:
                    formatted['browser'] = 'Safari'
        
        elif data_type == 'process':
            # Упрощаем название процесса
            if 'process_name' in formatted:
                process_name = formatted['process_name']
                if '.exe' in process_name.lower():
                    formatted['process_name'] = process_name.replace('.exe', '')
        
        elif data_type == 'usb':
            # Руссифицируем действия
            if 'action' in formatted:
                action = formatted['action'].lower()
                if 'connected' in action:
                    formatted['action'] = 'connected'
                elif 'disconnected' in action:
                    formatted['action'] = 'disconnected'
        
        return formatted
    
    def get_events_report(self, client_id: str, hours: int, target_date: datetime) -> List[Dict]:
        """Получает отчет за указанный период (для обратной совместимости)"""
        start_time = datetime.combine(target_date, datetime.min.time())
        end_time = start_time + timedelta(hours=hours)
        
        return self.get_events_report_by_period(client_id, start_time, end_time)
    
    def get_available_clients(self) -> List[Dict]:
        """Получает список всех клиентов с информацией"""
        self.ensure_connection()
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        client_id,
                        computer_name,
                        ip_address,
                        last_seen,
                        created_at
                    FROM clients 
                    ORDER BY last_seen DESC
                """)
                
                columns = [desc[0] for desc in cursor.description]
                clients = []
                
                for row in cursor.fetchall():
                    clients.append(dict(zip(columns, row)))
                
                return clients
                
        except Exception as e:
            print(f"❌ Ошибка получения клиентов: {e}")
            return []
    
    def save_hardware_snapshot(self, client_id: str, hardware_data: Dict, software_data: Dict) -> bool:
        """Сохраняет или обновляет снимок конфигурации"""
        self.ensure_connection()
        
        try:
            snapshot_date = datetime.now().date()
            
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO hardware_snapshots (client_id, snapshot_date, hardware_data, software_data)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (client_id, snapshot_date) 
                    DO UPDATE SET 
                        hardware_data = EXCLUDED.hardware_data,
                        software_data = EXCLUDED.software_data,
                        created_at = CURRENT_TIMESTAMP
                """, (client_id, snapshot_date, json.dumps(hardware_data), json.dumps(software_data)))
                
                self.connection.commit()
                print(f"✅ Снимок конфигурации сохранен: {client_id}")
                return True
                
        except Exception as e:
            print(f"❌ Ошибка сохранения снимка: {e}")
            self.connection.rollback()
            return False
    
    def get_hardware_snapshots(self, client_id: str, days: int = 7) -> List[Dict]:
        """Получает снимки конфигурации за последние N дней"""
        self.ensure_connection()
        
        try:
            start_date = datetime.now().date() - timedelta(days=days)
            
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        snapshot_date,
                        hardware_data,
                        software_data,
                        created_at
                    FROM hardware_snapshots 
                    WHERE client_id = %s AND snapshot_date >= %s
                    ORDER BY snapshot_date DESC
                """, (client_id, start_date))
                
                columns = [desc[0] for desc in cursor.description]
                snapshots = []
                
                for row in cursor.fetchall():
                    snapshot = dict(zip(columns, row))
                    # Парсим JSON данные
                    if isinstance(snapshot['hardware_data'], str):
                        snapshot['hardware_data'] = json.loads(snapshot['hardware_data'])
                    if isinstance(snapshot['software_data'], str):
                        snapshot['software_data'] = json.loads(snapshot['software_data'])
                    snapshots.append(snapshot)
                
                return snapshots
                
        except Exception as e:
            print(f"❌ Ошибка получения снимков: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получает статистику по системе"""
        self.ensure_connection()
        
        try:
            with self.connection.cursor() as cursor:
                # Общая статистика
                cursor.execute("""
                    SELECT 
                        COUNT(DISTINCT client_id) as total_clients,
                        COUNT(*) as total_events,
                        MAX(timestamp) as last_event
                    FROM events
                """)
                stats = dict(zip(['total_clients', 'total_events', 'last_event'], cursor.fetchone()))
                
                # Статистика по типам событий
                cursor.execute("""
                    SELECT data_type, COUNT(*) 
                    FROM events 
                    GROUP BY data_type 
                    ORDER BY COUNT(*) DESC
                """)
                stats['events_by_type'] = {row[0]: row[1] for row in cursor.fetchall()}
                
                # Активные клиенты (за последние 24 часа)
                cursor.execute("""
                    SELECT COUNT(DISTINCT client_id) 
                    FROM events 
                    WHERE timestamp >= NOW() - INTERVAL '24 hours'
                """)
                stats['active_clients_24h'] = cursor.fetchone()[0]
                
                return stats
                
        except Exception as e:
            print(f"❌ Ошибка получения статистики: {e}")
            return {}
       
    def close(self):
        """Закрытие подключения"""
        if self.connection and not self.connection.closed:
            self.connection.close()
            print("✅ Подключение к PostgreSQL закрыто")





            