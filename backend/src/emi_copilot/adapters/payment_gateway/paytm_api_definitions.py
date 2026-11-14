"""Every Paytm URL, path, field name, enum value and result code the Paytm adapter uses.

Each item was read on paytmpayments.com/docs on 2026-11-14 through a content extraction of
JS-heavy pages, not against a live account, so every item is [Verify] (ADR 0002). Other modules
import these names; none of them spells a Paytm detail itself.
"""

from types import MappingProxyType

from emi_copilot.domain.errors import PaymentGatewayRejectionReason
from emi_copilot.domain.payments import GatewayPaymentStatus

ADAPTER_NAME = "paytm"  # our adapter name (ADR 0004); not a Paytm detail

# --- Base URLs and paths -------------------------------------------------------------------
# Only staging hosts are on the docs pages; production has no default (ADR 0002).
# The status API is on a different host, under paytmpayments.in.
STAGING_EMI_SUBVENTION_BASE_URL = "https://securestage.paytmpayments.com"  # [Verify] banks-api
STAGING_PAYMENT_LINK_BASE_URL = "https://securestage.paytmpayments.com"  # [Verify] create-link-api
STAGING_TRANSACTION_STATUS_BASE_URL = (  # [Verify] docs/api/v3/transaction-status-api
    "https://securegw-stage.paytmpayments.in"  # [Verify] same page
)
BANKS_PATH = "/theia/api/v1/emiSubvention/banks"  # [Verify] docs/banks-api
TENURES_PATH = "/theia/api/v1/emiSubvention/tenures"  # [Verify] docs/tenures-api
CREATE_LINK_PATH = "/link/create"  # [Verify] docs/create-link-api
TRANSACTION_STATUS_PATH = "/v3/order/status"  # [Verify] docs/api/v3/transaction-status-api
MERCHANT_ID_QUERY_PARAMETER = "mid"  # [Verify] docs/banks-api, docs/tenures-api: ?mid={mid}

# --- Envelope shared by the JSON APIs ------------------------------------------------------
HEAD_FIELD = "head"  # [Verify] all four JSON API pages: {"head": {...}, "body": {...}}
BODY_FIELD = "body"  # [Verify] all four JSON API pages
MERCHANT_ID_FIELD = "mid"  # [Verify] banks, tenures, create-link and v3 status request bodies
# Replies are read as the same envelope; every reply field below is read inside its body.
# [Verify] all four JSON API pages: the "response body" tables are read as reply["body"].

# --- Banks and Tenures request head (EMI Subvention) ----------------------------------------
HEAD_REQUEST_ID_FIELD = "requestId"  # [Verify] docs/banks-api: string(32), unique
REQUEST_ID_MAXIMUM_LENGTH = 32  # [Verify] docs/banks-api: requestId is string(32)
HEAD_REQUEST_TIMESTAMP_FIELD = "requestTimestamp"  # [Verify] docs/banks-api: epoch seconds text
HEAD_VERSION_FIELD = "version"  # [Verify] docs/banks-api
HEAD_VERSION_VALUE = "v1"  # [Verify] docs/banks-api: e.g. "v1"
HEAD_TOKEN_TYPE_FIELD = "tokenType"  # noqa: S105 - name. [Verify] banks-api, create-link-api
SUBVENTION_TOKEN_TYPE_VALUE = "CHECKSUM"  # noqa: S105 - a type word. [Verify] docs/banks-api
HEAD_TOKEN_FIELD = "token"  # noqa: S105 - name. [Verify] docs/banks-api: checksum of the body

# --- Banks and Tenures request body ---------------------------------------------------------
ITEMS_FIELD = "items"  # [Verify] docs/banks-api, docs/create-link-api (simplifiedSubvention)
ITEM_ID_FIELD = "id"  # [Verify] docs/banks-api: items[].id
ITEM_PRODUCT_ID_FIELD = "productId"  # [Verify] docs/banks-api: items[].productId
ITEM_BRAND_ID_FIELD = "brandId"  # [Verify] docs/banks-api: items[].brandId
ITEM_CATEGORY_LIST_FIELD = "categoryList"  # [Verify] docs/banks-api: an array in the samples
ITEM_PRICE_FIELD = "price"  # [Verify] docs/banks-api: rupees, price x quantity
ITEM_QUANTITY_FIELD = "quantity"  # [Verify] docs/banks-api: items[].quantity
FILTERS_FIELD = "filters"  # [Verify] docs/tenures-api
FILTER_BANK_CODE_FIELD = "bankCode"  # [Verify] docs/tenures-api: filters.bankCode, mandatory
FILTER_CARD_TYPE_FIELD = "cardType"  # [Verify] docs/tenures-api: filters.cardType, mandatory

# --- Result info, shared by every JSON response ---------------------------------------------
RESULT_INFO_FIELD = "resultInfo"  # [Verify] all four JSON API pages
RESULT_STATUS_FIELD = "resultStatus"  # [Verify] all four JSON API pages
RESULT_CODE_FIELD = "resultCode"  # [Verify] all four JSON API pages
SUBVENTION_SUCCESS_RESULT_STATUS = "S"  # [Verify] docs/banks-api, docs/tenures-api: "S" or "F"
SUBVENTION_FAILURE_RESULT_STATUS = "F"  # [Verify] docs/banks-api, docs/tenures-api

# --- Banks response -------------------------------------------------------------------------
# [Verify] docs/banks-api: the nesting of cardTypes and bankDetails inside emiTypes is not
# confirmed. We read the most literal form: each emiTypes entry holds a cardTypes array and one
# bankDetails object.
EMI_TYPES_FIELD = "emiTypes"  # [Verify] docs/banks-api
CARD_TYPES_FIELD = "cardTypes"  # [Verify] docs/banks-api: emiTypes[].cardTypes[]
CARD_TYPE_FIELD = "cardType"  # [Verify] docs/banks-api: cardTypes[].cardType, docs/tenures-api
BANK_DETAILS_FIELD = "bankDetails"  # [Verify] docs/banks-api: emiTypes[].bankDetails
BANK_CODE_FIELD = "bankCode"  # [Verify] docs/banks-api: bankDetails.bankCode
CREDIT_CARD_TYPE = "CREDIT_CARD"  # [Verify] docs/banks-api, docs/tenures-api
DEBIT_CARD_TYPE = "DEBIT_CARD"  # [Verify] docs/banks-api, docs/tenures-api
KNOWN_CARD_TYPES = frozenset({CREDIT_CARD_TYPE, DEBIT_CARD_TYPE})  # [Verify] the two above

# --- Tenures response -----------------------------------------------------------------------
BANK_NAME_FIELD = "bankName"  # [Verify] docs/tenures-api: top-level bankName, the lender label
PLAN_DETAILS_FIELD = "planDetails"  # [Verify] docs/tenures-api
PLAN_ID_FIELD = "planId"  # [Verify] docs/tenures-api: our offer id; uniqueness not confirmed
PLAN_EMI_TYPE_FIELD = "emiType"  # [Verify] docs/tenures-api
SUBVENTION_PLAN_TYPE = "SUBVENTION"  # [Verify] docs/tenures-api: emiType "SUBVENTION"
STANDARD_PLAN_TYPE = "STANDARD"  # [Verify] docs/tenures-api: emiType "STANDARD"
KNOWN_PLAN_TYPES = frozenset({SUBVENTION_PLAN_TYPE, STANDARD_PLAN_TYPE})  # [Verify] the two above
PLAN_INTERVAL_FIELD = "interval"  # [Verify] docs/tenures-api: int months
PLAN_EMI_FIELD = "emi"  # [Verify] docs/tenures-api: rupees per month
PLAN_INTEREST_FIELD = "interest"  # [Verify] docs/tenures-api: rupees of total interest
# Subvention plans only; read literally as one {value, type, label} object.
PLAN_GRATIFICATIONS_FIELD = "gratifications"  # [Verify] docs/tenures-api
GRATIFICATION_VALUE_FIELD = "value"  # [Verify] docs/tenures-api: rupees
GRATIFICATION_TYPE_FIELD = "type"  # [Verify] docs/tenures-api: DISCOUNT or CASHBACK
KNOWN_GRATIFICATION_TYPES = frozenset({"DISCOUNT", "CASHBACK"})  # [Verify] docs/tenures-api
# Extra in total (ADR 0010 section 2, owner decision) [Verify] docs/tenures-api: whether a
# SUBVENTION plan's interest is the gross bank interest that its gratification offsets is not
# confirmed. Rule: net extra = interest - gratification value, for DISCOUNT and CASHBACK alike,
# never below zero; NO_COST exactly when the net extra is zero, else STANDARD. A STANDARD plan's
# gratifications are not read. The monthly installment is always the plan's own emi.

# --- Create Link ----------------------------------------------------------------------------
LINK_TOKEN_TYPE_VALUE = "AES"  # noqa: S105 - a type word. [Verify] docs/create-link-api
HEAD_SIGNATURE_FIELD = "signature"  # [Verify] docs/create-link-api, docs/api/v3/...-status-api
LINK_NAME_FIELD = "linkName"  # [Verify] docs/create-link-api: mandatory
LINK_NAME_MAXIMUM_LENGTH = 64  # [Verify] docs/create-link-api: linkName at most 64
LINK_DESCRIPTION_FIELD = "linkDescription"  # [Verify] docs/create-link-api: mandatory
LINK_DESCRIPTION_MAXIMUM_LENGTH = 30  # [Verify] docs/create-link-api: at most 30
LINK_TYPE_FIELD = "linkType"  # [Verify] docs/create-link-api: mandatory
FIXED_LINK_TYPE = "FIXED"  # [Verify] docs/create-link-api: a FIXED link needs an amount
LINK_AMOUNT_FIELD = "amount"  # [Verify] docs/create-link-api: double, rupees
LINK_ORDER_ID_FIELD = "linkOrderId"  # [Verify] docs/create-link-api: our order id (ADR 0002)
LINK_ORDER_ID_MAXIMUM_LENGTH = 50  # [Verify] docs/create-link-api: linkOrderId at most 50
STATUS_CALLBACK_URL_FIELD = "statusCallbackUrl"  # [Verify] docs/create-link-api: our webhook
# Item-based subvention block, from docs/affordability-emi-subvention-payment-links.
SIMPLIFIED_SUBVENTION_FIELD = "simplifiedSubvention"  # [Verify] that page
CUSTOMER_ID_FIELD = "customerId"  # [Verify] same page: simplifiedSubvention.customerId
SELECT_PLAN_ON_CASHIER_PAGE_FIELD = "selectPlanOnCashierPage"  # [Verify] same page: true
# Deliberately never sent (ADR 0010 section 1): partialPayment, bindLinkIdMobile and any
# customer contact, SMS or email field. [Verify] docs/create-link-api minimal sample omits them.
# resultMessage (Create Link) and resultMsg (the others) are never read or logged.
LINK_SUCCESS_RESULT_STATUS = "SUCCESS"  # [Verify] docs/create-link-api
LINK_FAILURE_RESULT_STATUS = "FAILED"  # [Verify] docs/create-link-api
LINK_ID_FIELD = "linkId"  # [Verify] docs/create-link-api response
SHORT_URL_FIELD = "shortUrl"  # [Verify] docs/create-link-api: shared with the customer
# longUrl is in the response too and is never read or shared. [Verify] docs/create-link-api

# Create Link failure codes that mean Paytm refused the request (ADR 0010 section 3 applies to
# the rest). [Verify] docs/create-link-api result code table.
LINK_REJECTION_REASONS_BY_RESULT_CODE = MappingProxyType(
    {
        "100": PaymentGatewayRejectionReason.OPERATION_NOT_PERMITTED,  # [Verify] failed (risk)
        "404": PaymentGatewayRejectionReason.INVALID_REQUEST,  # [Verify] data not found
        "5004": PaymentGatewayRejectionReason.INVALID_REQUEST,  # [Verify] empty merchant id
        "5008": PaymentGatewayRejectionReason.INVALID_REQUEST,  # [Verify] fixed link needs amount
        "5009": PaymentGatewayRejectionReason.INVALID_REQUEST,  # [Verify] amount below Rs 1
        "5021": PaymentGatewayRejectionReason.INVALID_REQUEST,  # [Verify] invalid expiry
        "5027": PaymentGatewayRejectionReason.INVALID_REQUEST,  # [Verify] expiry over 365 days
        "5028": PaymentGatewayRejectionReason.INVALID_REQUEST,  # [Verify] invalid checksum
        "5023": PaymentGatewayRejectionReason.OPERATION_NOT_PERMITTED,  # [Verify] invalid mid
        "5025": PaymentGatewayRejectionReason.OPERATION_NOT_PERMITTED,  # [Verify] not linked
    }
)
# Paytm's own internal (501) and unknown (502) errors: whether a link was made is unknown, so
# they are treated like a 5xx answer (ADR 0010 section 3).
LINK_OUTCOME_UNKNOWN_RESULT_CODES = frozenset({"501", "502"})  # [Verify] docs/create-link-api

# --- Transaction Status API v3 --------------------------------------------------------------
STATUS_ORDER_ID_FIELD = "orderId"  # [Verify] docs/api/v3/transaction-status-api: request, reply
STATUS_TRANSACTION_ID_FIELD = "txnId"  # [Verify] docs/api/v3/transaction-status-api
STATUS_TRANSACTION_AMOUNT_FIELD = "txnAmount"  # [Verify] same page: rupees, text or number
# [Verify] docs/api/v3/transaction-status-api: resultStatus values and how we read them.
TRANSACTION_STATUSES_BY_RESULT_STATUS = MappingProxyType(
    {
        "TXN_SUCCESS": GatewayPaymentStatus.PAID,  # [Verify] code 01
        "TXN_FAILURE": GatewayPaymentStatus.FAILED,  # [Verify] codes below
        "PENDING": GatewayPaymentStatus.PENDING,  # [Verify] codes 400, 402
        "NO_RECORD_FOUND": GatewayPaymentStatus.NOT_FOUND,  # [Verify] code 331
    }
)
# [Verify] docs/api/v3/transaction-status-api: the documented codes for each resultStatus. An
# undocumented code is still mapped by its status and logged by code, for review.
DOCUMENTED_RESULT_CODES_BY_RESULT_STATUS = MappingProxyType(
    {
        "TXN_SUCCESS": frozenset({"01"}),  # [Verify] same page
        "TXN_FAILURE": frozenset(  # [Verify] same page: 227/401 bank declined, 334 order, 335 mid
            {"227", "401", "235", "295", "334", "335"}  # [Verify] same page
            | {"501", "810", "820", "843", "267"}  # [Verify] same page
        ),
        "PENDING": frozenset({"400", "402"}),  # [Verify] same page
        "NO_RECORD_FOUND": frozenset({"331"}),  # [Verify] same page
    }
)
# Card-like reply fields (cardScheme, lastFourDigit, authCode, rrnCode) and every other field
# not named above are never read: the mapper whitelists. [Verify] same page

# --- Link Payment Status webhook ------------------------------------------------------------
# [Verify] docs/link-payment-status-webhook: key/value pairs; accepted as a form POST (ADR 0002).
WEBHOOK_CHECKSUM_FIELD = "CHECKSUMHASH"  # [Verify] same page, docs/checksum
WEBHOOK_MERCHANT_ID_FIELD = "MID"  # [Verify] same page
WEBHOOK_ORDER_ID_FIELD = "ORDERID"  # [Verify] same page: equals our linkOrderId
WEBHOOK_TRANSACTION_ID_FIELD = "TXNID"  # [Verify] same page
WEBHOOK_TRANSACTION_AMOUNT_FIELD = "TXNAMOUNT"  # [Verify] same page: rupees as text
WEBHOOK_STATUS_FIELD = "STATUS"  # [Verify] same page: the v3 status vocabulary
WEBHOOK_STATUSES_BY_STATUS_VALUE = MappingProxyType(
    {
        "TXN_SUCCESS": GatewayPaymentStatus.PAID,  # [Verify] same page
        "TXN_FAILURE": GatewayPaymentStatus.FAILED,  # [Verify] same page
        "PENDING": GatewayPaymentStatus.PENDING,  # [Verify] same page
    }
)
# Personal data: never read, logged, stored or returned (the tests check these two fields).
WEBHOOK_PERSONAL_DATA_FIELDS = frozenset({"PAYMENTEMAILID", "PAYMENTMOBILENUMBER"})  # [Verify]

# --- Checksum (docs/checksum, docs/checksum-implementation, paytmchecksum 1.7.0 source) ------
CHECKSUM_INITIALISATION_VECTOR = b"@@@@&&&&####$$$$"  # [Verify] paytmchecksum 1.7.0: fixed iv
CHECKSUM_SALT_LENGTH = 4  # [Verify] paytmchecksum 1.7.0: 4 random characters
CHECKSUM_SALT_ALPHABET = (  # [Verify] paytmchecksum 1.7.0: [A-Z0-9a-z]
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdefghijklmnopqrstuvwxyz"  # [Verify] same source
)
CHECKSUM_FIELD_SEPARATOR = "|"  # [Verify] paytmchecksum 1.7.0: values and salt joined by "|"
CHECKSUM_NULL_TEXT = "null"  # [Verify] paytmchecksum 1.7.0: "null" (any case) signs as ""
CHECKSUM_ACCEPTED_KEY_LENGTHS_IN_BYTES = frozenset({16, 24, 32})  # [Verify] AES; Paytm keys 16
