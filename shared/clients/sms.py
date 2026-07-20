from urllib.parse import quote
import requests

def send_otp_sms(mobile, otp):
    try:
        message = (
            f"Use OTP {otp} to login to GENZPLAYZONE. OTP is valid for 10 minutes. Do not share this OTP with anyone. -GENZPLAYZONE"
        )
        url = (
            "https://full2ads.com/smsapi/index"
            f"?key=26911C63F0A654"
            f"&campaign=0"
            f"&routeid=1"
            f"&type=text"
            f"&contacts={mobile}"
            f"&senderid=GENZPL"
            f"&tlv=%7B%22DLT_ENTITY_ID%22%3A%221001548232379518414%22%2C%22DLT_TEMPLATE_ID%22%3A%221107178090064521662%22%7D"
            f"&msg={quote(message)}"
        )
        response = requests.get(
            url,
            timeout=10
        )
        print("SMS Response:", response.text)
        return True
    except Exception as e:
        print("SMS Error:", str(e))
        return False

def send_sms_to_mobile(var1, mobile, msg):
    try:
        url = "https://sms.lifeboattechnologies.com/dev/bulkV2"
        payload = {
            "variables_values": var1,
            "route": "dlt",
            "message": msg,
            "numbers": mobile,
            "sender_id": "GENZPL"
        }
        headers = {
            "accept": "application/json",
            "Authorization": "CfnZkoK6sueIEU9GwL3BbiXgD8xluNQ0HlRTPrbzpSmVJ152O7tyWbQfSXVBO94Nra0DhHx6YkosTEzu",
            "content-type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)

        print(response.text)

        # url2 = "https://sms.lifeboattechnologies.com/dev/bulkV2?sender_id=GENZPL&message=12663&variables_values=Ranjith%7CGPZ10000100%7CBasket%20Ball%20Court%7C23%20Jul%202026%2C%208PM-9PM&route=dlt&numbers=9014083090"
        # url = "https://sms.lifeboattechnologies.com/dev/bulkV2"
        # params = {
        #     "authorization": "CfnZkoK6sueIEU9GwL3BbiXgD8xluNQ0HlRTPrbzpSmVJ152O7tyWbQfSXVBO94Nra0DhHx6YkosTEzu",
        #     "route": "dlt",
        #     "sender_id": "GENZPL",
        #     "message": msg,
        #     "variables_values": var1,
        #     "flash": "0",
        #     "numbers": str(mobile)
        # }
        # response = requests.get(
        #     url,
        #     params=params,
        #     timeout=10
        # )
        print(response.json())
        if response.status_code == 200:
            return True
        return False
    except Exception as e:
        print(e)
        return False
