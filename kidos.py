import socket
import threading
import json
import time


class Publisher:
    def __init__(self, sock, topic_name):
        self._sock = sock
        self.topic_name = topic_name

    def publish(self, data):
        message = {
            'action': 'publish',
            'payload': {
                'topic': self.topic_name,
                'data': data
            }
        }
        message_json = json.dumps(message) + '\n'
        self._sock.send(message_json.encode('utf-8'))


class Node:
    def __init__(self, node_name, master_host='127.0.0.1', master_port=12345):
        self.node_name = node_name
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._callbacks = {}
        self._is_running = True
        
        self._sock.connect((master_host, master_port))
        
        register_msg = {
            'action': 'register_node',
            'payload': {'node_name': node_name}
        }
        register_json = json.dumps(register_msg) + '\n'
        self._sock.send(register_json.encode('utf-8'))
        
        listen_thread = threading.Thread(target=self._listen_to_master)
        listen_thread.daemon = True
        listen_thread.start()

    def create_publisher(self, topic_name):
        register_msg = {
            'action': 'register_publisher',
            'payload': {'topic': topic_name}
        }
        register_json = json.dumps(register_msg) + '\n'
        self._sock.send(register_json.encode('utf-8'))
        
        return Publisher(self._sock, topic_name)

    def create_subscription(self, topic_name, callback):
        register_msg = {
            'action': 'register_subscriber',
            'payload': {'topic': topic_name}
        }
        register_json = json.dumps(register_msg) + '\n'
        self._sock.send(register_json.encode('utf-8'))
        
        self._callbacks[topic_name] = callback

    def spin(self):
        try:
            while self._is_running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.destroy_node()

    def destroy_node(self):
        self._is_running = False
        self._sock.close()

    def _listen_to_master(self):
        try:
            while self._is_running:
                data = self._sock.recv(1024).decode('utf-8')
                if not data:
                    break
                
                for line in data.strip().split('\n'):
                    if line:
                        message = json.loads(line)
                        action = message.get('action')
                        
                        if action == 'forward_message':
                            payload = message.get('payload', {})
                            topic = payload.get('topic')
                            data_content = payload.get('data')
                            
                            if topic in self._callbacks:
                                self._callbacks[topic](data_content)
        
        except Exception as e:
            if self._is_running:
                print(f"Listen error: {e}")
        finally:
            if self._is_running:
                self.destroy_node() 