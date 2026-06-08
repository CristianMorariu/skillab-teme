from pydantic import BaseModel, Field


class CalculatorParams(BaseModel):
    expression: str = Field(
        description="Expresia matematică de evaluat (ex: '2 + 3 * 4')", min_length=1
    )


class GetDatetimeParams(BaseModel):
    timezone: str = Field(default="Europe/Bucharest", description="Timezone-ul dorit")


class WebSearchParams(BaseModel):
    query: str = Field(description="Termenii de căutat pe web", min_length=2)
    max_results: int = Field(
        default=5, description="Numărul maxim de rezultate returnate", ge=1, le=20
    )


class CurrencyParams(BaseModel):
    amount: float = Field(description="Suma de convertit", gt=0)
    from_currency: str = Field(description="Valuta sursă (ex: EUR, USD, RON)")
    to_currency: str = Field(description="Valuta destinație (ex: EUR, USD, RON)")


class RandomFactParams(BaseModel):
    pass


class SearchDocumentsParams(BaseModel):
    query: str = Field(
        description="Întrebarea sau subiectul căutat în documente", min_length=3
    )
