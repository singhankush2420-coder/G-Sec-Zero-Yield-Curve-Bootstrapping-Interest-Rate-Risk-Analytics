# G-Sec Zero-Yield Curve Bootstrapping & Interest Rate Risk Analytics

**Python | QuantLib | PostgreSQL | CCIL Market Data**

## Project Overview

This project focuses on constructing and analysing Indian Government Securities (G-Sec) zero-yield curves using historical trade data sourced from the Clearing Corporation of India Limited (CCIL).

The project uses Python for data processing, PostgreSQL for market-data storage, and QuantLib for fixed-income valuation and yield curve construction. It also analyses changes in the yield curve between historical and current market dates.

The objective is to understand the relationship between bond prices, yields, discount factors, and interest rate risk through a practical fixed-income analytics workflow.

## Key Features

- **CCIL Market Data Processing:** Extracts and processes G-Sec trade data stored in PostgreSQL.
- **Data Preparation:** Cleans bond reference data and calculates volume-weighted average prices (VWAPs) using trade prices and face values.
- **Bond Selection:** Selects representative government securities around target maturities based on time to maturity and available trading activity.
- **Yield Curve Bootstrapping:** Constructs a discount curve using QuantLib's `PiecewiseLogCubicDiscount` interpolation method.
- **Fixed-Income Valuation:** Calculates clean prices, dirty prices, accrued interest, yield to maturity, duration, and convexity.
- **Zero-Yield Curve Analysis:** Generates zero-coupon rates across a range of tenors.
- **Forward Rate Analysis:** Derives forward rates from the bootstrapped term structure.
- **Interest Rate Risk Analytics:** Calculates DV01 and Key Rate DV01 (KRDV01) to assess sensitivity to parallel and localized yield curve shifts.
- **Historical Curve Comparison:** Compares zero-yield curves constructed using market observations from 21 August 2025 and 21 August 2026.
- **Calibration Validation:** Reprices selected calibration bonds using the bootstrapped curve and compares model prices with observed market prices.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core programming and analytics |
| pandas | Data cleaning, aggregation, and manipulation |
| NumPy | Numerical calculations |
| Matplotlib | Yield curve visualisation |
| SciPy | Numerical and interpolation utilities |
| QuantLib | Bond valuation, curve construction, and risk calculations |
| PostgreSQL | Market-data storage and querying |
| SQLAlchemy | Database connectivity |
| CCIL | Source of G-Sec trade market data |

## Project Workflow

1. Load CCIL G-Sec trade data from PostgreSQL.
2. Filter transactions for the selected market observation date.
3. Aggregate trades by ISIN and calculate VWAP, total traded face value, and trade count.
4. Match the trade data with bond reference information, including coupon rates and maturity dates.
5. Filter eligible Government of India securities and select representative bonds around target maturities.
6. Construct bond cash-flow schedules using QuantLib and applicable fixed-income conventions.
7. Build the bootstrapped discount curve from selected market instruments.
8. Extract zero rates and calculate forward rates.
9. Calculate duration, convexity, DV01, and Key Rate DV01.
10. Validate calibration prices and compare historical and current yield curves.

## Target Tenors

The analysis focuses on the following benchmark tenors:

- 1 Year
- 3 Years
- 5 Years
- 7 Years
- 10 Years

The actual calibration dates depend on the maturities of the selected bonds. A target tenor does not necessarily correspond to a bond with exactly that remaining maturity.

## Market Conventions

The current implementation incorporates the following conventions:

- **Calendar:** QuantLib India NSE calendar
- **Coupon frequency:** Semiannual
- **Day-count convention:** Thirty/360 Bond Basis
- **Payment adjustment:** Modified Following
- **Curve interpolation:** Log-cubic discount-factor interpolation
- **Market observations:** CCIL G-Sec trade data

Market conventions and instrument-specific terms should be verified against the applicable security documentation before using the results for production valuation.

## Interest Rate Risk Metrics

### Duration

Measures the sensitivity of a bond's price to changes in yield.

### Convexity

Measures the curvature of the relationship between bond prices and yields, improving the approximation of price changes for larger yield movements.

### DV01

Estimates the price change associated with a one-basis-point parallel increase in interest rates.

### Key Rate DV01 (KRDV01)

Measures sensitivity to a one-basis-point change at selected points on the yield curve, helping distinguish exposure across different maturities.

The risk metrics in the current implementation are calculated for the selected bonds. Portfolio-level aggregation and stress testing can be developed as a separate extension.

## Historical Yield Curve Analysis

The project compares curves constructed using observations from:

- **21 August 2025:** Historical reference date
- **21 August 2026:** Current reference date

The comparison examines changes in zero rates across common tenors and helps identify where yields have increased or decreased most significantly.

## Validation Approach

The implementation includes repricing selected calibration bonds using the constructed curve and comparing the resulting model prices with observed VWAPs.

This is an **in-sample calibration consistency check**, because the same bonds are used to construct and validate the curve. Independent out-of-sample testing would require additional instruments or observations not used during calibration.

The curve's maximum maturity is determined by the selected calibration instruments. A plotted 10-year axis label does not guarantee that the curve contains a directly calibrated 10-year rate.

## Disclaimer

This project is intended for educational and research purposes. The outputs depend on the quality of market data, instrument reference information, bond-selection methodology, and modelling assumptions. They should not be treated as production pricing outputs or investment advice without further validation.

## Author
Developed as a fixed-income quantitative analytics project using Python, QuantLib, PostgreSQL, and CCIL G-Sec market data.
