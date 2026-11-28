"""Tests for the Member 4 user interface (app.py)."""

import app
import data_manager

VERIFIED = {
    # Made-up record used ONLY for testing. It is never written to services.json.
    "service_name": "Test Certificate",
    "eligibility": "Test eligibility",
    "required_documents": ["Test document"],
    "application_fee": "Rs.1",
    "service_charge": "Rs.2",
    "processing_time": "3",
    "application_procedure": ["Step one"],
    "official_link": "https://example.karnataka.gov.in/apply",
    "source_url": "https://example.karnataka.gov.in/info",
    "last_verified": "2026-01-15",
}


def services():
    return data_manager.list_services()


def test_search_finds_names_and_small_typos():
    assert app.search_services("income", services()) == ["Income Certificate"]
    assert app.search_services("incme", services()) == ["Income Certificate"]
    assert app.search_services("CASTE certificate", services()) == ["Caste Certificate"]


def test_search_empty_or_generic_shows_all():
    everything = app.service_names(services())
    assert app.search_services("", services()) == everything
    assert app.search_services("certificate", services()) == everything


def test_search_does_not_guess_unknown_services():
    assert app.search_services("marriage certificate", services()) == []
    assert app.search_services("passport", services()) == []


def test_unverified_fee_and_time_are_hidden():
    record = dict(VERIFIED, last_verified="")
    text = app.fees_markdown(record)
    assert "Rs.1" not in text and "3 days" not in text
    assert text.count("Awaiting verification") == 3


def test_verified_record_shows_values():
    text = app.fees_markdown(VERIFIED)
    assert "Rs.1" in text and "3 days" in text
    assert "https://example.karnataka.gov.in/apply" in app.link_html(VERIFIED)


def test_verification_needs_date_and_official_source():
    assert app.is_verified(VERIFIED)
    assert not app.is_verified(dict(VERIFIED, source_url=""))
    assert not app.is_verified(dict(VERIFIED, source_url="https://example.com"))
    assert not app.is_verified(dict(VERIFIED, last_verified="yesterday"))


def test_only_government_links_are_accepted():
    for bad in ["", None, "javascript:alert(1)", "https://example.com",
                "https://gov.in.example.com", "http://["]:
        assert app.official_url(bad) is None


def test_na_documents_are_not_a_checklist_item():
    heading, documents = app.documents_view({"service_name": "x", "required_documents": ["NA"]})
    assert documents == [] and "NA" in heading


def test_missing_fields_say_not_available():
    record = {"service_name": "Empty"}
    for text in (app.eligibility_markdown(record), app.procedure_markdown(record),
                 app.fees_markdown(record), app.link_html(record),
                 app.documents_view(record)[0]):
        assert app.NOT_AVAILABLE in text


def test_show_service_returns_one_value_per_output():
    for name in app.service_names(services()) + [None, "Unknown"]:
        assert len(app.show_service(name)) == 8


def test_broken_json_does_not_crash(tmp_path, monkeypatch):
    bad = tmp_path / "services.json"
    bad.write_text("{ not json", encoding="utf-8")
    monkeypatch.setattr(data_manager, "DATA_FILE", bad)
    assert app.load_services() == ([], app.DATA_ERROR)
    assert app.show_service("Income Certificate")[0] == app.DATA_ERROR
    assert "something went wrong" in app.respond("fee?", [], None)[0]
    assert app.build_app() is not None


def test_chat_uses_selected_service():
    answer, active = app.respond("what documents do I need?", [], "Residence Certificate")
    assert "Residence Certificate" in answer and active == "Residence Certificate"


def test_chat_reads_new_gradio_history():
    history = [{"role": "user", "content": [{"type": "text", "text": "income certificate"}]}]
    answer, _ = app.respond("what is the fee?", history, None)
    assert "Income Certificate" in answer


def test_details_hidden_until_a_real_service_is_chosen():
    assert app.details_visibility(None)["visible"] is False
    assert app.details_visibility("Marriage Certificate")["visible"] is False
    assert app.details_visibility("Income Certificate")["visible"] is True


def test_unsupported_search_selects_nothing():
    dropdown, message = app.run_search("marriage certificate")
    assert dropdown["value"] is None and "No matching service" in message


def test_search_opens_only_an_unambiguous_match():
    assert app.run_search("income")[0]["value"] == "Income Certificate"
    assert app.run_search("certificate")[0]["value"] is None


def test_unverified_warning_appears_only_once():
    record = dict(VERIFIED, last_verified="")
    heading, _ = app.documents_view(record)
    page = "".join([app.status_markdown(record), app.eligibility_markdown(record), heading,
                    app.procedure_markdown(record), app.fees_markdown(record),
                    app.link_html(record)])
    assert page.count("Not yet verified") == 1