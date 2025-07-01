from .. import loader, utils
import aiohttp

@loader.tds
class CurrencyConverter(loader.Module):
    """Конвертер валют через API open.er-api.com (без ключа)"""

    strings = {
        "name": "CurrencyConverter",
        "usage": "Использование:\n!currency <сумма> <из_валюты> <в_валюту>\nПример:\n!currency 100 USD EUR",
        "error": "❗ Ошибка: {error}",
        "result": "💱 {amount} {from_currency} = {converted:.2f} {to_currency}",
        "currencies_list": "📄 Доступные валюты:\n{currencies}"
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
        """Показывает список доступных валют"""
        if not self.currencies:
            data = await self.fetch_rates("USD")
            if not data:
                return await message.edit("❗ Не удалось получить список валют")
            self.rates = data.get("rates", {})
            self.base = "USD"
            self.currencies = sorted(self.rates.keys())

        lines = "\n".join(self.currencies)
        await message.edit(self.strings["currencies_list"].format(currencies=lines))

