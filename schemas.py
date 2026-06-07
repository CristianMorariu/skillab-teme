from typing import List

from pydantic import BaseModel, Field


class Product(BaseModel):
    denumire: str
    cantitate: int
    pret_unitar: float
    total: float


class Invoice(BaseModel):
    """Schemă pentru extracția datelor dintr-o factură."""

    numar: str = Field(description="Numărul facturii (ex: FV-2024-001)")
    data: str = Field(description="Data emiterii facturii")
    furnizor: str = Field(description="Numele furnizorului")
    client: str = Field(description="Numele clientului")
    produse: List[Product] = Field(
        default=[], description="Lista produselor/serviciilor"
    )
    total: float = Field(description="Suma totală de plată în RON")


class Contract(BaseModel):
    """Schemă pentru extracția datelor dintr-un contract."""

    numar: str = Field(description="Numărul contractului (ex: CS-2024-015)")
    data_incheiere: str = Field(description="Data semnării contractului")
    prestator: str = Field(description="Numele prestatorului de servicii")
    beneficiar: str = Field(description="Numele beneficiarului")
    valoare: float = Field(description="Valoarea contractului")
    durata_luni: int = Field(description="Durata contractului în luni")
    obligatii_prestator: List[str] = Field(
        default=[], description="Lista obligațiilor prestatorului"
    )
