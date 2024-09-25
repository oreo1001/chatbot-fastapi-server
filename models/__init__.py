import os
from dotenv import load_dotenv

__all__ = ['connectionString']
BUCKET_NAME = "sapie-files"

load_dotenv()
currentEnv = os.getenv('FAST_ENV')
print(currentEnv)
if (currentEnv=='production'):
    connectionString = "mongodb://dba:20240925@localhost:11084/"
else:
    connectionString = "mongodb://localhost:27017/"