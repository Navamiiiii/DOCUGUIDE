
import json
from pathlib import Path

file_path = Path("data/services.json")

required_fields = [
    "service_name",
    "department",
    "portal",
    "service_description",
    "eligibility",
    "required_documents",
    "application_fee",
    "service_charge",
    "processing_time",
    "application_procedure",
    "official_link",
    "source_url"
]

try:
    with open(file_path, "r", encoding="utf-8") as file:
        services = json.load(file)

    print("JSON file is valid!")
    print("Total services:", len(services))

    for index, service in enumerate(services, start=1):
        print(f"\n--- Service {index}: {service.get('service_name', 'Unnamed')} ---")

        missing_fields = []

        for field in required_fields:
            if field not in service:
                missing_fields.append(field)

        if missing_fields:
            print("Missing fields:", missing_fields)
        else:
            print("All required fields exist.")

        empty_fields = []

        for field in required_fields:
            value = service.get(field)

            if value is None or value == "" or value == []:
                empty_fields.append(field)

        if empty_fields:
            print("Fields needing attention:", empty_fields)
        else:
            print("No empty fields.")

except json.JSONDecodeError as error:
    print("Invalid JSON format:", error)

except FileNotFoundError:
    print("services.json was not found. Check the file location.")
