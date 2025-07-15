#!/usr/bin/env python3
import socket
import threading
import json


class Master:
    def __init__(self, host='0.0.0.0', port=12345):
        self.host = host
        self.port = port
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._clients = []
        self._subscriptions = {}
        self._publishers = {}

    def start(self):
        self._server_sock.bind((self.host, self.port))
        self._server_sock.listen(5)
        print(f"Master started on {self.host}:{self.port}")
        
        try:
            while True:
                client_socket, address = self._server_sock.accept()
                print(f"New client connected: {address}")
                self._clients.append(client_socket)
                client_thread = threading.Thread(target=self._handle_client, args=(client_socket,))
                client_thread.daemon = True
                client_thread.start()
        except KeyboardInterrupt:
            print("Master shutting down...")
        finally:
            self._server_sock.close()

    def _handle_client(self, client_socket):
        try:
            while True:
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                
                for line in data.strip().split('\n'):
                    if line:
                        message = json.loads(line)
                        action = message.get('action')
                        payload = message.get('payload', {})
                        
                        if action == 'register_node':
                            print(f"Node registered: {payload.get('node_name')}")
                        
                        elif action == 'register_publisher':
                            topic = payload.get('topic')
                            if topic not in self._publishers:
                                self._publishers[topic] = []
                            self._publishers[topic].append(client_socket)
                            print(f"Publisher registered for topic: {topic}")
                        
                        elif action == 'register_subscriber':
                            topic = payload.get('topic')
                            if topic not in self._subscriptions:
                                self._subscriptions[topic] = []
                            self._subscriptions[topic].append(client_socket)
                            print(f"Subscriber registered for topic: {topic}")
                        
                        elif action == 'publish':
                            topic = payload.get('topic')
                            data_content = payload.get('data')
                            if topic in self._subscriptions:
                                forward_msg = {
                                    'action': 'forward_message',
                                    'payload': {
                                        'topic': topic,
                                        'data': data_content
                                    }
                                }
                                forward_json = json.dumps(forward_msg) + '\n'
                                
                                for subscriber_socket in self._subscriptions[topic]:
                                    try:
                                        subscriber_socket.send(forward_json.encode('utf-8'))
                                    except:
                                        pass
        
        except Exception as e:
            print(f"Client error: {e}")
        finally:
            if client_socket in self._clients:
                self._clients.remove(client_socket)
            
            for topic_subs in self._subscriptions.values():
                if client_socket in topic_subs:
                    topic_subs.remove(client_socket)
            
            for topic_pubs in self._publishers.values():
                if client_socket in topic_pubs:
                    topic_pubs.remove(client_socket)
            
            client_socket.close()


if __name__ == '__main__':
    master = Master()
    master.start() 