import os
from dotenv import load_dotenv

load_dotenv(override=True)

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
print(NEWS_API_KEY)
