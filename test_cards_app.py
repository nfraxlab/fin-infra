"""Test app to verify landing page cards for banking and market data."""
from svc_infra.api.fastapi.ease import easy_service_app
from fin_infra.banking import add_banking
from fin_infra.markets import add_market_data

# Create app
app = easy_service_app(name="FinInfraTest")

# Add banking capability (should create card at /)
banking = add_banking(app, provider="teller")

# Add market data capability (should create card at /)
market = add_market_data(app, provider="yahoo")

if __name__ == "__main__":
    import uvicorn
    print("\n🚀 Starting test server...")
    print("📍 Landing page with cards: http://localhost:8000/")
    print("📊 Banking docs: http://localhost:8000/banking/docs")
    print("📈 Market docs: http://localhost:8000/market/docs")
    print("\n✅ Expected cards on landing page: Banking, Market Data")
    uvicorn.run(app, host="0.0.0.0", port=8000)
