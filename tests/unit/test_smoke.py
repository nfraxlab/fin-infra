from __future__ import annotations


def test_imports_and_version() -> None:
    import fin_infra

    assert hasattr(fin_infra, "__version__")


def test_models_exist() -> None:
    from fin_infra.models import Account, Transaction, Quote, AccountType

    assert AccountType.checking.value == "checking"
    _ = Account(id="a1", name="Checking", type=AccountType.checking)
    _ = Transaction(id="t1", account_id="a1", date=__import__("datetime").date.today(), amount=1.23)
    _ = Quote(
        symbol="AAPL",
        price=190.0,
        as_of=__import__("datetime").datetime.now(__import__("datetime").UTC),
    )


def test_clients_exist() -> None:
    from fin_infra.clients import BankingClient, MarketDataClient, CreditClient

    assert BankingClient and MarketDataClient and CreditClient
