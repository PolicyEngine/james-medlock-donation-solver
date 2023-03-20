import streamlit as st

st.title("How much should James Medlock donate?")

st.write(
    "James Medlock may potentially win a $1m bet and wants to ensure he takes home 70\% of his winnings after taxes, by donating a certain amount to charity. This app will help him figure out how much he should donate."
)

import json
import numpy as np
import pandas as pd
from policyengine_us import Simulation, CountryTaxBenefitSystem

system = CountryTaxBenefitSystem()

# state_code = st.selectbox("What state do you live in?", [enum.name for enum in system.variables["state_code"].possible_values])

state_code = "CA"

# is_joint = st.checkbox("Are you filing jointly?", value=False)

is_joint = True

if is_joint:
    # Ask for employment income and self-employment income for both spouses, numeric entry

    filer_employment_income = st.number_input(
        "How much did James earn from wages and salaries?", value=0
    )
    filer_self_employment_income = st.number_input(
        "How much did James earn from self-employment?", value=0
    )

    spouse_employment_income = st.number_input(
        "How much did James' spouse earn from wages and salaries?", value=0
    )
    spouse_self_employment_income = st.number_input(
        "How much did James' spouse earn from self-employment?", value=0
    )

    base_situation = {
        "people": {
            "filer": {
                "age": {2023: 40},
                "employment_income": {2023: filer_employment_income},
                "self_employment_income": {2023: filer_self_employment_income},
            },
            "spouse": {
                "age": {2023: 40},
                "employment_income": {2023: spouse_employment_income},
                "self_employment_income": {
                    2023: spouse_self_employment_income
                },
            },
        },
        "tax_units": {
            "tax_unit": {
                "members": ["filer", "spouse"],
            }
        },
        "spm_units": {
            "spm_unit": {
                "members": ["filer", "spouse"],
            }
        },
        "households": {
            "household": {
                "members": ["filer", "spouse"],
                "state_code": {2023: state_code},
            },
        },
    }

else:
    # Ask for employment income and self-employment income for one spouse, numeric entry

    filer_employment_income = st.number_input(
        "How much did James earn from wages and salaries?", value=0
    )
    filer_self_employment_income = st.number_input(
        "How much did James earn from self-employment?", value=0
    )

    base_situation = {
        "people": {
            "filer": {
                "age": {2023: 40},
                "employment_income": {2023: filer_employment_income},
                "self_employment_income": {2023: filer_self_employment_income},
            },
        },
        "tax_units": {
            "tax_unit": {
                "members": ["filer"],
            }
        },
        "spm_units": {
            "spm_unit": {
                "members": ["filer"],
            }
        },
        "households": {
            "household": {
                "members": ["filer"],
                "state_code": {2023: state_code},
            },
        },
    }


winnings = st.number_input("How much will James win?", value=1000000)

donation_rate = st.slider(
    "What take-home percentage rate does James want to ensure?",
    min_value=0.0,
    max_value=1.0,
    value=0.7,
    step=0.01,
)


def get_donation_etr(donation):
    situation = json.loads(json.dumps(base_situation))
    situation["people"]["filer"]["taxable_pension_income"][2023] = winnings
    situation["people"]["filer"]["charitable_cash_donations"][2023] = donation

    alt_simulation = Simulation(situation=situation)
    return (
        alt_simulation.calculate("household_tax", 2023)[0]
        - simulation.calculate("household_tax", 2023)[0],
        alt_simulation.calculate("household_net_income", 2023)[0]
        - simulation.calculate("household_net_income", 2023)[0]
        - donation,
    )


# Show a loading message while the data is being fetched.


@st.cache_data(show_spinner=False)
def get_df(net_income):
    donations = []
    tax_changes = []
    net_income_changes = []
    etrs = []
    for donation in np.linspace(0, winnings, 20):
        donations += [donation]
        tax_change, net_income_change = get_donation_etr(donation)
        tax_changes += [tax_change]
        net_income_changes += [net_income_change]
        etrs += [1 - net_income_change / winnings]

    return pd.DataFrame(
        {
            "Donation": donations,
            "Tax change": tax_changes,
            "Baseline net income": net_income,
            "Net income change": net_income_changes,
            "Effective tax rate": etrs,
        }
    )


calculate_pressed = True

if calculate_pressed:
    simulation = Simulation(situation=base_situation)
    net_income = simulation.calculate("household_net_income", 2023)[0]
    with st.spinner(
        "Calculating James' take-home winnings under different donation sizes..."
    ):
        df = get_df(net_income)

    str_df = df.copy()

    for col in df.columns[:-1]:
        str_df[col] = df[col].apply(lambda x: f"${x:,.2f}")

    for col in df.columns[-1:]:
        str_df[col] = df[col].apply(lambda x: f"{x:.2%}")

    # Pick the row closest to the donation rate
    df = df.iloc[
        (df["Effective tax rate"] - donation_rate).abs().argsort()[:1]
    ]

    st.write(
        f"To ensure that James takes home close to {donation_rate:.2%} of his winnings, he should donate ${df['Donation'].values[0]:,.2f}. This results in a take-home percentage of {df['Effective tax rate'].values[0]:.2%}."
    )

    st.write(str_df)
