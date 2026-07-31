from uuid import uuid4

from django.conf import settings
import phonepe
from marshmallow.fields import Float, Decimal
from phonepe.sdk.pg.common.models.request.meta_info import MetaInfo
from phonepe.sdk.pg.common.models.request.refund_request import RefundRequest
from phonepe.sdk.pg.payments.v2.models.request.create_sdk_order_request import CreateSdkOrderRequest
from phonepe.sdk.pg.payments.v2.models.request.standard_checkout_pay_request import StandardCheckoutPayRequest
from phonepe.sdk.pg.payments.v2.standard_checkout_client import StandardCheckoutClient
from phonepe.sdk.pg.env import Env

client_secret = settings.PHONE_PE_CLIENT_SECRETE
client_id = settings.PHONE_PE_CLIENT_ID
client_version = settings.PHONE_PE_CLIENT_VERSION
should_publish_events = False

def get_phonepe_client():
    if settings.PHONE_PE_ENV.upper() == "PRODUCTION":
        phonepe_env = Env.PRODUCTION
    else:
        phonepe_env = Env.SANDBOX

    print("\n========== INITIALIZING PHONEPE CLIENT ==========")
    print("Client ID:", client_id)
    print("Client Version:", client_version)
    print("Environment from settings:", settings.PHONE_PE_ENV)
    print("SDK Environment:", phonepe_env)

    client = StandardCheckoutClient.get_instance(
        client_id=client_id,
        client_secret=client_secret,
        client_version=client_version,
        env=phonepe_env,
        should_publish_events=should_publish_events,
    )

    return client
def phone_pe_initate(order_id,total_amount):
    print("\n========== PHONEPE CREATE SDK ORDER ==========")

    client = get_phonepe_client()

    unique_order_id = str(order_id)
    # amount = 100

    print("Merchant Order ID:", unique_order_id)
    print("Amount:", total_amount)

    meta_info = MetaInfo(
        udf1="onboarding"
    )

    print("Meta Info:", meta_info)

    sdk_order_request = CreateSdkOrderRequest.build_standard_checkout_request(
        merchant_order_id=unique_order_id,
        amount=total_amount,
        meta_info=meta_info,
        disable_payment_retry=True
    )

    print("\nSDK Order Request:")
    print(sdk_order_request)

    try:
        print("\nCalling PhonePe Create SDK Order API...")

        create_order_response = client.create_sdk_order(
            sdk_order_request=sdk_order_request
        )

        print("\n========== PHONEPE RESPONSE ==========")
        print(create_order_response)
        print("======================================\n")

        return create_order_response

    except Exception as error:
        print("\n========== PHONEPE EXCEPTION ==========")
        print("Exception Type:", type(error).__name__)
        print("Exception:", str(error))
        print("=======================================\n")
        raise


def check_order_status(m_order_id):
    client = get_phonepe_client()
    merchant_order_id = m_order_id
    response = client.get_order_status(merchant_order_id, details=False)
    return response

def refund_phonepe(m_order_id, amount):
    client = get_phonepe_client()
    unique_merchant_refund_id = str(uuid4())
    original_merchant_order_id = m_order_id
    amt = float(amount) * 100.00
    amt = int(amt)

    print(f"initiating phone pe refund {original_merchant_order_id}")
    refund_request = RefundRequest.build_refund_request(merchant_refund_id=unique_merchant_refund_id,
                                                        original_merchant_order_id=original_merchant_order_id,
                                                        amount=amt)
    refund_response = client.refund(refund_request=refund_request)
    print("refund api completed from phone pe")
    return refund_response
