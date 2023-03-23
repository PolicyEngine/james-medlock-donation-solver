import streamlit as st

st.set_page_config(page_title="James Medlock donation solver")

st.title("How much should James Medlock donate to GiveDirectly?")

st.subheader(
    "[Read the PolicyEngine blog post](https://policyengine.org/us/blog/2023-03-23-medlock-donation-calculator)"
)

st.write(
    "Twitter user James Medlock has entered a \$1 million bet with Balaji Srinivasan. If he wins, he plans to give enough to GiveDirectly such that he takes home \$300,000 after taxes and donations. This app uses the PolicyEngine US Python package to estimate out how much he should donate."
)

import json
import pandas as pd
from policyengine_us import Simulation, CountryTaxBenefitSystem
import plotly.express as px
import pkg_resources


system = CountryTaxBenefitSystem()

STATE_CODE = "CA"

# Ask for employment income and self-employment income for both spouses, numeric entry

filer_employment_income = st.number_input(
    "How much will Medlock earn from wages and salaries in 2023?", value=0
)
filer_self_employment_income = st.number_input(
    "How much will Medlock earn from self-employment in 2023?", value=0
)

spouse_employment_income = st.number_input(
    "How much will Medlock's wife earn from wages and salaries in 2023?",
    value=0,
)
spouse_self_employment_income = st.number_input(
    "How much will Medlock's wife earn from self-employment in 2023?",
    value=0,
)


WINNINGS = 1_000_000
TAKE_HOME_SHARE = 0.3


base_situation = {
    "people": {
        "filer": {
            "age": {2023: 33},
            "employment_income": {2023: filer_employment_income},
            "self_employment_income": {2023: filer_self_employment_income},
        },
        "spouse": {
            "age": {2023: 33},
            "employment_income": {2023: spouse_employment_income},
            "self_employment_income": {2023: spouse_self_employment_income},
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
            "state_code": {2023: STATE_CODE},
        },
    },
}


# Show a loading message while the data is being fetched.


def get_df():
    simulation = Simulation(situation=base_situation)
    situation = json.loads(json.dumps(base_situation))
    situation["people"]["filer"]["miscellaneous_income"] = {2023: WINNINGS}
    situation["axes"] = [
        [
            {
                "name": "charitable_cash_donations",
                "period": 2023,
                "min": 0,
                "max": WINNINGS,
                "count": 100,
            }
        ]
    ]

    alt_simulation = Simulation(situation=situation)
    donations = alt_simulation.calculate(
        "charitable_cash_donations", 2023, map_to="household"
    )
    tax_changes = (
        alt_simulation.calculate("household_tax", 2023)
        - simulation.calculate("household_tax", 2023)[0]
    )
    net_income = simulation.calculate("household_net_income", 2023)[0]
    net_income_changes = (
        alt_simulation.calculate("household_net_income", 2023)
        - donations
        - net_income
    )
    take_home_pct = net_income_changes / WINNINGS

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
        str_df[col] = df[col].apply(lambda x: f"${x:,.0f}")

    for col in df.columns[-1:]:
        str_df[col] = df[col].apply(lambda x: f"{x:.1%}")

    # Pick the row closest to the donation rate
    df_subset = df.iloc[
        (df["Take-home percentage"] - TAKE_HOME_SHARE).abs().argsort()[:1]
    ]

    st.write(
        f"If Medlock donates **${df_subset['Donation'].values[0]:,.0f}**, he will take home {df_subset['Take-home percentage'].values[0]:.1%} of his winnings after taxes and donations."
    )

    st.write(str_df)

    fig = px.line(
        df,
        x="Donation",
        y="Take-home percentage",
        title="How Medlock's donation affects the share of winnings he takes home",
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
        y0=TAKE_HOME_SHARE,
        x1=df["Donation"].max(),
        y1=TAKE_HOME_SHARE,
        line=dict(color="#616161", dash="dash"),
    )

    # Add a label at the point where the lines intersect with the (x, y) coordinates
    fig.add_annotation(
        x=df_subset["Donation"].values[0],
        y=df_subset["Take-home percentage"].values[0] * 0.95,
        text=f"Take-home percentage: {df_subset['Take-home percentage'].values[0]:.1%} <br />from a donation of ${df_subset['Donation'].values[0]:,.0f}",
        showarrow=True,
        arrowhead=1,
        ax=0,
        ay=50,
    )

    st.plotly_chart(fig)

st.header("Assumptions")

# Get the version of policyengine_us
policyengine_us_version = pkg_resources.get_distribution(
    "policyengine_us"
).version

st.write(
    f"This uses the [PolicyEngine US Python package v{policyengine_us_version}](https://github.com/PolicyEngine/policyengine-us), assuming Medlock lives in California, and that he and his wife are both 33 years old and have no other income or special circumstances that would provide tax credits or deductions (beyond SALT and the charitable deduction). California has not yet released 2023 tax brackets, so we use 2022 values."
)
