from flask import Flask, render_template, Response
from flask_sslify import SSLify
import socket
import fcntl
import struct
import subprocess
import re
import psycopg2
from dotenv import load_dotenv
import os
import atexit

# Load environment variables from env-setup file
load_dotenv(dotenv_path='env')

app = Flask(__name__)
sslify = SSLify(app)

# Define connection parameters
conn_params = {
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT'),
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
}

def get_local_ip_address(interface_name):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        local_ip_address = socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915,  # SIOCGIFADDR
            struct.pack('256s', bytes(interface_name, 'utf-8')[:15])
        )[20:24])

        return local_ip_address

    except Exception as e:
        print(f"Terjadi kesalahan: {e}")
        return None

def get_network_interfaces():
    try:
        result = subprocess.check_output(["ifconfig"]).decode("utf-8")
        interface_lines = re.findall(r'^\s*(ens\w*|eth\w*):', result, re.MULTILINE)
        return interface_lines
    except subprocess.CalledProcessError as e:
        print("Error executing ifconfig:", e)
        return None

def get_local_ip_from_selected_interface(selected_interface):
    ip_address = get_local_ip_address(selected_interface)
    if ip_address:
        return ip_address
    else:
        return None

def get_primary_db_ip():
    try:
        conn_string = f"postgres://{conn_params['user']}:{conn_params['password']}@{conn_params['host']}:{conn_params['port']}/{conn_params['dbname']}"
        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor()
        cursor.execute("SELECT primary_host FROM pgautofailover.get_primary()")
        primary_info = cursor.fetchone()
        cursor.close()

        if primary_info is not None:
            return primary_info[0]
        else:
            return None

    except Exception as e:
        print(f"Error: {e}")
        return None

    finally:
        if 'conn' in locals() and conn is not None:
            conn.close()

def kill_port(port):
    try:
        subprocess.run(["fuser", "-k", f"{port}/tcp"])
    except Exception as e:
        print(f"Error killing port {port}: {e}")

@app.route('/')
def status():
    interfaces = get_network_interfaces()

    if interfaces:
        selected_interface = interfaces[0]
        local_ip = get_local_ip_from_selected_interface(selected_interface)
        primary_db_ip = get_primary_db_ip()

        if local_ip and primary_db_ip:
            if local_ip == primary_db_ip:
                return Response("primary", status=200, mimetype='text/plain')
            else:
                return Response("slave", status=503, mimetype='text/plain')
        else:
            return Response("Tidak dapat mendapatkan IP lokal atau IP dari cek-primarydb.py.", status=500, mimetype='text/plain')
    else:
        return Response("Tidak ada antarmuka yang ditemukan.", status=500, mimetype='text/plain')

if __name__ == '__main__':
    atexit.register(kill_port, 5000)
    app.run(debug=True, host='0.0.0.0', port=5000)

