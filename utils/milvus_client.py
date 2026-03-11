import requests
import json
import time

class MilvusClient:
    # TODO: Need a more comprehensive retrieval mechanism

    def __init__(self, base_url="http://localhost:5002"):
        self.base_url = base_url
        
    def insert_experience(self, data):
        """
        插入经验数据到Milvus数据库
        
        Args:
            data: 包含经验描述的字典列表
            
        Returns:
            服务器响应
        """
        url = f"{self.base_url}/api/insert/experience"
        
        # 如果传入的是列表，直接使用；否则包装成列表
        if isinstance(data, list):
            payload = {"data": data}
        else:
            # 原有的单个数据处理逻辑
            data = [{
                "description": data,
                "timestamp": int(time.time())
            }]
            payload = {"data": data}
        
        try:
            response = requests.post(url, json=payload)
            return response.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def search_experience(self, query_data):
        """
        从Milvus数据库搜索经验数据
        
        Args:
            query_data: 查询数据
            
        Returns:
            服务器响应
        """
        url = f"{self.base_url}/api/search/experience"
        
        try:
            response = requests.post(url, json={"data": query_data})
            return response.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}

def test_milvus_client():
    """
    测试Milvus客户端的基本功能
    """
    print("开始测试Milvus客户端...")
    
    # 创建客户端实例
    client = MilvusClient()
    
    # 准备测试数据
    test_data = [
        {
            "description": "机器人在厨房找到了一个红色的苹果",
            "timestamp": int(time.time())
        },
        {
            "description": "机器人在客厅的桌子上发现了一个蓝色的杯子",
            "timestamp": int(time.time())
        },
        {
            "description": "机器人在卧室的床头柜上看到一个绿色的台灯",
            "timestamp": int(time.time())
        }
    ]
    
    # 测试插入功能
    print("\n1. 测试插入功能...")
    insert_result = client.insert_experience(test_data)
    print(f"插入结果: {insert_result}")
    
    if insert_result.get("status") != "success":
        print("插入失败，终止测试")
        return
    
    # 等待一段时间确保数据被处理
    time.sleep(2)
    
    # 测试查询功能
    print("\n2. 测试查询功能...")
    query_data = "寻找一个水果"
    search_result = client.search_experience(query_data)
    print(f"查询结果: {search_result}")
    
    print("\n测试完成!")

if __name__ == "__main__":
    # 运行测试
    test_milvus_client()