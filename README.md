# `KidOS`: 一个极简Python机器人系统设计文档

## 1. 系统概述

`KidOS` 是一个专为教育目的设计的、受ROS2启发的微型机器人操作系统。它的核心目标是让初高中学生能够理解、复现并使用一个基本的发布/订阅（Pub/Sub）通信框架来构建简单的多进程机器人应用。

### 核心设计原则：

*   **教育性优先**: 透明度高于一切。代码必须易于阅读和理解，避免复杂的优化和抽象。
*   **中心化架构**: 采用“中央调度器”（Master/Broker）模式，而非ROS2的去中心化发现机制。这种C/S架构对初学者来说逻辑最清晰。
*   **极简依赖**: 仅使用Python标准库（`socket`, `threading`, `json`, `subprocess`），无需安装任何第三方通信库。
*   **隐喻驱动**: 系统的所有组件都与课程中使用的“工人/频道”等隐喻强对应。

## 2. 系统架构

系统由三部分组成：

1.  **中央调度器 (Master)**: 一个独立的Python脚本 (`master.py`)。它是整个系统的神经中枢，所有节点都必须先连接到它。
2.  **KidOS核心库 (`kidos.py`)**: 一个Python模块，提供了面向用户的API。学生通过`import kidos`来使用我们定义的类，从而创建节点、发布者和订阅者。
3.  **用户节点 (Node)**: 任意数量的、由学生编写的Python脚本。每个脚本都是一个“工人”，执行特定的任务（如读取传感器、控制电机等）。


*(这里可以用一个简单的流程图来表示：多个Node箭头指向Master，Master再箭头指向其他Node)*

## 3. 通信方案

### 3.1. 底层协议

*   **传输层**: 使用 **TCP/IP** 协议。TCP提供了可靠的、面向连接的字节流服务，避免了处理UDP丢包等复杂问题，适合教学。
*   **通信模型**: 基于`socket`库实现的客户端/服务器（C/S）模型。
    *   **服务器**: `Master`节点。
    *   **客户端**: 每一个`User Node`。

### 3.2. 数据格式

*   **消息序列化**: 使用 **JSON (JavaScript Object Notation)**。
    *   **优点**: 人类可读，Python内置`json`库支持良好，易于调试。
    *   **格式**: 每个在网络上传输的逻辑单元都是一个JSON字符串，并以换行符`\n`作为消息分隔符，以解决TCP的“粘包”问题。

### 3.3. 通信协议定义

客户端（Node）与服务器（Master）之间的所有通信都遵循以下JSON结构：

```json
{
  "action": "ACTION_TYPE",
  "payload": { ... }
}
```

*   **`action`**: 字符串，定义了消息的目的。
*   **`payload`**: 对象，包含了该`action`所需的具体数据。

定义的`action`类型包括：

1.  **`register_node`**: 节点启动时向Master注册。
    *   `payload`: `{"node_name": "motor_controller"}`
2.  **`register_publisher`**: 节点声明它要在一个主题上发布消息。
    *   `payload`: `{"topic": "cmd_vel"}`
3.  **`register_subscriber`**: 节点声明它要订阅一个主题。
    *   `payload`: `{"topic": "cmd_vel"}`
4.  **`publish`**: 节点发布一条消息到特定主题。
    *   `payload`: `{"topic": "cmd_vel", "data": {"linear_x": 0.5, "angular_z": 0.0}}`
5.  **`forward_message`** (Master to Node): Master将消息转发给订阅者。
    *   `payload`: `{"topic": "cmd_vel", "data": {"linear_x": 0.5, "angular_z": 0.0}}`

## 4. 核心类定义 (`kidos.py`)

这是学生将直接接触和使用的部分。我们需要定义三个核心类。

### 4.1. `class kidos.Node`

代表一个“工人”或机器人系统中的一个独立进程。

*   **职责**:
    *   初始化时连接到Master。
    *   管理该节点下的发布者和订阅者。
    *   作为工厂，创建`Publisher`和`Subscription`实例。
    *   在后台线程中持续监听来自Master的消息，并分发给对应的回调函数。
    *   提供一个`spin()`方法来保持主线程活跃。

*   **属性**:
    *   `node_name` (str): 节点名称。
    *   `_sock` (socket.socket): 与Master通信的socket对象。
    *   `_callbacks` (dict): 一个字典，键是`topic`，值是对应的回调函数。`{"scan": on_scan_received}`。
    *   `_is_running` (bool): 控制监听线程的循环。

*   **方法**:
    *   `__init__(self, node_name: str, master_host='127.0.0.1', master_port=12345)`:
        *   连接到Master。
        *   向Master发送`register_node`消息。
        *   启动后台监听线程 `_listen_to_master()`.
    *   `create_publisher(self, topic_name: str) -> Publisher`:
        *   向Master发送`register_publisher`消息。
        *   返回一个`Publisher`类的实例。
    *   `create_subscription(self, topic_name: str, callback: callable)`:
        *   向Master发送`register_subscriber`消息。
        *   将`topic_name`和`callback`存入`_callbacks`字典。
    *   `spin(self)`:
        *   进入一个`while self._is_running:`循环，让主程序不退出。
    *   `destroy_node(self)`:
        *   设置`_is_running = False`，关闭socket连接，优雅地退出。
    *   `_listen_to_master(self)` (私有方法):
        *   在一个单独的线程中运行。
        *   循环接收来自Master的数据，解析JSON。
        *   如果消息是`forward_message`，则根据`topic`查找`_callbacks`字典并调用相应的回调函数，将`data`传入。

### 4.2. `class kidos.Publisher`

代表一个消息的发布者。

*   **职责**:
    *   提供一个简单的`publish()`方法来发送数据。

*   **属性**:
    *   `_sock` (socket.socket): 从`Node`对象继承的socket连接。
    *   `topic_name` (str): 该发布者绑定的主题名称。

*   **方法**:
    *   `__init__(self, sock, topic_name)`:
        *   由`Node.create_publisher()`内部调用，不应由用户直接实例化。
    *   `publish(self, data)`:
        *   将数据打包成`{"action": "publish", "payload": {"topic": self.topic_name, "data": data}}`的格式。
        *   序列化为JSON字符串，并通过socket发送给Master。

### 4.3. `class kidos.Master` (在 `master.py` 中实现)

代表中央调度器。这是一个独立的、需要首先运行的服务器程序。

*   **职责**:
    *   监听指定的端口，等待节点连接。
    *   为每个连接的节点创建一个处理线程。
    *   维护系统的全局状态信息。
    *   根据节点发来的消息，执行相应的注册或转发操作。

*   **属性**:
    *   `_server_sock` (socket.socket): 服务器监听socket。
    *   `_clients` (list): 存储所有客户端socket连接的列表。
    *   `_subscriptions` (dict): 核心数据结构，记录订阅信息。格式：`{"topic_name": [client_socket_1, client_socket_2, ...]}`。
    *   `_publishers` (dict, 可选): 记录发布者信息，用于管理和调试。格式：`{"topic_name": [client_socket_3, ...]}`。

*   **方法**:
    *   `__init__(self, host='0.0.0.0', port=12345)`:
        *   创建并绑定服务器socket。
    *   `start(self)`:
        *   开始监听连接。
        *   进入一个主循环，`accept()`新的客户端连接，并为每个连接创建一个新的`_handle_client`线程。
    *   `_handle_client(self, client_socket)` (私有方法):
        *   在一个单独的线程中为每个客户端服务。
        *   循环接收来自该客户端的数据。
        *   解析JSON消息，根据`action`执行不同逻辑：
            *   **`register_subscriber`**: 将`client_socket`添加到`_subscriptions`字典中对应`topic`的列表里。
            *   **`register_publisher`**: (可选)记录发布者。
            *   **`publish`**: 遍历`_subscriptions`中对应`topic`的所有订阅者socket，将消息（包装成`forward_message`格式）转发给他们。
        *   处理客户端断开连接的异常，将其从所有数据结构中清理掉。

## 5. 开发与教学步骤

1.  **第一步：实现`Master`**
    *   编写`master.py`。这是课程中需要手搓的第一部分。重点讲解socket服务器、多线程处理客户端以及核心数据结构`_subscriptions`的设计。

2.  **第二步：实现`KidOS`核心库**
    *   编写`kidos.py`。这是手搓的第二部分。重点讲解如何将底层的socket通信封装成易于使用的`Node`, `Publisher`类。强调“封装”的思想。

3.  **第三步：编写示例应用**
    *   编写简单的`talker.py`和`listener.py`。这是课程的实践案例，展示如何使用`kidos`库。学生在此阶段，只需关注应用逻辑，无需关心底层通信细节。

