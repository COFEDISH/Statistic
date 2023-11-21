from flask import Flask, render_template, request, redirect, render_template_string
from collections import defaultdict
from flask_socketio import SocketIO
import string
import socket
import json
import datetime
app = Flask(__name__)

subd_address = ('37.193.53.6', 6379)

def get_current_date():
    today_date = datetime.datetime.today().strftime('%Y-%m-%d')
    return today_date

def process_json_data(json_data):
    # Создаем пустой список для хранения данных
    data_structures = []

    # Преобразуем строку JSON в список словарей
    json_records = json.loads(json_data)

    # Проходим по каждой записи в JSON
    for record in json_records:
        # Если запись содержит URL
        if record.get('URL'):
            # Создаем новую структуру для этого URL
            new_structure = {
                'URL': record['URL'],
                'ip': {}
            }

            # Находим все записи с Pid равным Id этой записи с URL
            related_records = [r for r in json_records if r.get('Pid') == record['Id']]

            # Собираем IP-адреса и временные интервалы из связанных записей
            for related_record in related_records:
                if related_record.get('SourceIP'):
                    # Если IP еще не встречался, добавляем его в структуру
                    if related_record['SourceIP'] not in new_structure['ip']:
                        new_structure['ip'][related_record['SourceIP']] = []

                    # Находим все записи с Pid равным Id этого IP-адреса
                    ip_related_records = [r for r in json_records if r.get('Pid') == related_record['Id']]

                    # Собираем временные интервалы и их количество
                    for ip_related_record in ip_related_records:
                        if ip_related_record.get('TimeInterval'):
                            new_structure['ip'][related_record['SourceIP']].append({
                                'time_interval': ip_related_record['TimeInterval'],
                                'count_time_interval': ip_related_record['Count']
                            })

            # Добавляем созданную структуру в список
            data_structures.append(new_structure)

    return data_structures



def generate_html_table(data):
    ip_table = defaultdict(lambda: defaultdict(int))
    html_table = "<table border='1'>"

    for entry in data:
        url = entry['URL']
        ips = entry['ip']
        for ip, time_intervals in ips.items():
            for time_interval in time_intervals:
                count = time_interval['count_time_interval']
                ip_table[ip]['Total Count'] += count
                ip_table[ip][url] += count

                time_int = time_interval['time_interval']
                ip_table[ip][time_int + '_' + url] += count

    for ip, urls in ip_table.items():
        total_count = urls.pop('Total Count', 0)
        if total_count > 0:
            html_table += f"<tr><td>IP Address: {ip} Count: {total_count}</td></tr>"
            for url, count in urls.items():
                if count > 0 and url != 'Total Count':
                    parts = url.split('_', 1)
                    if len(parts) == 2:
                        time_int, url = parts
                        html_table += f"<tr><td>&emsp;Time: {time_int} Count: {count}</td></tr>"
                        html_table += f"<tr><td>&emsp;&emsp;URL: {url}, Count: {count}</td></tr>"

    html_table += "</table>"
    return html_table


@app.route('/', methods=['GET', 'POST'])
def display_data():
        date = get_current_date()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect(subd_address)
                s.sendall(f"--file data{date}.json --query 'GSON get'".encode())
                print("Message sent successfully.")
                datas_subd = s.recv(16384)
                data_sub = datas_subd.decode()
                print(data_sub)
            except ConnectionRefusedError:
                print("Connection to the server failed.")

        result = process_json_data(data_sub)

        html_table = generate_html_table(result)
        return render_template_string(html_table)



if __name__ == '__main__':
    app.run(host='192.168.0.105', port=50011, debug=True)