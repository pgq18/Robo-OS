from pymilvus import DataType
from pymilvus import Function, FunctionType
from pymilvus import MilvusClient, DataType
from pymilvus import model

from flask import Flask, Response, jsonify, request, send_file, render_template_string
app = Flask(__name__)
import time
import json
import random

class MemoryDataBase():
    def __init__(self, init=True):
        self.embedding_fn = model.DefaultEmbeddingFunction()
        if init:
            self.client = MilvusClient("test.db")
            self.init_db()
        else:
            self.client = MilvusClient("test.db")

    def init_db(self):
        object_schema = MilvusClient.create_schema(
            auto_id=False,
            enable_dynamic_field=True,
        )
        object_schema.add_field(field_name="id",    datatype=DataType.INT64, is_primary=True, auto_id=True, description="object id")
        object_schema.add_field(field_name="description",  datatype=DataType.VARCHAR, enable_analyzer=True, enable_match=True, max_length=200, description="description")
        object_schema.add_field(field_name="timestamp",    datatype=DataType.INT32, description="publish time")
        object_schema.add_field(field_name="dense_vector", datatype=DataType.FLOAT_VECTOR, dim=768, description="text dense vector")
        index_params = self.client.prepare_index_params()
        index_params.add_index(
            field_name="dense_vector", 
            index_type="AUTOINDEX",
            metric_type="COSINE"
        )
        self.client.create_collection(
            collection_name="experience_collection",
            schema=object_schema,
            index_params=index_params
        )
    
    def insert(self, data):
        res = self.client.insert(
            collection_name="experience_collection",
            data=data
        )
        return res
    
    def search_object(self, query):
        res = self.client.search(
            collection_name="experience_collection",  # target collection
            anns_field="dense_vector",
            data=query,  # query vectors
            limit=1,  # number of returned entities
            output_fields=["description", "timestamp"],  # specifies fields to be returned
            search_params={"metric_type": "COSINE"}
        )
        return res

@app.route('/api/insert/experience', methods=['POST'])
def insert_object():
    global db
    try:
        print("Received request data:")
        print(request.json)
        data = request.json['data']
        print("data: ")
        print(data)
        docs = [d['description'] for d in data]
        print("docs: ")
        print(docs)
        vectors = db.embedding_fn.encode_documents(docs)
        for i in range(len(data)):
            data[i]['dense_vector'] = vectors[i]
        res = db.insert(data)
        return jsonify({"status": "success", "data": "insert successfully", "num_objects": len(res['ids'])}), 200
    except Exception as e:
        print(f"Error processing insert request: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/api/search/experience', methods=['POST'])
def search_object():
    global db
    try:
        data = request.json['data']
        # 确保传递给 encode_documents 的是字符串列表
        if isinstance(data, str):
            query_texts = [data]
        elif isinstance(data, list):
            query_texts = data
        else:
            query_texts = [str(data)]
        print("query_texts")
        print(query_texts)
        query_vectors = db.embedding_fn.encode_documents(query_texts)
        result = db.search_object(query_vectors)
        print(result)
        if result and len(result) > 0 and len(result[0]) > 0:
            return jsonify({"status": "success", "data": result[0][0]['entity']}), 200
        else:
            return jsonify({"status": "success", "data": None}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    db = MemoryDataBase()
    host='127.0.0.1'
    port=5002
    app.run(host=host, port=port, debug=False)

