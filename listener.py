#!/usr/bin/env python3
import kidos


def hello_callback(data):
    print(f"Received: {data}")


def main():
    node = kidos.Node('listener')
    node.create_subscription('hello_topic', hello_callback)
    
    print("Listener started. Waiting for messages...")
    node.spin()


if __name__ == '__main__':
    main() 