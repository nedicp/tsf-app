from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from backend.config import Config
import logging

class Database:
    _instance = None
    _client = None
    _db = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None:
            self.connect()

    def connect(self):
        """Connect to MongoDB"""
        try:
            if not Config.DATABASE_CONNECTION_STRING:
                raise ValueError("DATABASE_CONNECTION_STRING not found in environment variables")

            self._client = MongoClient(
                Config.DATABASE_CONNECTION_STRING,
                server_api=ServerApi('1')
            )

            self._client.admin.command('ping')
            print("Successfully connected to MongoDB!")

            self._db = self._client[Config.DATABASE_NAME]

            self._create_indexes()

        except Exception as e:
            print(f"Failed to connect to MongoDB: {e}")
            raise

    def _create_indexes(self):
        """Create necessary indexes for better performance"""
        try:
            users_collection = self._db.users

            users_collection.create_index("username", unique=True)

            users_collection.create_index("email", unique=True)

            print("Database indexes created successfully")

        except Exception as e:
            print(f"Warning: Could not create indexes: {e}")

    def get_database(self):
        """Get the database instance"""
        if self._db is None:
            self.connect()
        return self._db

    def get_collection(self, collection_name):
        """Get a specific collection"""
        db = self.get_database()
        return db[collection_name]

    def close_connection(self):
        """Close the database connection"""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            print("Database connection closed")

db = Database()
