import pandas as pd
import numpy as np 
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d 
from scipy.optimize import brentq
import datetime as dt
import psycopg2 
from sqlalchemy import create_engine
from urllib.parse import quote_plus
import QuantLib as ql

def get_connection():
    connection = create_engine(
        "postgresql+psycopg2://postgres:username@localhost:password/database_name"
    )
    return connection

connection = get_connection()

df = pd.read_sql("Select * from g_sec_data", connection)
print(df.head(5))
print(df.info())

df['trade'] = pd.to_datetime(df['trade'], format="%d-%m-%Y")
print(df.info())

df['coupon_rate'] = df['security_desc'].str.split(' ').str[0].astype(str)

coupon = df[df['trade'] ==pd.Timestamp('2026-08-21')].copy()
print(coupon)

df_cupon = coupon['isin'].unique()
print(df_cupon)
print(coupon['isin'].value_counts())

bond_check = coupon[['isin','security_desc','coupon_rate']].drop_duplicates('isin')
print(bond_check)

df2 = pd.read_csv('C:/Users/Ankush/Desktop/maturity_data.csv')
df2.columns = df2.columns.str.strip()

unique_isin = coupon['isin'].unique()
matched = pd.Series(unique_isin).isin(df2['ISIN'])
print("Total traded ISIN:", len(unique_isin))
print("Matched ISIN:", matched.sum())
print("Unmatched ISIN:", (~matched).sum())


coupon = df.loc[
    df['trade'].eq(pd.Timestamp('2026-08-21'))
].copy()

print('Coupon rows:',len(coupon))
print('Coupon ISIN:',coupon['isin'].nunique())
print(coupon[['isin','trade','trade_price','face_value']].head(10))

print("COUPON ISIN COUNT:", coupon['isin'].nunique())
print("FIRST COUPON ISINS:")
print(coupon['isin'].unique()[:10])

coupon['price_volume'] = coupon['trade_price'] * coupon['face_value']

v_data = coupon.groupby('isin').agg(
    total_price_volume=('price_volume','sum'),
    total_face_value=('face_value','sum'),
    trade_count=('isin','size')
)

v_data['vwap'] = (
    v_data['total_price_volume'] / v_data['total_face_value']
)

v_data = v_data.reset_index()

print('VWAP ISIN count:', len(v_data))
print(v_data.head(10))

del v_data

v_data = coupon.groupby('isin').agg(
    total_price_volume=('price_volume', 'sum'),
    total_face_value=('face_value', 'sum'),
    trade_count=('isin', 'size')
)

v_data['vwap'] = (
    v_data['total_price_volume'] /
    v_data['total_face_value']
)

v_data = v_data.reset_index()

print("VWAP ISIN COUNT:", len(v_data))
print(v_data.head(10))

bond_coupon = coupon[['isin','coupon_rate']].drop_duplicates('isin')

bond_master = (
    bond_coupon
    .merge(v_data, on='isin', how='left')
    .merge(df2,left_on='isin',right_on='ISIN',how='left')
)

bond_master = bond_master.drop(columns=['ISIN'])

bond_master = bond_master.rename(columns={
    'isin': 'ISIN',
    'coupon_rate': 'Coupon_Rate',
    'total_price_volume': 'Total_Price_Volume',
    'total_face_value': 'Total_Face_Value',
    'trade_count': 'Trade_Count',
    'vwap': 'VWAP',
    'Maturity date': 'Maturity_Date',
    'Coupon frequency': 'Coupon_Frequency',
    'Issuer': 'Issuer'
})

bond_master['Coupon_Rate'] = pd.to_numeric(
    bond_master['Coupon_Rate'],
    errors='coerce'
)

bond_master['Maturity_Date'] = pd.to_datetime(
    bond_master['Maturity_Date'],
    errors='coerce'
)

missing_bonds = bond_master[
    bond_master[
        ['Coupon_Rate', 'Maturity_Date', 'Coupon_Frequency']
    ].isnull().any(axis=1)
]

print(missing_bonds[
    ['ISIN', 'Coupon_Rate', 'Maturity_Date', 'Coupon_Frequency', 'Issuer', 'VWAP']
].to_string(index=False))

bootstrap_bonds = bond_master[
    bond_master['Coupon_Rate'].notna() &
    bond_master['Maturity_Date'].notna() &
    bond_master['Coupon_Frequency'].notna()
].copy()

print(
    bootstrap_bonds[
        ['ISIN', 'Coupon_Rate', 'Maturity_Date',
         'Coupon_Frequency', 'Issuer', 'VWAP']
    ].head(20).to_string(index=False)
)

print(bootstrap_bonds['Maturity_Date'].dt.year.drop_duplicates().sort_values(ascending=True))

diff_date = pd.to_datetime('2026-08-21')
bootstrap_bonds['years_to_mature'] = (bootstrap_bonds['Maturity_Date'] - diff_date).dt.days / 365.25



bootstrap_bonds = bootstrap_bonds[bootstrap_bonds['Issuer'] == 'GOI']
bootstrap_bonds = bootstrap_bonds[bootstrap_bonds['Coupon_Rate'] != 182.]
bootstrap_bonds = bootstrap_bonds[bootstrap_bonds['Coupon_Rate'] != 364.]
bootstrap_bonds = bootstrap_bonds[bootstrap_bonds['Coupon_Rate'] != 91.]
bootstrap_bonds = bootstrap_bonds[bootstrap_bonds['Coupon_Rate'] != 2.50]

tenors = []
for _, row in bootstrap_bonds.iterrows():
   if row['years_to_mature'] <= 1.000000:
       tenors.append(row)
   if 1.000000 < row['years_to_mature'] <= 3.000000:
        tenors.append(row) 
   if 3.000000 < row['years_to_mature'] <= 5.000000:
        tenors.append(row)
   if 5.000000 < row['years_to_mature'] <= 7.000000:
        tenors.append(row)
   if 7.000000 < row['years_to_mature'] <= 10.000000:
        tenors.append(row)
tenors = pd.DataFrame(tenors)

tenors = tenors.sort_values(by='years_to_mature')
    

target_tenors = [1,3,5,7,10]

for tenor in target_tenors:
    bootstrap_bonds[f"distance_{tenor}Y"] = (
        bootstrap_bonds['years_to_mature'] - tenor
    ).abs()


candidates_1Y = bootstrap_bonds[
    (bootstrap_bonds['years_to_mature'] > 0.5) &
    (bootstrap_bonds['years_to_mature'] < 1.5) 
].sort_values('distance_1Y')

candidates_3Y = bootstrap_bonds[
    (bootstrap_bonds['years_to_mature'] > 2.5) &
    (bootstrap_bonds['years_to_mature'] < 3.5) 
].sort_values('distance_3Y')

candidates_5Y = bootstrap_bonds[
    (bootstrap_bonds['years_to_mature'] > 4.5) &
    (bootstrap_bonds['years_to_mature'] < 5.5) 
].sort_values('distance_5Y')

candidates_7Y = bootstrap_bonds[
    (bootstrap_bonds['years_to_mature'] > 6.5) &
    (bootstrap_bonds['years_to_mature'] < 7.5) 
].sort_values('distance_7Y')

candidates_10Y = bootstrap_bonds[
    (bootstrap_bonds['years_to_mature'] > 9.5) &
    (bootstrap_bonds['years_to_mature'] < 10.5) 
].sort_values('distance_10Y')


isin_list = ['IN0020170026','IN0020190362','IN0020240076','IN0020260066','IN0020260025']
bond_validation = coupon[coupon['isin'].isin(isin_list)]

ytm = (
    coupon.groupby('isin')
    .apply(lambda x: (x['ytm_yield'] * x['face_value']).sum() / x['face_value'].sum())
    .reset_index(name='Market_YTM')
)

bootstrap_bonds = bootstrap_bonds.merge(
    ytm,
    left_on='ISIN',
    right_on='isin',
    how='left'
)

bootstrap_bonds.drop(columns=['isin'], inplace=True)

effective_dates = {'IN0020170026': ql.Date(15,5,2017),
    'IN0020190362': ql.Date(7,10,2019),
    'IN0020240076': ql.Date(18,6,2024),
    'IN0020260066': ql.Date(17,8,2026),
    'IN0020260025': ql.Date(11,5,2026)
}

def bond_calculation(
    isin,
    coupon_rate,
    effective_date,
    maturity_date,
    market_yeild,
    vwap,
    evaluation_date,
    face_value):
    ql.Settings.instance().evaluationDate = evaluation_date
    
    schedule = ql.Schedule(
        effective_date,
        maturity_date,
        ql.Period(ql.Semiannual),
        ql.India(ql.India.NSE),
        ql.Unadjusted,
        ql.Unadjusted,
        ql.DateGeneration.Backward,
        False
    )

    bond = ql.FixedRateBond(
        1,
        face_value,
        schedule,
        [coupon_rate],
        ql.Thirty360(ql.Thirty360.BondBasis),
        ql.ModifiedFollowing,
        face_value,
        effective_date
    )

    bond_cashflow = bond.cashflows()
    for cf in bond_cashflow:
        bond_date = cf.date()
        bond_amount = cf.amount()
    
    curve = ql.FlatForward(
        effective_date,
        market_yeild,
        ql.Thirty360(ql.Thirty360.BondBasis)
    )

    engine = ql.DiscountingBondEngine(
        ql.YieldTermStructureHandle(curve)
    )

    bond.setPricingEngine(engine)
    clean_price = bond.cleanPrice()
    bond_price = ql.BondPrice(clean_price,ql.BondPrice.Clean)
    dirty_price = bond.dirtyPrice()
    accured_interest = bond.accruedAmount()
    bond_ytm = bond.bondYield(
        bond_price,
        ql.Thirty360(ql.Thirty360.BondBasis),
        ql.Compounded,
        ql.Semiannual
    )

    duration = ql.BondFunctions.duration(
        bond,
        bond_ytm,
        ql.Thirty360(ql.Thirty360.BondBasis),
        ql.Compounded,
        ql.Semiannual
    )

    convexity = ql.BondFunctions.convexity(
        bond,
        bond_ytm,
        ql.Thirty360(ql.Thirty360.BondBasis),
        ql.Compounded,
        ql.Semiannual
    )

    return (schedule, bond, bond_date,bond_amount,clean_price,dirty_price,accured_interest,duration,convexity)

results = []
bonds = {}

selected_bonds = bootstrap_bonds[
    bootstrap_bonds['ISIN'].isin(isin_list)
].copy()

fixed_income = []
for _, row in selected_bonds.iterrows():
    isin = row['ISIN']
    coupon_rates = row['Coupon_Rate'] / 100
    effective_date_ql = effective_dates[isin]
    maturity_date = ql.Date(
        row['Maturity_Date'].day,
        row['Maturity_Date'].month,
        row['Maturity_Date'].year
    )
    market_yeild = row['Market_YTM'] / 100
    vwap = row['VWAP']
    evaluation_date = ql.Date(21,8,2026)
    face_value = 100.0

    result = bond_calculation(
        isin,
        coupon_rates,
        effective_date_ql,
        maturity_date,
        market_yeild,
        vwap,
        evaluation_date,
        face_value
    )

    results.append(result)

    # Store the correct FixedRateBond against its ISIN
    bonds[isin] = result[1]

    # Extract Duration and Convexity
    duration = result[7]
    convexity = result[8]

    fixed_income.append({
        'ISIN': isin,
        'Coupon_Rate': coupon_rates * 100,
        'Maturity_Date': maturity_date,
        'Years_to_Maturity': row['years_to_mature'],
        'Market_Price': vwap,
        'Market_YTM': market_yeild * 100,
        'Duration': duration,
        'Convexity': convexity
    })

bond_helper = []
def coupons_bond_helper(
    price,
    settlement_days,
    face_amount,
    coupon_schedule,
    coupon,
    day_count_convention,
    payment_convention,
    redemption,
    issue_date
):

    price_handle = ql.QuoteHandle(ql.SimpleQuote(price))

    helper = ql.FixedRateBondHelper(
        price_handle,
        settlement_days,
        face_amount,
        coupon_schedule,
        [coupon],
        day_count_convention,
        payment_convention,
        redemption,
        issue_date
    )
    return helper

for _, row in selected_bonds.iterrows():

    isin = row['ISIN']

    price = row['VWAP']
    settlement_days = 1
    face_amount = 100.0

    issue_date = effective_dates[isin]

    maturity_date = ql.Date(
        row['Maturity_Date'].day,
        row['Maturity_Date'].month,
        row['Maturity_Date'].year
    )

    coupon_schedule = ql.Schedule(
        issue_date,
        maturity_date,
        ql.Period(ql.Semiannual),
        ql.India(ql.India.NSE),
        ql.Unadjusted,
        ql.Unadjusted,
        ql.DateGeneration.Backward,
        False
    )

    coupon = row['Coupon_Rate'] / 100

    day_count_convention = ql.Thirty360(
        ql.Thirty360.BondBasis
    )

    payment_convention = ql.ModifiedFollowing

    redemption = 100.0

    helper = coupons_bond_helper(
        price,
        settlement_days,
        face_amount,
        coupon_schedule,
        coupon,
        day_count_convention,
        payment_convention,
        redemption,
        issue_date
    )

    bond_helper.append(helper)

yield_curve = ql.PiecewiseLogCubicDiscount(
    1,
    ql.India(ql.India.NSE),
    bond_helper,
    ql.Actual365Fixed()
)

pillar_dates = yield_curve.dates()

for date in pillar_dates:
    zero_rate = yield_curve.zeroRate(
        date,
        ql.Actual365Fixed(),
        ql.Continuous
    ).rate()

    print(date, zero_rate)

back_testing = ql.DiscountingBondEngine(
    ql.YieldTermStructureHandle(yield_curve)
)

validation_results = []

for _, row in selected_bonds.iterrows():

    isin = row['ISIN']

    # Market price
    market_price = row['VWAP']

    # Bond terms
    face_amount = 100.0
    coupon = row['Coupon_Rate'] / 100
    issue_date = effective_dates[isin]

    maturity_date = ql.Date(
        row['Maturity_Date'].day,
        row['Maturity_Date'].month,
        row['Maturity_Date'].year
    )

    # Coupon schedule
    coupon_schedule = ql.Schedule(
        issue_date,
        maturity_date,
        ql.Period(ql.Semiannual),
        ql.India(ql.India.NSE),
        ql.Unadjusted,
        ql.Unadjusted,
        ql.DateGeneration.Backward,
        False
    )

    # Create the actual FixedRateBond
    bond = ql.FixedRateBond(
        1,
        face_amount,
        coupon_schedule,
        [coupon],
        ql.Thirty360(ql.Thirty360.BondBasis),
        ql.ModifiedFollowing,
        100.0,
        issue_date
    )

    bond.setPricingEngine(back_testing)

    # Curve-implied clean price
    model_price = bond.cleanPrice()

    # Pricing error
    price_error = model_price - market_price

    validation_results.append(
        (
            isin,
            market_price,
            model_price,
            price_error
        )
    )

for result in validation_results:
    print(result)

forward_rates = pd.DataFrame({
    'ForwardDates': 
    [
        ql.Date(24,8,2026),
        ql.Date(17,5,2027),
        ql.Date(8,10,2029),
        ql.Date(18,6,2031),
        ql.Date(17,8,2033),
        ql.Date(12,5,2036)
    ]}, 
    
    index = 
    [
        '0Y',
        '1Y',
        '3Y',
        '5Y',
        '7Y',
        '10Y'
    ]
)

forward_rate_curve = []
for i in range(len(forward_rates) - 1):
    start = forward_rates.index[i]
    end = forward_rates.index[i + 1]
    d1 = forward_rates.iloc[i]['ForwardDates']
    d2 = forward_rates.iloc[i + 1]['ForwardDates']
    calculated_rate = yield_curve.forwardRate(
        d1,
        d2,
        ql.Actual365Fixed(),
        ql.Compounded,
        ql.Semiannual
    )
    forward_rate_curve.append(calculated_rate.rate() * 100)
print(forward_rate_curve)

zero_rate_values = [
    yield_curve.zeroRate(
        date,
        ql.Actual365Fixed(),
        ql.Compounded,
        ql.Semiannual
    ).rate() * 100
    for date in forward_rates['ForwardDates']
]

tenors = ['0Y', '1Y', '3Y', '5Y', '7Y', '10Y']
forward_tenors = ['1Y', '3Y', '5Y', '7Y', '10Y']

tenor_grid = np.arange(0.5,10.0,0.5)
zero_curve_grid = []
reference_date = yield_curve.referenceDate()
calendar = ql.India(ql.India.NSE)
for tenor in tenor_grid:
    months = int(tenor * 12)
    target_date = calendar.advance(
        reference_date,
        ql.Period(months,ql.Months)
    )

    zero_rate = yield_curve.zeroRate(
        target_date,
        ql.Actual365Fixed(),
        ql.Compounded,
        ql.Semiannual
    )

    zero_curve_grid.append({
        'Tenor': tenor,
        'Date': target_date,
        'Zero_Rate': zero_rate.rate() * 100
    })

zero_curve_grid = pd.DataFrame(zero_curve_grid)

forward_rate = []
for x in range(len(zero_curve_grid) - 1):
    st = zero_curve_grid.index[x]
    ed = zero_curve_grid.index[x + 1]
    d1 = zero_curve_grid.iloc[x]['Date']
    d2 = zero_curve_grid.iloc[x + 1]['Date']
    y = yield_curve.forwardRate(
        d1,
        d2,
        ql.Actual365Fixed(),
        ql.Compounded,
        ql.Semiannual
    )
    forward_rate.append({
        'Start_tenor': zero_curve_grid.iloc[x]['Tenor'],
        'End_tenor': zero_curve_grid.iloc[x + 1]['Tenor'],
        'Start_Date': d1,
        'End_Date': d2,
        'Forward_Rate': y.rate() * 100
    })
forward_rate = pd.DataFrame(forward_rate)
print(forward_rate)

# Calculate midpoints for plotting forward rates cleanly
mid_tenors = (forward_rate['Start_tenor'] + forward_rate['End_tenor']) / 2.0

plt.figure(figsize=(10, 6))
plt.plot(
    zero_curve_grid['Tenor'],
    zero_curve_grid['Zero_Rate'],
    marker='*',
    label='Zero Curve',
)
plt.plot(
    mid_tenors,
    forward_rate['Forward_Rate'],
    marker='*',
    label='Forward Curve',
)

plt.xlabel('Tenor (Years)')
plt.ylabel('Interest Rate (%)')
plt.title('Detailed Bootstrapped Zero Curve vs Forward Curve (Smooth)')
plt.legend()
plt.xticks([1, 3, 5, 7, 10])
plt.xlim(0.5, 10)
plt.grid(True)
plt.tight_layout()
plt.show()

key_rates = [1.0, 3.0, 5.0, 7.0, 10.0]

key_rates_dates = []
for t in key_rates:
    key_dates = calendar.advance(
        reference_date,
        ql.Period(int(t * 12), ql.Months)
    )
    key_rates_dates.append(key_dates)

risk_results = []
for _, row in selected_bonds.iterrows():
    isin = row['ISIN']
    bond = bonds[isin]

    base_engine = ql.DiscountingBondEngine(
        ql.YieldTermStructureHandle(yield_curve)
    )

    bond.setPricingEngine(base_engine)
    base_price = bond.cleanPrice()

    ## DV0! calculation
    parallel_spread = ql.QuoteHandle(
        ql.SimpleQuote(0.0001)
    )

    parallel_curve = ql.ZeroSpreadedTermStructure(
        ql.YieldTermStructureHandle(yield_curve),
        parallel_spread,
        ql.Compounded,
        ql.Semiannual,
        ql.Actual365Fixed()
    )

    parallel_engine = ql.DiscountingBondEngine(
        ql.YieldTermStructureHandle(parallel_curve)
    )

    bond.setPricingEngine(parallel_engine)
    shocked_price = bond.cleanPrice()
    dv01 = base_price - shocked_price

    # Key Rate Calculations
    krd_results = {}
    for i, key_rate in enumerate(key_rates):
        spreads = []
        for j in range(len(key_rates)):
            if i == j:
              spread = ql.QuoteHandle(
                ql.SimpleQuote(0.0001)
              )
            else:
                spread = ql.QuoteHandle(
                    ql.SimpleQuote(0.0)
                )
            spreads.append(spread)

        key_rate_curve = ql.PiecewiseZeroSpreadedTermStructure(
            ql.YieldTermStructureHandle(yield_curve),
            spreads,
            key_rates_dates,
            ql.Compounded,
            ql.Semiannual,
            ql.Actual365Fixed()
        )  

        key_rate_engine = ql.DiscountingBondEngine(
            ql.YieldTermStructureHandle(key_rate_curve)
        )

        bond.setPricingEngine(key_rate_engine)
        key_rate_price = bond.cleanPrice()
        krd_value = base_price - key_rate_price
        krd_results[f'KRDV01_{key_rate:0f}Y'] = krd_value

    risk_results.append({
        'ISIN':isin,
        'DV01': dv01,
        **krd_results
    })

risk_results_df = pd.DataFrame(risk_results)
print(risk_results_df.to_string(index=False))

new_bootstrap_data = df[df['trade'] == '2025-08-21']
print(new_bootstrap_data.head())
print(new_bootstrap_data['isin'].unique())
check = df2[df2['ISIN'].isin(new_bootstrap_data['isin'])]
print(check)

new_bootstrap_data['price_volume'] = new_bootstrap_data['face_value'] * new_bootstrap_data['trade_price']
v_data_2025 = new_bootstrap_data.groupby('isin').agg(
    total_price_value = ('price_volume','sum'),
    total_face_value = ('face_value','sum'),
    total_trade_count = ('isin','size')
).reset_index()

v_data_2025['vwap'] = (
    v_data_2025['total_price_value'] / v_data_2025['total_face_value']
)

print(v_data_2025.info())

bond_2025 = (
    v_data_2025.merge(check,left_on = 'isin',right_on='ISIN', how ='left')
)

coupon_rate = (new_bootstrap_data.groupby('isin')['coupon_rate'].first())
bond_2025 = bond_2025.merge(coupon_rate,on='isin',how='left')
print(bond_2025.info())
print(bond_2025.isna().sum())

bond_2025 = bond_2025[bond_2025['Issuer'] == 'GOI']
bond_2025 = bond_2025[bond_2025['coupon_rate'] != 'GOI']
print(bond_2025['coupon_rate'].unique())
bond_2025 = bond_2025[bond_2025['isin'].isin(check['ISIN'])]
print(bond_2025['Maturity date'].unique())
print(bond_2025.head())


bond_2025['Maturity date'] = pd.to_datetime(bond_2025['Maturity date'])
bond_2025['years_to_mature'] = (bond_2025['Maturity date'] - pd.Timestamp('2025-08-21')).dt.days / 365.25
print(bond_2025.head())

tenors_2025 = []
for _,row in bond_2025.iterrows():
    if row['years_to_mature'] <= 1.000000:
        tenors_2025.append(row)
    if 1.000000 < row['years_to_mature'] <= 3.000000:
        tenors_2025.append(row)
    if 3.000000 < row['years_to_mature'] <= 5.000000:
        tenors_2025.append(row)
    if 5.000000 < row['years_to_mature'] <= 7.000000:
        tenors_2025.append(row)
    if 7.000000 < row['years_to_mature'] <= 10.000000:
        tenors_2025.append(row)
tenors_2025 = pd.DataFrame(tenors_2025)
tenors_2025 = tenors_2025.sort_values(by='years_to_mature')

target_tenors_2025 = [1,3,5,7,10]
for tenor in target_tenors_2025:
    bond_2025[f'distance_{tenor}Y'] = (
        bond_2025['years_to_mature'] - tenor
    ).abs()

candidates_1Y_2025 = bond_2025[
    (bond_2025['years_to_mature'] > 0.5) &
    (bond_2025['years_to_mature'] < 1.5)
].sort_values('distance_1Y')

candidates_3Y_2025 = bond_2025[
    (bond_2025['years_to_mature'] > 2.5) &
    (bond_2025['years_to_mature'] < 3.5)
].sort_values('distance_3Y')

candidates_5Y_2025 = bond_2025[
    (bond_2025['years_to_mature'] > 4.5) &
    (bond_2025['years_to_mature'] < 5.5)
].sort_values('distance_5Y')

candidates_7Y_2025 = bond_2025[
    (bond_2025['years_to_mature'] > 6.5) &
    (bond_2025['years_to_mature'] < 7.5)
].sort_values('distance_7Y')

candidates_10Y_2025 = bond_2025[
    (bond_2025['years_to_mature'] > 9.5) &
    (bond_2025['years_to_mature'] < 10.5)
].sort_values('distance_10Y')


#print("Candidates for 1Y:", candidates_1Y_2025[['isin','total_trade_count','vwap','years_to_mature','distance_1Y']])
#print("Candidates for 3Y:", candidates_3Y_2025[['isin','total_trade_count','vwap','years_to_mature','distance_3Y']])
#print("Candidates for 5Y:", candidates_5Y_2025[['isin','total_trade_count','vwap','years_to_mature','distance_5Y']])
#print("Candidates for 7Y:", candidates_7Y_2025[['isin','total_trade_count','vwap','years_to_mature','distance_7Y']])
#print("Candidates for 10Y:", candidates_10Y_2025[['isin','total_trade_count','vwap','years_to_mature','distance_10Y']])

isin_list_2025 = ['IN0020170026','IN0020180454', 'IN0020230135','IN0020220151','IN0020210152']
ytm_2025 = (
    new_bootstrap_data.groupby('isin').
    apply(lambda x: (x['ytm_yield'] * x['face_value']).sum() / x['face_value'].sum())
    .reset_index(name='Market_YTM')
)

bond_2025 = bond_2025.merge(
    ytm_2025,
    left_on='isin',
    right_on = 'isin',
    how = 'left'
)
print(bond_2025.info())
bond_2025['coupon_rate'] = pd.to_numeric(bond_2025['coupon_rate'])


effective_dates_2025 = {
    'IN0020170026': ql.Date(15,5,2017),
    'IN0020180454': ql.Date(14,1,2019),
    'IN0020230135': ql.Date(13,11,2023),
    'IN0020220151': ql.Date(6,2,2023),
    'IN0020210152': ql.Date(13,9,2021)
}

def bond_calculation_2025(
    isin,
    coupon_rate,
    effective_date,
    maturity_date,
    market_yield,
    vwap,
    evaluation_date,
    face_value):
    ql.Settings.instance().evaluationDate = evaluation_date

    schedule = ql.Schedule(
        effective_date,
        maturity_date,
        ql.Period(ql.Semiannual),
        ql.India(ql.India.NSE),
        ql.Unadjusted,
        ql.Unadjusted,
        ql.DateGeneration.Backward,
        False
    )

    bond = ql.FixedRateBond(
        1,
        face_value,
        schedule,
        [coupon_rate],
        ql.Thirty360(ql.Thirty360.BondBasis),
        ql.ModifiedFollowing,
        face_value,
        effective_date
    )

    bond_cashflow = bond.cashflows()
    for cf in bond_cashflow:
        bond_date = cf.date()
        bond_amount = cf.amount()

    curve = ql.FlatForward(
        effective_date,
        market_yield,
        ql.Thirty360(ql.Thirty360.BondBasis)
    )

    engine = ql.DiscountingBondEngine(
        ql.YieldTermStructureHandle(curve)
    )

    bond.setPricingEngine(engine)
    clean_price = bond.cleanPrice()
    bond_price = ql.BondPrice(clean_price, ql.BondPrice.Clean)
    dirty_price = bond.dirtyPrice()
    accured_interest = bond.accruedAmount()
    bond_ytm = bond.bondYield(
        bond_price,
        ql.Thirty360(ql.Thirty360.BondBasis),
        ql.Compounded,
        ql.Semiannual
    )

    duration = ql.BondFunctions.duration(
        bond,
        bond_ytm,
        ql.Thirty360(ql.Thirty360.BondBasis),
        ql.Compounded,
        ql.Semiannual    
    )

    convexity = ql.BondFunctions.convexity(
        bond,
        bond_ytm,
        ql.Thirty360(ql.Thirty360.BondBasis),
        ql.Compounded,
        ql.Semiannual    
    )

    return (schedule, bond, bond_date, bond_amount, clean_price, dirty_price, accured_interest, duration, convexity)

selected_bonds_2025 = bond_2025[
    bond_2025['isin'].isin(isin_list_2025)
].copy()

print(type(effective_dates_2025))

results_2025 = []

for _,row in selected_bonds_2025.iterrows():
    isin = row['isin']
    face_value = 100.0
    coupon_rate = row['coupon_rate'] / 100
    effective_date = effective_dates_2025[isin]
    maturity_date = ql.Date(
        row['Maturity date'].day, 
        row['Maturity date'].month, 
        row['Maturity date'].year
    )
    market_yield = row['Market_YTM'] / 100
    vwap = row['vwap']
    evaluation_date = ql.Date(21,8,2025)
    result_2025 = bond_calculation_2025(
        isin,
        coupon_rate,
        effective_date,
        maturity_date,
        market_yield,
        vwap,
        evaluation_date,
        face_value
    )
    results_2025.append(result_2025)

bond_helper_2025 = []
def coupons_bond_helper_2025(
    price,
    settlement_days,
    face_amount,
    coupon_schedule,
    coupon,
    day_count_convention,
    payment_convention,
    redemption,
    issue_date
):
    price_handle = ql.QuoteHandle(ql.SimpleQuote(price))

    helper = ql.FixedRateBondHelper(
        price_handle,
        settlement_days,
        face_amount,
        coupon_schedule,
        [coupon],
        day_count_convention,
        payment_convention,
        redemption,
        issue_date
    )
    return helper

for _, row in selected_bonds_2025.iterrows():
    isin = row['isin']
    price = row['vwap']
    settlement_days = 1
    face_amount = 100.0
    issue_date = effective_dates_2025[isin]
    maturity_date = ql.Date(
        row['Maturity date'].day,
        row['Maturity date'].month,
        row['Maturity date'].year
    )
    coupon_schedule = ql.Schedule(
        issue_date,
        maturity_date,
        ql.Period(ql.Semiannual),
        ql.India(ql.India.NSE),
        ql.Unadjusted,
        ql.Unadjusted,
        ql.DateGeneration.Backward,
        False
    )
    coupon = row['coupon_rate'] / 100
    day_count_convention = ql.Thirty360(ql.Thirty360.BondBasis)
    payment_convention = ql.ModifiedFollowing
    redemption = 100.0

    helper_2025 = coupons_bond_helper_2025(
        price,
        settlement_days,
        face_amount,
        coupon_schedule,
        coupon,
        day_count_convention,
        payment_convention,
        redemption,
        issue_date
    )

    bond_helper_2025.append(helper_2025)

yield_curve_2025 = ql.PiecewiseLogCubicDiscount(
    1,
    ql.India(ql.India.NSE),
    bond_helper_2025,
    ql.Actual365Fixed()
)

tenor_grid_2025 = np.arange(0.5, 10.0, 0.5)
zero_curve_grid_2025 = []
reference_date_2025 = yield_curve_2025.referenceDate()
calendar_2025 = ql.India(ql.India.NSE)
for tenor in tenor_grid_2025:
    months = int(tenor * 12)
    target_date = calendar_2025.advance(
        reference_date_2025,
        ql.Period(months, ql.Months)
    )

    zero_rate = yield_curve_2025.zeroRate(
        target_date,
        ql.Actual365Fixed(),
        ql.Compounded,
        ql.Semiannual
    )

    zero_curve_grid_2025.append({
        'Tenor': tenor,
        'Date': target_date,
        'Zero_Rate': zero_rate.rate() * 100
    })
zero_curve_grid_2025 = pd.DataFrame(zero_curve_grid_2025)


plt.figure(figsize=(10, 6))
plt.plot(
    zero_curve_grid['Tenor'],
    zero_curve_grid['Zero_Rate'],
    marker='*',
    label='Zero Curve',
)
plt.plot(
    zero_curve_grid_2025['Tenor'],
    zero_curve_grid_2025['Zero_Rate'],
    marker='*',
    label='Zero Curve 2025',
)
plt.xlabel('Tenor')
plt.ylabel('Interest Rate (%)')
plt.title('Bootstrapped Zero Curve Comparison: 2026 vs 2025')
plt.xticks([1, 3, 5, 7, 10])
plt.xlim(0.5, 10)
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()

## Validating the 2025 bootstrapped curve with market prices
validation_results_2025 = []
back_testing_2025 = ql.DiscountingBondEngine(
    ql.YieldTermStructureHandle(yield_curve_2025)
)
for _, row in selected_bonds_2025.iterrows():
    isin = row['isin']
    price = row['vwap']
    effective_date = effective_dates_2025[isin]
    face_value = 100.0
    coupon_rate = row['coupon_rate'] / 100
    maturity_date = ql.Date(
        row['Maturity date'].day, 
        row['Maturity date'].month, 
        row['Maturity date'].year
    )

    schedule = ql.Schedule(
        effective_date,
        maturity_date,
        ql.Period(ql.Semiannual),
        ql.India(ql.India.NSE),
        ql.Unadjusted,
        ql.Unadjusted,
        ql.DateGeneration.Backward,
        False
    )

    bond = ql.FixedRateBond(
        1,
        face_value,
        schedule,
        [coupon_rate],
        ql.Thirty360(ql.Thirty360.BondBasis),
        ql.ModifiedFollowing,
        face_value,
        effective_date
    )

    bond.setPricingEngine(back_testing_2025)
    model_price_2025 = bond.cleanPrice()

    # Pricing error
    price_error = model_price_2025 - price

    validation_results_2025.append(
        (
            isin,
            price,
            model_price_2025,
            price_error
        )
    )

for result in validation_results_2025:
    print(result)

yield_curve_analysis = []
tenor_year = [1,3,5,7,10]
for tenor in tenor_year:

    rate_2026 = zero_curve_grid.loc[
        zero_curve_grid['Tenor'] == tenor, 'Zero_Rate'
    ]

    rate_2025 = zero_curve_grid_2025.loc[
        zero_curve_grid_2025['Tenor'] == tenor, 'Zero_Rate'
    ]

    if rate_2026.empty or rate_2025.empty:
        print(f"Missing zero rate for {tenor}Y")
        continue

    rate_2026 = rate_2026.iloc[0]
    rate_2025 = rate_2025.iloc[0]

    difference = (rate_2026 - rate_2025) * 100

    yield_curve_analysis.append({
        'Tenor': tenor,
        'Zero Rate 2026 (%)': rate_2026,
        'Zero Rate 2025 (%)': rate_2025,
        'Change (bp)': difference
    })

yield_curve_analysis = pd.DataFrame(yield_curve_analysis)

print(yield_curve_analysis.round(4))