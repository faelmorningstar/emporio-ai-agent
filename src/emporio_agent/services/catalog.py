"""Carregamento e consultas do catálogo CSV, sem dependências externas."""

import csv
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path


class CatalogError(ValueError):
    """Arquivo ou registro do catálogo inválido."""


def money(value: str | Decimal) -> Decimal:
    """Aceita valores decimais exatos; floats são rejeitados."""
    if not isinstance(value, (str, Decimal)):
        raise ValueError("Valor monetário deve ser str ou Decimal.")
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"Valor monetário inválido: {value!r}.") from exc
    if not result.is_finite() or result < 0:
        raise ValueError("Valor monetário deve ser finito e não negativo.")
    return result


@dataclass(frozen=True)
class Category:
    category_id: int
    name: str
    description: str


@dataclass(frozen=True)
class Product:
    product_id: int
    price_brl: Decimal
    name: str
    category_id: int
    description: str
    stock_quantity: int
    status: str
    specs: dict
    created_at: date

    @property
    def in_stock(self) -> bool:
        return self.stock_quantity > 0

    @property
    def available(self) -> bool:
        return self.status == "active" and self.in_stock


@dataclass(frozen=True)
class Promotion:
    promotion_id: int
    product_id: int
    discount_percent: Decimal
    description: str
    is_active: bool

    def discounted_price(self, price: Decimal) -> Decimal:
        """Aplica somente esta promoção; não acumula descontos."""
        if not self.is_active:
            raise ValueError("Promoção inativa não pode ser aplicada.")
        return (money(price) * (1 - self.discount_percent / Decimal(100))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )


HEADERS = {
    "categories": "category_id,name,description",
    "products": "product_id,price_brl,name,category_id,description,stock_quantity,status,specs,created_at",
    "promotions": "promotion_id,product_id,discount_percent,description,is_active",
}


def _integer(value: str, *, minimum: int = 1) -> int:
    if not value.isascii() or not value.isdecimal() or int(value) < minimum:
        raise ValueError(f"Inteiro inválido: {value!r}; mínimo {minimum}.")
    return int(value)


def _parse(table: str, r: dict):
    if table == "categories":
        return Category(_integer(r['category_id']), r['name'], r['description'])
    if table == "products":
        if r['status'] not in {'active', 'discontinued', 'coming_soon'}:
            raise ValueError(f"Status desconhecido: {r['status']!r}.")
        specs = json.loads(r['specs'])
        if not isinstance(specs, dict):
            raise ValueError("specs deve ser um objeto JSON.")
        return Product(
            _integer(r['product_id']), money(r['price_brl']), r['name'],
            _integer(r['category_id']), r['description'],
            _integer(r['stock_quantity'], minimum=0), r['status'], specs,
            date.fromisoformat(r['created_at']),
        )
    percent = money(r['discount_percent'])
    if percent > 100:
        raise ValueError("discount_percent deve estar entre 0 e 100.")
    if r['is_active'] not in {'0', '1'}:
        raise ValueError("is_active deve ser 0 ou 1.")
    return Promotion(_integer(r['promotion_id']), _integer(r['product_id']),
                     percent, r['description'], r['is_active'] == '1')


def _load(directory: Path, table: str) -> dict:
    path = directory / f"{table}.csv"
    result = {}
    try:
        with path.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream, strict=True)
            expected = HEADERS[table].split(',')
            if reader.fieldnames is None or len(reader.fieldnames) != len(expected) or set(reader.fieldnames) != set(expected):
                raise CatalogError(f"{path}: cabeçalhos esperados: {', '.join(expected)}.")
            for row in reader:
                try:
                    if set(row) != set(expected) or any(v is None or not v.strip() for v in row.values()):
                        raise ValueError("Colunas ausentes, extras ou campos vazios.")
                    record = _parse(table, row)
                    id_field = {'categories': 'category_id', 'products': 'product_id',
                                'promotions': 'promotion_id'}[table]
                    key = getattr(record, id_field)
                    if key in result:
                        raise ValueError(f"Identificador duplicado: {key}.")
                    result[key] = record
                except (ValueError, TypeError, InvalidOperation) as exc:
                    raise CatalogError(f"{path}, linha {reader.line_num}: {exc}") from exc
    except (OSError, UnicodeError, csv.Error) as exc:
        raise CatalogError(f"Não foi possível ler {path}: {exc}") from exc
    return result


@dataclass
class Catalog:
    categories: dict[int, Category]
    products: dict[int, Product]
    promotions: dict[int, Promotion]

    @classmethod
    def load(cls, directory: str | Path) -> 'Catalog':
        directory = Path(directory)
        categories = _load(directory, 'categories')
        products = _load(directory, 'products')
        promotions = _load(directory, 'promotions')
        for p in products.values():
            if p.category_id not in categories:
                raise CatalogError(f"products.csv: produto {p.product_id} referencia categoria inexistente {p.category_id}.")
        for promo in promotions.values():
            if promo.product_id not in products:
                raise CatalogError(f"promotions.csv: promoção {promo.promotion_id} referencia produto inexistente {promo.product_id}.")
        return cls(categories, products, promotions)

    def get_product(self, product_id: int) -> Product:
        try:
            return self.products[product_id]
        except KeyError as exc:
            raise LookupError(f"Produto {product_id} não encontrado.") from exc

    def search_products(self, *, name: str | None = None, category: int | str | None = None,
                        min_price: str | Decimal | None = None,
                        max_price: str | Decimal | None = None) -> list[Product]:
        """Nome parcial; categoria por ID ou nome exato; limites inclusivos.

        Compara nomes sem distinguir maiúsculas. Inclui todos os status.
        Os preços filtrados são os de catálogo, antes dos descontos.
        """
        low = money(min_price) if min_price is not None else None
        high = money(max_price) if max_price is not None else None
        if low is not None and high is not None and low > high:
            raise ValueError("Preço mínimo não pode exceder o máximo.")
        return [p for p in self.products.values()
                if (name is None or name.casefold() in p.name.casefold())
                and (category is None or p.category_id == category or
                     isinstance(category, str) and self.categories[p.category_id].name.casefold() == category.casefold())
                and (low is None or p.price_brl >= low)
                and (high is None or p.price_brl <= high)]

    def active_promotions(self, product_id: int | None = None) -> list[Promotion]:
        """Atividade baseada somente em is_active; os dados não contêm validade."""
        if product_id is not None:
            self.get_product(product_id)
        return [p for p in self.promotions.values()
                if p.is_active and (product_id is None or p.product_id == product_id)]
