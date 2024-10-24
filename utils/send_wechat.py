import requests
from requests.auth import HTTPBasicAuth
import json
from minio import Minio
from minio.error import S3Error
from datetime import datetime
import os
# from dotenv import load_dotenv

# # 加载 .env 文件
# load_dotenv()

# 从环境变量获取配置
base_url = os.getenv('API_BASE_URL')
username = os.getenv('API_USERNAME')
password = os.getenv('API_PASSWORD')

# 创建一个会话对象,用于所有请求
session = requests.Session()
session.auth = HTTPBasicAuth(username, password)


def upload_to_minio():
    # MinIO 客户端配置
    minio_client = Minio(
        os.getenv('MINIO_ENDPOINT'),
        access_key=os.getenv('MINIO_ACCESS_KEY'),
        secret_key=os.getenv('MINIO_SECRET_KEY'),
        secure=False  # 使用 HTTP
    )

    # 准备上传参数
    bucket_name = os.getenv('MINIO_BUCKET_NAME')
    current_time = datetime.now().strftime("%Y-%m-%d@%H:%M:%S")
    object_name = f"auto_img/{current_time}/douyin_login_qr.png"
    file_path = "cookies/douyin_login_qr.png"

    try:
        # 上传文件
        minio_client.fput_object(bucket_name, object_name, file_path)
        print(f"文件 '{file_path}' 已成功上传到 '{bucket_name}/{object_name}'")

        # 生成 URL
        url = f"http://{os.getenv('MINIO_ENDPOINT')}/{bucket_name}/{object_name}"
        return url
    except S3Error as e:
        print(f"上传失败: {e}")
        return None


def get_earliest_receiver():
    url = f'{base_url}/get_receivers'
    headers = {
        'accept': 'application/json'
    }

    try:
        response = session.get(url, headers=headers)
        if response.status_code == 200:
            receivers = response.json()
            if receivers:
                earliest_receiver = min(receivers.items(), key=lambda x: x[1])
                return earliest_receiver[0]  # 返回 user_id
            else:
                print("没有可用的接收者")
                return None
        else:
            print(f"获取接收者失败,状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
            return None
    except Exception as e:
        print(f"获取接收者时发生错误: {str(e)}")
        return None


def send_message(send_message: str):
    send_text_url = f'{base_url}/send_text_message'
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }

    user_id = get_earliest_receiver()
    if not user_id:
        print("无法获取有效的 user_id,消息发送失败")
        return

    send_message = {
        "user_id": user_id,
        "message": send_message
    }

    try:
        response = session.post(send_text_url, headers=headers, json=send_message)
        if response.status_code == 200:
            print("消息发送成功")
            print(response.json())
        else:
            print(f"发送失败,状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
    except Exception as e:
        print(f"发送消息时发生错误: {str(e)}")


def send_image_url(image_url: str):
    url = f'{base_url}/send_image_url'
    send_text_url = f'{base_url}/send_text_message'
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }

    user_id = get_earliest_receiver()
    if not user_id:
        print("无法获取有效的 user_id,消息发送失败")
        return

    data = {
        "user_id": user_id,
        "image_url": image_url
    }

    send_message = {
        "user_id": user_id,
        "message": "抖音平台 cookies 已过期;请重新扫码登录!"
    }

    print(data)

    try:
        session.post(send_text_url, headers=headers, json=send_message)
        response = session.post(url, headers=headers, json=data)
        if response.status_code == 200:
            print("图片消息发送成功")
            print(response.json())
        else:
            print(f"发送失败,状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
    except Exception as e:
        print(f"发送消息时发生错误: {str(e)}")


def run_workflow(api_key: str):
    url = os.getenv('DIFY_API_URL')
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    # 上传图片并获取 URL
    image_url = upload_to_minio()
    print(image_url)
    if not image_url:
        print("图片上传失败,无法继续执行工作流")
        return

    # 发送图片消息
    send_image_url(image_url)

    data = {
        "inputs": {"query": f"img_url:{image_url}"},
        "response_mode": "blocking",
        "user": "NarratoAI 客服"
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=100)

        if response.status_code == 200:
            result = response.json()
            print("工作流执行结果:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"请求失败,状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
    except requests.exceptions.Timeout:
        print("请求超时,可能是由于工作流执行时间过长导致。")
    except Exception as e:
        print(f"发生错误: {str(e)}")


def send_image_file(file_path: str):
    url = f'{base_url}/send_image_file'
    headers = {
        'accept': 'application/json'
    }

    user_id = get_earliest_receiver()
    if not user_id:
        print("无法获取有效的 user_id,图片文件发送失败")
        return

    try:
        with open(file_path, 'rb') as file:
            files = {'file': (os.path.basename(file_path), file, 'image/png')}
            params = {'user_id': user_id}
            response = session.post(url, headers=headers, params=params, files=files)

        if response.status_code == 200:
            print("图片文件发送成功")
            print(response.json())
        else:
            print(f"发送失败,状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
    except Exception as e:
        print(f"发送图片文件时发生错误: {str(e)}")


if __name__ == "__main__":
    # 上传图片到 MinIO 并发送图片 URL
    # image_url = upload_to_minio()
    # send_image_message(image_url)
    # print(image_url)

    # 直接发送图片文件
    file_path = "cookies/douyin_login_qr.png"  # 确保这个路径是正确的
    send_image_file(file_path)
