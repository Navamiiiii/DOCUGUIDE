
from playwright.sync_api import sync_playwright
from pathlib import Path

# Seva Sindhu Departments & Services page
URL = "https://sevasindhu.karnataka.gov.in/Sevasindhu/DepartmentServices"

# Income Certificate service ID identified from DevTools
SERVICE_ID = 17

SERVICE_NAME = "Income Certificate"


def extract_service(page):

    print("\nOpening Income Certificate...")

    # Locate the Income Certificate link
    service = page.locator(
        f'a[onclick="servdetails({SERVICE_ID})"]'
    )

    if service.count() == 0:
        raise Exception("Income Certificate link not found!")

    # Click the service
    service.first.click()

    print("Service clicked successfully!")

    # Locate the popup
    popup = page.locator("#myModal")

    # Wait for popup to become visible
    popup.wait_for(
        state="visible",
        timeout=20000
    )

    print("Popup opened successfully!")

    # Wait until popup content is available
    page.wait_for_timeout(2000)

    # Extract complete popup text
    popup_text = popup.inner_text().strip()

    if not popup_text:
        raise Exception("Popup opened, but no text was extracted!")

    print("\n========== COMPLETE SERVICE INFORMATION ==========\n")

    print(popup_text)

    # Save extracted information
    output_path = Path("data/income_certificate_output.txt")

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(popup_text)

    print("\n========== EXTRACTION SUMMARY ==========")

    print("Service:", SERVICE_NAME)

    print("Characters extracted:", len(popup_text))

    print("Output saved to:", output_path)

    return popup_text


def main():

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=False
        )

        page = browser.new_page()

        try:

            print("Opening Seva Sindhu...")

            page.goto(
                URL,
                wait_until="domcontentloaded",
                timeout=60000
            )

            print("Website opened successfully!")

            input(
                "\nNavigate to the Departments & Services page "
                "if required, then press ENTER in this terminal..."
            )

            result = extract_service(page)

            print("\nExtraction completed successfully!")

        except Exception as error:

            print("\nERROR OCCURRED:")
            print(repr(error))

        finally:

            input("\nPress ENTER to close the browser...")

            browser.close()


if __name__ == "__main__":
    main()
