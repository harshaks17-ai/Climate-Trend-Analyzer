"""Climate Trend Analyzer - core package.

Modules
-------
config        -> paths + global constants
simulation    -> synthetic (virtual) climate dataset generator
preprocessing -> cleaning + feature engineering
eda           -> exploratory statistics + static charts
trends        -> long-term trend / change-point analysis
anomaly       -> anomaly (extreme event) detection
forecast      -> time-series forecasting
visuals       -> plotly 3D + animated interactive charts
report        -> markdown report + summary tables
"""

__version__ = "1.0.0"
__all__ = [
    "config",
    "simulation",
    "preprocessing",
    "eda",
    "trends",
    "anomaly",
    "forecast",
    "visuals",
    "report",
]
