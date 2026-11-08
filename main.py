from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="TP Modélisation - Chemical Operations")


class SimulationInput(BaseModel):
    m0: float = Field(default=1000.0, gt=0, description="Débit initial (kg/h)")
    x0: float = Field(default=0.10, ge=0, le=1, description="Fraction soluble à l'entrée")
    residus: float = Field(default=20.0, ge=0, description="Résidus filtrés (kg/h)")

    mR: float = Field(default=100.0, ge=0, description="Débit ajouté au mélange (kg/h)")
    xR: float = Field(default=0.40, ge=0, le=1, description="Fraction soluble du courant ajouté")

    Cp: float = Field(default=3.8, gt=0, description="Capacité thermique (kJ/(kg·°C))")
    T2: float = 20.0
    T3: float = 80.0

    x4: float = Field(default=0.40, gt=0, le=1, description="Fraction soluble cible après évaporation")
    lambda_v: float = Field(default=2300.0, gt=0, description="Chaleur latente (kJ/kg)")

    T4: float = 80.0
    T5: float = 25.0


@app.get("/")
def home():
    return {
        "message": "API de simulation des opérations chimiques",
        "documentation": "/docs",
        "endpoint": "POST /run-tp",
    }


@app.post("/run-tp")
def run_tp_simulation(data: SimulationInput):
    # 1. Filtration: on suppose que toute la matière soluble passe dans le filtrat.
    if data.residus >= data.m0:
        raise HTTPException(
            status_code=400,
            detail="Les résidus doivent être inférieurs au débit initial.",
        )

    m1 = data.m0 - data.residus
    x1 = (data.m0 * data.x0) / m1

    if x1 > 1:
        raise HTTPException(
            status_code=400,
            detail="La fraction soluble calculée après filtration dépasse 1.",
        )

    # 2. Mélange
    m2 = m1 + data.mR
    x2 = (m1 * x1 + data.mR * data.xR) / m2

    # 3. Chauffage (kW, si les débits sont en kg/h)
    Q3_kW = (m2 * data.Cp * (data.T3 - data.T2)) / 3600

    # 4. Évaporation
    if data.x4 < x2:
        raise HTTPException(
            status_code=400,
            detail="La fraction cible x4 doit être au moins égale à x2.",
        )

    m4 = (m2 * x2) / data.x4
    mv = m2 - m4
    Q4_kW = (mv * data.lambda_v) / 3600

    # 5. Refroidissement (puissance à extraire lorsque T4 > T5)
    Q5_kW = (m4 * data.Cp * (data.T4 - data.T5)) / 3600

    return {
        "1_Filtration": {"m1_kg_h": m1, "x1": x1},
        "2_Melange": {"m2_kg_h": m2, "x2": x2},
        "3_Chauffage": {"Q3_kW": Q3_kW},
        "4_Evaporation": {"m4_kg_h": m4, "mv_kg_h": mv, "Q4_kW": Q4_kW},
        "5_Refroidissement": {"Q5_extrait_kW": Q5_kW},
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
