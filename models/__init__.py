import os

__all__ = ['connectionString']
BUCKET_NAME = "sapie-files"

currentEnv = os.getenv('FLASK_ENV')
if (currentEnv=='production'):
    connectionString = "mongodb://dba:20240924@localhost:11084/"
else:
    connectionString = "mongodb://localhost:27017/"