import json
import re
from pathlib import Path

DATA_FOLDER = Path("data")
OUTPUT_FILE = DATA_FOLDER / "services.json"

# Text files and their service names
SERVICE_FILES = [
    ("income_certificate_output.txt", "Income Certificate"),
    ("residence_certificate.txt", "Residence Certificate"),
    ("caste_certificate.txt", "Caste Certificate"),
    ("birth_certificate.txt", "Birth Certificate")
]


def get_section(text, start, end):
    pattern = (
        re.escape(start)
        + r"\s*:?\s*(.*?)"
        + r"(?="
        + re.escape(end)
        + r"\s*:?\s*|$)"
    )

    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)

    return match.group(1).strip() if match else ""


def get_list(text):
    items = []

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        line = re.sub(r"^\d+[\.)]\s*", "", line)

        if line:
            items.append(line)

    return items


def extract_service(filename, service_name):

    file_path = DATA_FOLDER / filename

    if not file_path.exists():
        print("File not found:", filename)
        return None

    text = file_path.read_text(encoding="utf-8")

    if not text.strip():
        print("Empty file:", filename)
        return None

    service = {
        "service_name": service_name,
        "department": "",
        "portal": "Seva Sindhu",

        "service_description": get_section(
            text, "Service Description", "Eligibility"
        ),

        "eligibility": get_section(
            text, "Eligibility", "Supporting Document"
        ),

        "required_documents": get_list(
            get_section(text, "Supporting Document", "Application Fee")
        ),

        "application_fee": get_section(
            text, "Application Fee", "Service Charge"
        ),

        "service_charge": get_section(
            text, "Service Charge", "Delivery Time"
        ),

        "processing_time": get_section(
            text, "Delivery Time (Days)", "Procedure for applying"
        ),

        "application_procedure": get_list(
            get_section(text, "Procedure for applying", "User manual")
        ),

        "official_link": "",
        "source_url": "",
        # Only set this after a person checks the record against an official source.
        "last_verified": "",

        "raw_text": text
    }

    return service


def main():

    # Load existing services
    if OUTPUT_FILE.exists():
        try:
            services = json.loads(
                OUTPUT_FILE.read_text(encoding="utf-8")
            )
        except json.JSONDecodeError:
            print("Existing JSON is invalid.")
            return
    else:
        services = []

    successful = 0

    for filename, service_name in SERVICE_FILES:

        print("\nProcessing:", service_name)

        service = extract_service(filename, service_name)

        if service is None:
            continue

        # Update existing record or add a new one
        services = [
            item for item in services
            if item.get("service_name", "").lower()
            != service_name.lower()
        ]

        services.append(service)

        successful += 1

        print("Successfully converted:", service_name)

    OUTPUT_FILE.write_text(
        json.dumps(services, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )

    print("\n================================")
    print("CONVERSION COMPLETED")
    print("Services converted:", successful)
    print("Total services in JSON:", len(services))
    print("Saved to:", OUTPUT_FILE)
    print("================================")


if __name__ == "__main__":
    main()
