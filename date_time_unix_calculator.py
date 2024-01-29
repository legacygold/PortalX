import datetime

# Unix time stamp
unix_timestamp = 1694917020

# Convert to datetime in UTC
utc_datetime = datetime.datetime.utcfromtimestamp(unix_timestamp)

# Adjust for EDT (UTC-4 during DST)
edt_datetime = utc_datetime - datetime.timedelta(hours=4)

# Print the result
print("EDT Date and Time:", edt_datetime)
