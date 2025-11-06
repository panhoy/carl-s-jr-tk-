from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from bson.json_util import ObjectId
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# --- MongoDB Setup ---
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://carlsjrtk:carlsjrtkcambodai12345@cluster0.6wemwdl.mongodb.net/?appName=Cluster0")

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
    client.server_info()  # test DB connection
    db = client.get_database("carlsjr_inventory")
    oil_collection = db.oil_entries
    soap_collection = db.soap_entries
    db_enabled = True
    print("✅ Connected to MongoDB")
except Exception:
    oil_collection = []
    soap_collection = []
    db_enabled = False
    print("⚠ MongoDB not running — using Memory Mode")

# Helper to select storage
def get_collection(product_type):
    if db_enabled:
        return oil_collection if product_type == "oil" else soap_collection
    else:
        return oil_collection if product_type == "oil" else soap_collection

def parse_json(data):
    if "_id" in data:
        data["_id"] = str(data["_id"])
    return data

@app.route('/api/inventory/<product_type>', methods=['GET'])
def get_entries(product_type):
    try:
        if db_enabled:
            entries = list(get_collection(product_type).find().sort([('date', -1)]))
            entries = [parse_json(e) for e in entries]
        else:
            entries = get_collection(product_type)

        return jsonify(entries)
    except:
        return jsonify({"error": "Failed to load data"}), 500

@app.route('/api/inventory/<product_type>', methods=['POST'])
def add_entry(product_type):
    data = request.json

    if not all(k in data for k in ['day', 'date']):
        return jsonify({"error": "Missing fields"}), 400

    new_entry = {
        "day": data['day'],
        "date": data['date'],
        "status": "New Use"
    }

    if db_enabled:
        collection = get_collection(product_type)
        collection.update_many({"status": "New Use"}, {"$set": {"status": "Old EXP"}})
        result = collection.insert_one(new_entry)
        new_entry["_id"] = str(result.inserted_id)
    else:
        new_entry["_id"] = str(len(get_collection(product_type)) + 1)
        get_collection(product_type).append(new_entry)

    return jsonify(new_entry), 201

@app.route('/api/inventory/<product_type>/<entry_id>', methods=['DELETE'])
def delete_entry(product_type, entry_id):
    if db_enabled:
        result = get_collection(product_type).delete_one({"_id": ObjectId(entry_id)})
        if result.deleted_count == 0:
            return jsonify({"error": "Not found"}), 404
    else:
        items = get_collection(product_type)
        updated = [i for i in items if str(i["_id"]) != entry_id]
        if len(updated) == len(items):
            return jsonify({"error": "Not found"}), 404
        if product_type == "oil":
            global oil_collection
            oil_collection = updated
        else:
            global soap_collection
            soap_collection = updated

    return jsonify({"message": "Deleted"}), 200

if __name__ == "__main__":
    print("\n🚀 Flask API running at: http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
