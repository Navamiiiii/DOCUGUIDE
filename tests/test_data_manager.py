from data_manager import list_services, get_service

def test_services_load():
    assert isinstance(list_services(), list)

def test_fuzzy_lookup():
    result = get_service("income cert")
    assert result is None or result["service_name"] == "Income Certificate"
