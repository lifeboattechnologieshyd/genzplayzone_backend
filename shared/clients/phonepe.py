from uuid import uuid4
from decimal import Decimal

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

    env_name = str(settings.PHONE_PE_ENV).upper()

    if env_name == "PRODUCTION":
        phonepe_env = Env.PRODUCTION
    else:
        phonepe_env = Env.SANDBOX
    print("PHONE_PE_ENV:", settings.PHONE_PE_ENV)
    print("PHONE_PE_ENV Type:", type(settings.PHONE_PE_ENV))


    print("SDK Environment:", phonepe_env)
    print("SDK Environment Type:", type(phonepe_env))

    print("\n========== INITIALIZING PHONEPE CLIENT ==========")
    print("Client ID:", client_id)
    print("Client Version:", client_version)
    print("Environment from settings:", settings.PHONE_PE_ENV)
    print("SDK Environment:", phonepe_env)

    return StandardCheckoutClient.get_instance(
        client_id=client_id,
        client_secret=client_secret,
        client_version=client_version,
        env=phonepe_env,
        should_publish_events=should_publish_events,
    )


def phone_pe_initate(order_id, total_amount):
    print("1. Entered phone_pe_initate")

    client = get_phonepe_client()

    print("2. Client initialized")

    unique_order_id = str(order_id)
    print("3. Merchant Order ID:", unique_order_id)

    amount_in_paise = int(total_amount * 100)
    print("4. Amount in paise:", amount_in_paise)

    meta_info = MetaInfo(udf1="onboarding")
    print("5. Meta info created")

    sdk_order_request = CreateSdkOrderRequest.build_standard_checkout_request(
        merchant_order_id=unique_order_id,
        amount=amount_in_paise,
        meta_info=meta_info,
        disable_payment_retry=True,
    )

    print("6. SDK request created")

    response = client.create_sdk_order(sdk_order_request)

    print("7. PhonePe response:", response)

    return response


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
