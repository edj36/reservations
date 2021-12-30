import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pandas as pd
from pytz import timezone


FROM_ADDRESS = os.environ.get("FROM_ADDRESS")
FROM_ADDRESS_PASSWORD = os.environ.get("FROM_ADDRESS_PASSWORD")
TO_ADDRESSES = "edj36@cornell.edu"
EST_TIMEZONE = timezone('EST')

today_datetime = datetime.now(EST_TIMEZONE)

# load and format output from latest reservations
reservations_df = pd.read_csv('data/reservations_latest.csv')

reservations_df['dinner'] = (
    (pd.to_datetime(reservations_df['res_time']).dt.hour >= 18)&
    (pd.to_datetime(reservations_df['res_time']).dt.hour <= 20)
)

reservations_df['day_of_week'] = pd.to_datetime(reservations_df['res_time']).dt.day_name()

df_as_html = (
    reservations_df[reservations_df['dinner']==True]
    .groupby(by=['name', 'date'], as_index=False)
    .agg({'dinner':'count', 'day_of_week':'first', 'url':'first'})
).to_html(index=False)

# create message container - the correct MIME type is multipart/alternative.
msg = MIMEMultipart('alternative')
msg['Subject'] = f"Reservations checked on: {today_datetime.strftime('%Y-%m-%d')}"
msg['From'] = FROM_ADDRESS
msg['To'] = TO_ADDRESSES

# create the HTML and message
html = """
<html>
<head></head>
<body>
Count of dinner reservations (between 6-9 PM) available by restaurant and day:
<br>
<br>
{0}
</body>
</html>
""".format(df_as_html)
part = MIMEText(html, 'html')
msg.attach(part)

# send the email
server = smtplib.SMTP('smtp.gmail.com', 587)
server.ehlo()
server.starttls()
server.login(FROM_ADDRESS, FROM_ADDRESS_PASSWORD)
server.sendmail(FROM_ADDRESS, TO_ADDRESSES, msg.as_string())
server.quit()
