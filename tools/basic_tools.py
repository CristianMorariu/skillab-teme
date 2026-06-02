import datetime
from .registry import register_tool
from .params_models import (
    CalculatorParams,
    GetDatetimeParams,
    WebSearchParams,
    CurrencyParams,
    RandomFactParams,
)


@register_tool
def calculator(params: CalculatorParams) -> str:
    """Calculează rezultatul unei expresii matematice. Primește expresia ca string, ex: '2 + 3 * 4'."""
    try:
        result = eval(params.expression)
        return f"Rezultatul expresiei '{params.expression}' este: {result}"
    except Exception as e:
        return f"Eroare la calcul: {e}"


@register_tool
def get_datetime(params: GetDatetimeParams) -> str:
    """Returnează data și ora curentă pentru un timezone dat."""
    now = datetime.datetime.now()
    return (
        f"Data și ora curentă: {now.strftime('%Y-%m-%d %H:%M:%S')} ({params.timezone})"
    )


@register_tool
def web_search(params: WebSearchParams) -> str:
    """Caută informații pe web după un query text și returnează rezultatele relevante."""
    return f"[Simulat] Rezultate pentru '{params.query}': rezultat 1, rezultat 2, rezultat 3"


@register_tool
def currency(params: CurrencyParams) -> str:
    """Convertește o sumă dintr-o valută în alta folosind cursuri aproximative față de EUR."""
    rates_to_eur = {
        "EUR": 1.0,
        "USD": 1.08,
        "RON": 5.0,
        "GBP": 0.86,
        "CHF": 0.97,
    }
    from_cur = params.from_currency.upper()
    to_cur = params.to_currency.upper()
    if from_cur not in rates_to_eur:
        return f"Valuta '{from_cur}' nu este suportată. Valute disponibile: {', '.join(rates_to_eur)}"
    if to_cur not in rates_to_eur:
        return f"Valuta '{to_cur}' nu este suportată. Valute disponibile: {', '.join(rates_to_eur)}"
    amount_in_eur = params.amount / rates_to_eur[from_cur]
    result = amount_in_eur * rates_to_eur[to_cur]
    return f"{params.amount} {from_cur} = {result:.2f} {to_cur} (curs aproximativ)"


@register_tool
def random_fact(params: RandomFactParams) -> str:
    """Returnează un fapt interesant aleatoriu."""
    import random

    facts = [
        "Mierea nu se strică niciodată — s-au găsit borcane de miere vechi de 3000 de ani în mormintele egiptenilor.",
        "Un fulger are o temperatură de aproximativ 30.000 Kelvin — de 5 ori mai fierbinte decât suprafața Soarelui.",
        "Caracatițele au trei inimi și sânge albastru.",
        "Bananas sunt ușor radioactive datorită potasiului-40 pe care îl conțin.",
        "O zi pe Venus este mai lungă decât un an pe Venus.",
        "Pixelul cel mai folosit pe internet este albul (#FFFFFF).",
        "Python a fost numit după trupa Monty Python, nu după șarpele boa.",
    ]
    return random.choice(facts)
