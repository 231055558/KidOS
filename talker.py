#!/usr/bin/env python3
import kidos
import time


def main():
    node = kidos.Node('talker')
    pub = node.create_publisher('hello_topic')
    
    count = 0
    try:
        while True:
            message = f"Hello KidOS! Count: {count}"
            pub.publish(message)
            print(f"Published: {message}")
            count += 1
            time.sleep(1)
    except KeyboardInterrupt:
        node.destroy_node()


if __name__ == '__main__':
    main() 