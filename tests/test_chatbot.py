"""Regression tests for safe certificate recognition and JSON-grounded answers."""

import pytest

from chatbot import answer_question
from nlp import parse_query


@pytest.mark.parametrize(
    ("question", "expected_service"),
    [
        ("What documents do I need for an income certificate?", "Income Certificate"),
        ("How long does a residence certificate take?", "Residence Certificate"),
        ("What documents for caste certificate?", "Caste Certificate"),
        ("What is the process for birth certificate?", "Birth Certificate"),
    ],
)
def test_supported_services_are_recognized(question, expected_service):
    parsed = parse_query(question)
    assert parsed.service_name == expected_service
    assert parsed.unsupported_service is None


@pytest.mark.parametrize(
    ("question", "expected_service", "expected_fact"),
    [
        ("What documents for income certificate?", "Income Certificate", "Salary certificate self declaration"),
        ("How long does residence certificate take?", "Residence Certificate", "14"),
        ("What documents for caste certificate?", "Caste Certificate", "Old Caste Certificate"),
        ("What is the process for birth certificate?", "Birth Certificate", "Applicant will get the Acknowledgment"),
    ],
)
def test_answer_uses_the_matching_json_record(question, expected_service, expected_fact):
    answer = answer_question(question)
    assert expected_service in answer
    assert expected_fact in answer


def test_service_name_followed_by_details_returns_that_service_overview():
    answer = answer_question("income certificate details")
    assert "**Income Certificate**" in answer
    assert "Salary certificate self declaration" in answer
    assert "Caste Certificate —" not in answer


def test_missing_acknowledgement_uses_birth_procedure_without_dumping_record():
    answer = answer_question(
        "I did not receive acknowledgement",
        context_service="Birth Certificate",
    )
    assert "Birth Certificate" in answer
    assert "Applicant will get the Acknowledgment" in answer
    assert "does not explain what to do if you did not receive it" in answer
    assert "Caste Certificate" not in answer


def test_birth_na_is_not_presented_as_a_required_document():
    answer = answer_question("What documents are needed for a birth certificate?")
    assert "does not name any supporting documents" in answer
    assert "1. NA" not in answer


def test_document_question_without_service_does_not_assume_a_certificate():
    answer = answer_question("Is ration card required?")
    assert "Income Certificate, Residence Certificate, Caste Certificate" in answer
    assert "Please specify one" in answer
    assert "If you meant Income Certificate, yes" not in answer


def test_unrecognized_question_does_not_dump_selected_service_details():
    answer = answer_question("I have a question", context_service="Birth Certificate")
    assert "Birth Certificate" in answer
    assert "recognized" in answer
    assert "Citizens can use this service" not in answer


def test_marriage_certificate_is_not_fuzzy_matched_to_caste():
    question = "Marriage Certificate details"
    parsed = parse_query(question)
    answer = answer_question(question)

    assert parsed.service_name is None
    assert parsed.unsupported_service == "Marriage Certificate"
    assert "don't have information about Marriage Certificate" in answer
    assert "Caste Certificate —" not in answer
    assert "Caste Certificate (Cat-A)" not in answer


def test_unsupported_certificate_overrides_selected_service_context():
    answer = answer_question(
        "Marriage Certificate details",
        context_service="Caste Certificate",
    )

    assert "Marriage Certificate" in answer
    assert "Caste Certificate —" not in answer


def test_multiple_supported_certificates_require_clarification():
    parsed = parse_query("Compare income certificate and residence certificate")
    answer = answer_question("Compare income certificate and residence certificate")

    assert parsed.service_name is None
    assert set(parsed.ambiguous_services) == {"Income Certificate", "Residence Certificate"}
    assert "Which one do you mean?" in answer
