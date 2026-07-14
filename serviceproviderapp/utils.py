# from django.conf import settings
# import requests

#     # @action(detail=True, methods=['post'], url_path='submit-document')
#     # Kycaid verification function (reusable, called in view).
# def verify_document_with_kycaid(image_url, document_type='PASSPORT'):
#         """Async-friendly Kycaid integration: Verify uploaded image URL.
#         Why: Offload to Celery in prod; here synchronous for simplicity. Returns verification_id/status.
#         Scalable: Rate-limit API calls if high volume."""
#         if not image_url.startswith('http'):  # Assume local/media; download for Kycaid.
#             # In prod: Use temp file from S3/media URL.
#             import urllib.request
#             local_file = '/tmp/temp_doc.jpg'
#             urllib.request.urlretrieve(image_url, local_file)
#         else:
#             local_file = image_url  # Remote URL handling.
    
#         api_key = settings.KYCAID_API_KEY
#         base_url = "https://api.kycaid.com"
#         headers = {"Authorization": f"Token {api_key}", "Content-Type": "application/json"}
    
#         try:
#             # Step 1: Create applicant.
#             applicant_payload = {"type": "PERSON", "residence_country": "BD"}  # Default; customize per provider_country.
#             resp = requests.post(f"{base_url}/applicants", headers=headers, json=applicant_payload)
#             applicant_id = resp.json()["applicant_id"]
    
#             # Step 2: Upload file (adapt for URL; here assume local for demo).
#             upload_headers = {"Authorization": f"Token {api_key}"}
#             with open(local_file, "rb") as f:  # Or stream from URL.
#                 files = {"file": (local_file.split('/')[-1], f, "image/jpeg")}
#                 upload_resp = requests.post(f"{base_url}/files", headers=upload_headers, files=files)
#             file_id = upload_resp.json()["file_id"]
    
#             # Step 3: Create document.
#             doc_payload = {"applicant_id": applicant_id, "type": document_type, "front_side_id": file_id}
#             doc_resp = requests.post(f"{base_url}/documents", headers=headers, json=doc_payload)
#             document_id = doc_resp.json()["document_id"]
    
#             # Step 4-5: Verification and poll (simplified; full poll in prod).
#             verif_payload = {"applicant_id": applicant_id, "types": ["document"], "form_id": settings.KYCAID_FORM_ID}
#             verif_resp = requests.post(f"{base_url}/verifications", headers=headers, json=verif_payload)
#             verification_id = verif_resp.json()["verification_id"]
#             # Poll loop (as in provided code; timeout 60s).
#             import time
#             for _ in range(6):  # 60s / 10s.
#                 time.sleep(10)
#                 poll_resp = requests.get(f"{base_url}/verifications/{verification_id}", headers=headers)
#                 poll_data = poll_resp.json()
#                 if poll_data["status"] == "completed":
#                     status = poll_data.get("verified", False) and "verified" or "failed"
#                     return verification_id, status  # Return for DB save.
#             return verification_id, "pending"
#         except Exception as e:
#             return None, f"error: {str(e)}"


import requests, time
from django.conf import settings

BASE_URL = "https://api.kycaid.com"

# Map our internal document_type values to KYCAID API document type identifiers.
# KYCAID supported types: PASSPORT, DOMESTIC_PASSPORT, DRIVERS_LICENSE,
# GOVERNMENT_ID, PERMANENT_RESIDENCE_PERMIT, FOREIGN_CITIZEN_PASSPORT, REFUGEE_CARD
DOCUMENT_TYPE_MAP = {
    "passport": "PASSPORT",
    "national_id": "GOVERNMENT_ID",     # KYCAID calls national IDs "GOVERNMENT_ID"
    "driving_licence": "DRIVERS_LICENSE", # KYCAID spells it LICENSE not LICENCE
}

COUNTRY_ISO_MAP = {
    # Asia
    "Bangladesh": "BD",
    "India": "IN",
    "Pakistan": "PK",
    "Sri Lanka": "LK",
    "Nepal": "NP",
    "China": "CN",
    "Japan": "JP",
    "South Korea": "KR",
    "Singapore": "SG",
    "Malaysia": "MY",
    "Indonesia": "ID",
    "Thailand": "TH",
    "Philippines": "PH",
    "Vietnam": "VN",
    # Middle East
    "United Arab Emirates": "AE",
    "Saudi Arabia": "SA",
    "Qatar": "QA",
    "Kuwait": "KW",
    "Bahrain": "BH",
    "Oman": "OM",
    "Jordan": "JO",
    "Lebanon": "LB",
    "Egypt": "EG",
    "Turkey": "TR",
    # Africa
    "Nigeria": "NG",
    "Ghana": "GH",
    "Kenya": "KE",
    "South Africa": "ZA",
    "Ethiopia": "ET",
    "Tanzania": "TZ",
    "Uganda": "UG",
    # Americas
    "United States": "US",
    "Canada": "CA",
    "Brazil": "BR",
    "Mexico": "MX",
    "Argentina": "AR",
    "Colombia": "CO",
    "Chile": "CL",
    "Peru": "PE",
    # Europe
    "United Kingdom": "GB",
    "Germany": "DE",
    "France": "FR",
    "Italy": "IT",
    "Spain": "ES",
    "Netherlands": "NL",
    "Sweden": "SE",
    "Norway": "NO",
    "Denmark": "DK",
    "Finland": "FI",
    "Poland": "PL",
    "Portugal": "PT",
    "Belgium": "BE",
    "Switzerland": "CH",
    "Austria": "AT",
    "Greece": "GR",
    "Russia": "RU",
    "Ukraine": "UA",
    # Oceania
    "Australia": "AU",
    "New Zealand": "NZ",
}

def verify_document_with_kycaid(*, document_file, document_type, country_code):
    """
    Submit a document to the KYCAID API for verification.

    document_type must be one of our internal types: passport, national_id, driving_licence.
    These are mapped to the correct KYCAID API identifiers via DOCUMENT_TYPE_MAP.
    country_code must be a valid ISO 3166-1 alpha-2 code (e.g. 'AE', 'US').
    Returns a dict with 'verification_id' on success, raises on API failure.
    """
    # Map internal document_type to KYCAID API type
    kycaid_doc_type = DOCUMENT_TYPE_MAP.get(document_type)
    if not kycaid_doc_type:
        # Fallback: upper-case the raw value and hope for the best,
        # but log a warning so this is visible in logs.
        import logging
        logging.getLogger(__name__).warning(
            f"Unknown document_type '{document_type}' — sending uppercased to KYCAID."
        )
        kycaid_doc_type = document_type.upper()

    # Fallback country code if missing from map
    if not country_code:
        import logging
        logging.getLogger(__name__).warning(
            "country_code is None — defaulting to 'US' for KYCAID."
        )
        country_code = "US"

    headers = {
        "Authorization": f"Token {settings.KYCAID_API_KEY}",
        "Content-Type": "application/json"
    }

    # 1️⃣ Create applicant
    applicant_payload = {
        "type": "PERSON",
        "residence_country": country_code
    }
    print("KYCAID applicant payload:", applicant_payload)
    resp = requests.post(f"{BASE_URL}/applicants", json=applicant_payload, headers=headers)
    resp.raise_for_status()
    applicant_id = resp.json()["applicant_id"]

    # 2️⃣ Upload file
    upload_headers = {"Authorization": f"Token {settings.KYCAID_API_KEY}"}
    files = {"file": (document_file.name, document_file, document_file.content_type)}
    upload_resp = requests.post(f"{BASE_URL}/files", headers=upload_headers, files=files)
    upload_resp.raise_for_status()
    file_id = upload_resp.json()["file_id"]

    # 3️⃣ Create document — use the mapped KYCAID type, NOT the raw user-supplied value
    doc_payload = {
        "applicant_id": applicant_id,
        "type": kycaid_doc_type,
        "front_side_id": file_id
    }
    requests.post(f"{BASE_URL}/documents", json=doc_payload, headers=headers).raise_for_status()

    # 4️⃣ Create verification
    verif_payload = {
        "applicant_id": applicant_id,
        "types": ["document"],
        "form_id": settings.KYCAID_FORM_ID
    }
    verif_resp = requests.post(f"{BASE_URL}/verifications", json=verif_payload, headers=headers)
    verif_resp.raise_for_status()
    verification_id = verif_resp.json()["verification_id"]

    # 5️⃣ Poll
    '''
    for _ in range(30):
        time.sleep(10)
        poll = requests.get(f"{BASE_URL}/verifications/{verification_id}", headers=headers)
        poll.raise_for_status()
        data = poll.json()
        if data["status"] == "completed":
            return {
                "verification_id": verification_id,
                "verified": data.get("verified", False),
                "raw": data
            }
    '''


    return {"verification_id": verification_id, "verified": False}
