import os
from resend import Email
from dotenv import load_dotenv
load_dotenv()
# Set your API key
import os
import resend

resend.api_key = os.environ["RESEND_API_KEY"]

params = {
    "from": "",
    "to": ["aliyanehtesham28@gmail.com"],
    "subject": "Hello world",
    "html": "<strong>It works!</strong>"
}

email = resend.Emails.send(params)
print(email)