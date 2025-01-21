from datetime import datetime, timedelta

NOW = datetime.now()
FROM_DATE = NOW
TO_DATE = timedelta(days=45) + FROM_DATE
print(f"FROM_DATE: {FROM_DATE} \n"
      f"TO_DATE: {TO_DATE}")
