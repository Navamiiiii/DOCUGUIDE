
import json
import re
from pathlib import Path

# Input and output file paths
INPUT_FILE = Path("data/income_certificate_output.txt")
OUTPUT_FILE = Path("data/services.json")


def extract_section(text, start, end=None):
    """
    Extracts text between two section headings.
    """
    pattern = re.escape(start) + r"\s*:?\s*(.*?)(?="

    if end:
        pattern += re.escape(end)
    else:
        pattern += r"$"

    pattern += r")"

    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)

    if match:
        return match.group(1).strip()

    return ""


def convert_to_json():

    if not INPUT_FILE.exists():
        print("ERROR: Input text file not found!")
        return

    # Read extracted text
    text = INPUT_FILE.read_text(encoding="utf-8")

    # Remove popup close symbol and unnecessary whitespace
    text = text.replace("×", "").strip()

    # Extract service information
    service = {
        "service_name": "Income Certificate",
        "department": "Revenue Department",
        "portal": "Seva Sindhu",

        "service_description": extract_section(
            text, "Service Description", "Eligibility"
        ),

        "eligibility": extract_section(
            text, "Eligibility", "Supporting Document"
        ),

        "required_documents": [],

        "application_fee": "",

        "service_charge": "",

        "processing_time": "",

        "application_procedure": [],

        "official_link": "",

        "source_url": "",

        "last_verified": ""
    }

    # Extract supporting documents
    documents = extract_section(
        text, "Supporting Document", "Application Fee"
    )

    service["required_documents"] = [
        re.sub(r"^\s*\d+[\.)]\s*", "", line).strip()
        for line in documents.splitlines()
        if line.strip()
    ]

    # Extract application fee
    fee = re.search(
        r"Application Fee\s*:\s*(.*)",
        text,
        re.IGNORECASE
    )

    if fee:
        service["application_fee"] = fee.group(1).strip()

    # Extract service charge
    charge = re.search(
        r"Service Charge.*?:\s*(.*)",
        text,
        re.IGNORECASE
    )

    if charge:
        service["service_charge"] = charge.group(1).strip()

    # Extract delivery time
    delivery = re.search(
        r"Delivery Time\s*\(Days\)\s*:\s*(.*)",
        text,
        re.IGNORECASE
    )

    if delivery:
        service["processing_time"] = delivery.group(1).strip() + " days"

    # Extract application procedure
    procedure = extract_section(
        text, "Procedure for applying", "User manual"
    )

    service["application_procedure"] = [
        re.sub(r"^\s*\d+[\.)]\s*", "", line).strip()
        for line in procedure.splitlines()
        if line.strip()
    ]

    # Save as a JSON array so more services can be added later
    services = []

    if OUTPUT_FILE.exists():
        try:
            services = json.loads(
                OUTPUT_FILE.read_text(encoding="utf-8")
            )
        except json.JSONDecodeError:
            print("Existing JSON is invalid. Creating a new file.")

    # Avoid adding the same service twice
    services = [
        item for item in services
        if item.get("service_name") != service["service_name"]
    ]

    services.append(service)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT_FILE.write_text(
        json.dumps(services, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )

    print("\nJSON conversion completed!")
    print("Saved to:", OUTPUT_FILE)

    print("\nExtracted information:")
    print(json.dumps(service, indent=4, ensure_ascii=False))


if __name__ == "__main__":
    convert_to_json()
