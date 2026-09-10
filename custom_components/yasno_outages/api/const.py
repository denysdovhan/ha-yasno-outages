"""API constants for Yasno outages."""

from typing import Final

# Event names
EVENT_NAME_OUTAGE: Final = "Definite"
EVENT_NAME_NOT_PLANNED: Final = "NotPlanned"

# API Endpoints
REGIONS_ENDPOINT: Final = (
    "https://app.yasno.ua/api/blackout-service/public/shutdowns/addresses/v2/regions"
)
PLANNED_OUTAGES_ENDPOINT: Final = "https://app.yasno.ua/api/blackout-service/public/shutdowns/regions/{region_id}/dsos/{dso_id}/planned-outages"
PROBABLE_OUTAGES_ENDPOINT: Final = (
    "https://app.yasno.ua/api/blackout-service/public/shutdowns/probable-outages"
)
STREETS_ENDPOINT: Final = (
    "https://app.yasno.ua/api/blackout-service/public/shutdowns/addresses/v2/streets"
)
HOUSES_ENDPOINT: Final = (
    "https://app.yasno.ua/api/blackout-service/public/shutdowns/addresses/v2/houses"
)
GROUP_BY_ADDRESS_ENDPOINT: Final = (
    "https://app.yasno.ua/api/blackout-service/public/shutdowns/addresses/v2/group"
)

# API params
API_PARAM_REGION_ID: Final = "regionId"
API_PARAM_DSO_ID: Final = "dsoId"
API_PARAM_QUERY: Final = "query"
API_PARAM_STREET_ID: Final = "streetId"
API_PARAM_HOUSE_ID: Final = "houseId"
API_HTTP_STATUS_NOT_FOUND: Final = 404

# API Status values
API_STATUS_NO_OUTAGES: Final = "NoOutages"
API_STATUS_SCHEDULE_APPLIES: Final = "ScheduleApplies"
API_STATUS_WAITING_FOR_SCHEDULE: Final = "WaitingForSchedule"
API_STATUS_EMERGENCY_SHUTDOWNS: Final = "EmergencyShutdowns"
API_STATUS_NO_OUTAGES: Final = "NoOutages"

# API Block names
API_KEY_TODAY: Final = "today"
API_KEY_TOMORROW: Final = "tomorrow"
API_KEY_STATUS: Final = "status"
API_KEY_DATE: Final = "date"
API_KEY_UPDATED_ON: Final = "updatedOn"

# Authenticated login (Azure AD B2C, phone number + SMS/Viber OTP).
# Reverse-engineered from the official YASNO mobile app's
# res/raw/auth_config.json (MSAL) and its login WebView traffic.
AUTH_CLIENT_ID: Final = "0ce1809d-fd6a-40e5-9341-4222d06c00a3"
AUTH_TENANT_ID: Final = "0a7343d9-a7fb-4915-a143-b4b671f48aa5"
AUTH_POLICY: Final = "B2C_1A_SIGNUP_SIGNIN"
AUTH_AUTHORITY: Final = f"https://login.yasno.ua/{AUTH_TENANT_ID}/{AUTH_POLICY}"
AUTH_REDIRECT_URI: Final = (
    "msauth://com.dsolutions.yasnomobile/xb2DQCaO6b6UjOKP726qSV%2F7YLw%3D"
)
AUTH_SCOPE: Final = (
    "openid offline_access "
    "https://yasnomobileprod.onmicrosoft.com/BackendAPI/user_access"
)
AUTH_VERIFICATION_CONTROL_ID: Final = "PhoneOtpConditionalVerificationControl"
AUTH_MESSAGE_TYPE_SMS: Final = "sms"
AUTH_MESSAGE_TYPE_VIBER: Final = "viber"
AUTH_USER_AGENT: Final = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_4 like Mac OS X) AppleWebKit/605.1.15"
    " (KHTML, like Gecko) PKeyAuth/1.0"
)
# Yasno's B2C login endpoint (login.yasno.ua) sits behind an Imperva WAF with
# TLS/JA3 fingerprint-based bot detection: a plain aiohttp client is blocked
# with a generic 400 "Bad Request" regardless of headers/IP, while a request
# using a real browser's TLS fingerprint succeeds. `curl_cffi` is used for the
# login flow specifically to impersonate this fingerprint (see skill notes).
AUTH_IMPERSONATE: Final = "safari184_ios"

# Authenticated (logged-in customer account) endpoints.
ACCOUNTS_ENDPOINT: Final = "https://app.yasno.ua/api/account-service/users/me/accounts"
CONTRACTS_ENDPOINT: Final = (
    "https://app.yasno.ua/api/account-service/users/me/contracts"
)
DEBT_ENDPOINT: Final = "https://app.yasno.ua/api/account-service/users/me/b2c/debt"
TARIFF_ENDPOINT: Final = (
    "https://app.yasno.ua/api/account-service/users/me/accounts/v3/b2c/"
    "{account_id}/tariff"
)
AUTH_ADDRESSES_ENDPOINT: Final = (
    "https://app.yasno.ua/api/blackout-service/shutdowns/addresses"
)
AUTH_CURRENT_SLOTS_ENDPOINT: Final = (
    "https://app.yasno.ua/api/blackout-service/shutdowns/addresses/current-slots"
)

# Tariff zone names, as returned by the tariff endpoint.
TARIFF_ZONE_DAY: Final = "Day"
TARIFF_ZONE_NIGHT: Final = "Night"

STATISTICS_LAST_MONTH_ENDPOINT: Final = (
    "https://app.yasno.ua/api/account-service/statistics/last-month"
)
RECOMMENDED_AMOUNT_ENDPOINT: Final = (
    "https://app.yasno.ua/api/account-service/users/me/accounts/b2c/"
    "{account_id}/recommended-amount"
)
PAYMENT_HISTORY_ENDPOINT: Final = (
    "https://app.yasno.ua/api/payment-service/v2/payment/history"
)
