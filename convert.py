from .. import loader, utils
import aiohttp

@loader.tds
class CurrencyConverter(loader.Module):
    """Конвертер валют с разбиением по регионам и выводом всех валют"""

    strings = {
        "name": "CurrencyConverter",
        "usage": ("Использование:\n"
                  "!currency <сумма> <из_валюты> <в_валюту>\n"
                  "Пример:\n!currency 100 USD EUR\n\n"
                  "Список валют с разбивкой по регионам:\n"
                  "!currencylist"),
        "error": "❗ Ошибка: {error}",
        "result": "💱 {amount} {from_currency} = {converted:.2f} {to_currency}",
        "currencies_by_region": "🌍 Валюты по регионам:\n\n{regions}\n\n📄 Все доступные валюты:\n{all_currencies}"
    }

    REGION_CURRENCIES = {
        "Европа": [
            "EUR", "GBP", "CHF", "SEK", "NOK", "DKK", "RUB", "UAH", "CZK", "PLN", "HUF",
            "BGN", "HRK", "RON", "ISK", "MKD", "MDL", "BYN", "GEL"
        ],
        "Азия": [
            "CNY", "JPY", "INR", "KRW", "SGD", "THB", "MYR", "IDR", "PHP", "VND", "PKR",
            "BDT", "LKR", "NPR", "KZT", "UZS", "TWD", "HKD"
        ],
        "Америка": [
            "USD", "CAD", "MXN", "BRL", "ARS", "CLP", "COP", "PEN", "UYU", "VEF", "GTQ",
            "BOB", "PYG", "CRC", "HTG"
        ],
        "Океания": [
            "AUD", "NZD", "FJD", "PGK", "SBD"
        ],
        "Африка": [
            "ZAR", "EGP", "NGN", "KES", "GHS", "DZD", "MAD", "TND", "TZS", "UGX", "XOF", "XAF"
        ],
    }

    async def client_ready(self, client, db):
        self.client = client
        self.rates = None
        self.base = None
        self.currencies = None

    async def fetch_rates(self, base):
        url = f"https://open.er-api.com/v6/latest/{base}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                if data.get("result") != "success":
                    return None
                return data

    @loader.command()
    async def currency(self, message):
        """Конвертирует сумму из одной валюты в другую"""
        args = utils.get_args_raw(message)
        parts = args.split()
        if len(parts) != 3:
            return await message.edit(self.strings["usage"])

        amount_str, from_currency, to_currency = parts
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        try:
            amount = float(amount_str.replace(',', '.'))
        except ValueError:
            return await message.edit(self.strings["error"].format(error="Неверная сумма"))

        if self.base != from_currency or not self.rates:
            data = await self.fetch_rates(from_currency)
            if not data:
                return await message.edit(self.strings["error"].format(error="Не удалось получить курсы валют"))
            self.rates = data.get("rates", {})
            self.base = from_currency
            self.currencies = sorted(self.rates.keys())

        if to_currency not in self.rates:
            return await message.edit(self.strings["error"].format(error=f"Валюта {to_currency} не поддерживается"))

        rate = self.rates[to_currency]
        converted = amount * rate

        await message.edit(self.strings["result"].format(
            amount=amount,
            from_currency=from_currency,
            to_currency=to_currency,
            converted=converted
        ))

    @loader.command()
    async def currencylist(self, message):
        """Показывает валюты по регионам и полный список валют"""

        if not self.currencies:
            data = await self.fetch_rates("USD")
            if not data:
                return await message.edit("❗ Не удалось получить список валют")
            self.rates = data.get("rates", {})
            self.base = "USD"
            self.currencies = sorted(self.rates.keys())

        currency_to_region = {}
        for region, codes in self.REGION_CURRENCIES.items():
            for c in codes:
                currency_to_region[c] = region

        region_groups = {region: [] for region in self.REGION_CURRENCIES.keys()}
        region_groups["Прочие"] = []

        for c in self.currencies:
            if c in currency_to_region:
                region_groups[currency_to_region[c]].append(c)
            else:
                region_groups["Прочие"].append(c)

        lines = []
        for region, codes in region_groups.items():
            if not codes:
                continue
            codes_sorted = sorted(codes)
            lines.append(f"🌍 {region}: {', '.join(codes_sorted)}")

        all_currencies_line = "  ".join(self.currencies)

        text = self.strings["currencies_by_region"].format(
            regions="\n".join(lines),
            all_currencies=all_currencies_line
        )
        await message.edit(text)
