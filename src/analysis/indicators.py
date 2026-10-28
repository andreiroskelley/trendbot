def calculate_relative_strength(stock_close: pd.Series, market_close: pd.Series, period: int = 20) -> pd.Series:
    """
    Calculate Relative Strength (RS) of a stock vs. the broader market (e.g., SPY).
    RS = (Stock Price / Market Price) * 100
    A rising RS line means the stock is outperforming the market.
    """
    # Align the two series on their dates to ensure we are comparing the same days
    aligned = pd.concat([stock_close, market_close], axis=1, join='inner')
    aligned.columns = ['stock', 'market']

    if len(aligned) < period:
        logger.warning(
            f"Not enough aligned data for RS: stock={len(stock_close)} bars, "
            f"market={len(market_close)} bars, aligned={len(aligned)}, need={period}. "
            f"Check that stock and benchmark are the same asset class "
            f"(stocks 04:00 UTC vs crypto 00:00 UTC timestamps do not align)."
        )
        return pd.Series(index=stock_close.index, dtype=float)

    # Calculate the raw ratio
    rs_ratio = (aligned['stock'] / aligned['market']) * 100

    # Reindex back to the original stock index to maintain alignment
    return rs_ratio.reindex(stock_close.index)