import streamlit as st

st.title("How much should James Medlock donate?")

st.write(
    "James Medlock may potentially win a $1m bet and wants to ensure he takes home 70\% of his winnings after taxes, by donating a certain amount to charity. This app will help him figure out how much he should donate."
)

import json
import numpy as np
import pandas as pd
from policyengine_us import Simulation, CountryTaxBenefitSystem
import plotly.express as px

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
                "premium_tax_credit": {2023: 0},
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
                "premium_tax_credit": {2023: 0},
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


# Show a loading message while the data is being fetched.


def get_df():
    simulation = Simulation(situation=base_situation)
    situation = json.loads(json.dumps(base_situation))
    situation["people"]["filer"]["taxable_pension_income"] = {2023: winnings}
    situation["axes"] = [[{
        "name": "charitable_cash_donations",
        "period": 2023,
        "min": 0,
        "max": winnings,
        "count": 100,
    }]]

    alt_simulation = Simulation(situation=situation)
    donations = alt_simulation.calculate("charitable_cash_donations", 2023, map_to="household")
    tax_changes = alt_simulation.calculate("household_tax", 2023) - simulation.calculate("household_tax", 2023)[0]
    net_income = simulation.calculate("household_net_income", 2023)[0]
    net_income_changes = alt_simulation.calculate("household_net_income", 2023) - donations - net_income
    take_home_pct = net_income_changes / winnings

    return pd.DataFrame(
        {
            "Donation": donations,
            "Tax change": tax_changes,
            "Baseline net income": [net_income] * len(donations),
            "Net income change": net_income_changes,
            "Take-home percentage": take_home_pct,
        }
    )


calculate_pressed = True

if calculate_pressed:
    with st.spinner(
        "Calculating James' take-home winnings under different donation sizes..."
    ):
        df = get_df()

    str_df = df.copy()

    for col in df.columns[:-1]:
        str_df[col] = df[col].apply(lambda x: f"${x:,.2f}")

    for col in df.columns[-1:]:
        str_df[col] = df[col].apply(lambda x: f"{x:.2%}")

    donation_rate = st.slider(
        "What take-home percentage rate does James want to ensure?",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.01,
    )

    # Pick the row closest to the donation rate
    df_subset = df.iloc[
        (df["Take-home percentage"] - donation_rate).abs().argsort()[:1]
    ]

    st.write(
        f"To ensure that James takes home close to {donation_rate:.2%} of his winnings, he should donate ${df_subset['Donation'].values[0]:,.2f}. This results in a take-home percentage of {df_subset['Take-home percentage'].values[0]:.2%}."
    )

    st.write(str_df)

    fig = px.line(
        df,
        x="Donation",
        y="Take-home percentage",
        title="Take-home percentage vs. donation size",
        color_discrete_sequence=["#2C6496"],
    ).update_layout(
        xaxis_title="Donation size",
        xaxis_tickformat="$,.0f",
        xaxis_range=[0, df["Donation"].max()],
        yaxis_title="Take-home percentage",
        yaxis_range=[0, 1],
        yaxis_tickformat=".0%",
        width=800,
        height=600,
        template="plotly_white",
    )
    
    # Add a horizontal line at the donation rate
    fig.add_shape(
        type="line",
        x0=0,
        y0=donation_rate,
        x1=df["Donation"].max(),
        y1=donation_rate,
        line=dict(color="#616161", dash="dash"),
    )

    # Add a label at the point where the lines intersect with the (x, y) coordinates
    fig.add_annotation(
        x=df_subset["Donation"].values[0] * 1.05,
        y=df_subset["Take-home percentage"].values[0] * 0.95,
        text=f"Take-home percentage: {df_subset['Take-home percentage'].values[0]:.2%} <br />from a donation of ${df_subset['Donation'].values[0]:,.2f}",
        showarrow=True,
        arrowhead=1,
        ax=0,
        ay=50,
    )

    st.plotly_chart(fig)