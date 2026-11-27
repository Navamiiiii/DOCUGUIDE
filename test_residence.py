
from playwright.sync_api import sync_playwright
from pathlib import Path

URL = "https://sevasindhu.karnataka.gov.in/Sevasindhu/DepartmentServices"

SERVICE_ID = 29
SERVICE_NAME = "Residence Certificate"


def main():

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        try:
            print("Opening Seva Sindhu...")

            page.goto(URL, wait_until="domcontentloaded", timeout=60000)

            print("Website opened!")

            input(
                "\nNavigate to Departments & Services page "
                "and press ENTER..."
            )

            print("\nOpening Residence Certificate...")

            service = page.locator(
                f'a[onclick="servdetails({SERVICE_ID})"]'
            )

            if service.count() == 0:
                raise Exception("Residence Certificate link not found!")

            service.first.click()

            popup = page.locator("#myModal")
            popup.wait_for(state="visible", timeout=20000)

            page.wait_for_timeout(1500)

            popup_text = popup.inner_text().strip()

            if not popup_text:
                raise Exception("No information extracted!")

            print("\n========== SERVICE INFORMATION ==========\n")
            print(popup_text)

            output = Path("data/residence_certificate.txt")
            output.parent.mkdir(parents=True, exist_ok=True)

            output.write_text(popup_text, encoding="utf-8")

            print("\nExtraction completed successfully!")
            print("Saved to:", output)

        except Exception as error:
            print("\nERROR:", error)

        finally:
            input("\nPress ENTER to close browser...")
            browser.close()


if __name__ == "__main__":
    main()
