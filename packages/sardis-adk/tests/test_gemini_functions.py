from sardis_adk.gemini_functions import get_sardis_gemini_tools


def test_gemini_function_declarations_include_payment_tools():
    tools = get_sardis_gemini_tools()

    declarations = tools["function_declarations"]
    names = {declaration["name"] for declaration in declarations}

    assert "sardis_pay" in names
    assert "sardis_check_balance" in names
    assert "sardis_check_policy" in names
