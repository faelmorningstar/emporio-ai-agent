"""Dados sintéticos mínimos, sem reproduzir o catálogo privado."""

import csv
from decimal import Decimal

import pytest

from emporio_agent.services.catalog import Catalog, CatalogError, HEADERS


def write_table(root, table, rows, headers=None):
    with (root / f'{table}.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(headers or HEADERS[table].split(','))
        writer.writerows(rows)


@pytest.fixture
def source(tmp_path):
    write_table(tmp_path, 'categories', [[1, 'Categoria A', 'Teste'], [2, 'Categoria B', 'Teste']])
    write_table(tmp_path, 'products', [
        [1, '10.05', 'Produto Alfa', 1, 'Teste', 2, 'active', '{}', '2025-01-01'],
        [2, '20.00', 'Produto Beta', 2, 'Teste', 0, 'active', '{}', '2025-01-02'],
        [3, '30.00', 'Item Gama', 1, 'Teste', 3, 'discontinued', '{}', '2025-01-03'],
        [4, '40.00', 'Item Delta', 1, 'Teste', 1, 'coming_soon', '{}', '2025-01-04'],
    ])
    write_table(tmp_path, 'promotions', [
        [1, 1, '10', 'Teste A', 1],
        [2, 1, '50', 'Teste B', 0],
        [3, 1, '20', 'Teste C', 1],
        [4, 2, '100', 'Teste D', 1],
    ])
    return tmp_path


def test_loading_and_types(source):
    c = Catalog.load(source)
    assert (len(c.categories), len(c.products), len(c.promotions)) == (2, 4, 4)
    p = c.get_product(1)
    assert p.price_brl == Decimal('10.05')
    assert isinstance(p.price_brl, Decimal)
    assert p.specs == {}
    assert p.created_at.isoformat() == '2025-01-01'


def test_filters(source):
    c = Catalog.load(source)
    assert [p.product_id for p in c.search_products(name='PRODUTO')] == [1, 2]
    assert [p.product_id for p in c.search_products(category='categoria a')] == [1, 3, 4]
    assert [p.product_id for p in c.search_products(category=2)] == [2]
    assert [p.product_id for p in c.search_products(min_price='10.05', max_price=Decimal('20'))] == [1, 2]
    assert [p.product_id for p in c.search_products(name='produto', category=1, max_price='11')] == [1]
    assert c.search_products(name='inexistente') == []
    assert c.search_products(category=999) == []


@pytest.mark.parametrize('low,high', [('20', '10'), ('-1', None), ('NaN', None), ('Infinity', None), (1.5, None)])
def test_invalid_price_filters(source, low, high):
    with pytest.raises(ValueError):
        Catalog.load(source).search_products(min_price=low, max_price=high)


def test_stock_and_status(source):
    c = Catalog.load(source)
    assert c.get_product(1).in_stock and c.get_product(1).available
    assert not c.get_product(2).in_stock and not c.get_product(2).available
    for key in (3, 4):
        assert c.get_product(key).in_stock
        assert not c.get_product(key).available
    with pytest.raises(LookupError, match='999'):
        c.get_product(999)


def test_promotions_and_decimal_rounding(source):
    c = Catalog.load(source)
    assert [p.promotion_id for p in c.active_promotions()] == [1, 3, 4]
    assert [p.promotion_id for p in c.active_promotions(1)] == [1, 3]
    # Cada promoção é calculada isoladamente, sem acumulação presumida.
    assert [p.discounted_price(c.get_product(1).price_brl) for p in c.active_promotions(1)] == [Decimal('9.05'), Decimal('8.04')]
    assert c.promotions[4].discounted_price(Decimal('20')) == Decimal('0.00')
    with pytest.raises(ValueError, match='inativa'):
        c.promotions[2].discounted_price(Decimal('10.05'))
    assert c.active_promotions(3) == []
    with pytest.raises(LookupError):
        c.active_promotions(999)


@pytest.mark.parametrize('table', ['categories', 'products', 'promotions'])
def test_missing_files(source, table):
    (source / f'{table}.csv').unlink()
    with pytest.raises(CatalogError, match=f'{table}.csv'):
        Catalog.load(source)


def test_invalid_headers(source):
    write_table(source, 'categories', [], ['id', 'name'])
    with pytest.raises(CatalogError, match='cabeçalhos'):
        Catalog.load(source)


@pytest.mark.parametrize('field,value', [
    ('price_brl', '-1'), ('price_brl', 'NaN'), ('price_brl', 'abc'),
    ('stock_quantity', '-1'), ('stock_quantity', '1.5'), ('status', 'unknown'),
    ('specs', 'not json'), ('specs', '[]'), ('created_at', '2025-02-30'),
    ('category_id', '999'), ('product_id', '0'), ('name', ''),
])
def test_invalid_products(source, field, value):
    row = ['1', '10.05', 'Produto teste', '1', 'Teste', '2', 'active', '{}', '2025-01-01']
    row[HEADERS['products'].split(',').index(field)] = value
    write_table(source, 'products', [row])
    with pytest.raises(CatalogError, match='products.csv'):
        Catalog.load(source)


@pytest.mark.parametrize('field,value', [('discount_percent', '101'), ('discount_percent', '-1'),
                                        ('discount_percent', 'Infinity'), ('is_active', 'true'),
                                        ('product_id', '999')])
def test_invalid_promotions(source, field, value):
    row = ['1', '1', '10', 'Teste', '1']
    row[HEADERS['promotions'].split(',').index(field)] = value
    write_table(source, 'promotions', [row])
    with pytest.raises(CatalogError, match='promotions.csv'):
        Catalog.load(source)


@pytest.mark.parametrize('table,row', [
    ('categories', [1, 'Teste', 'Teste']),
    ('products', [1, '10', 'Teste', 1, 'Teste', 1, 'active', '{}', '2025-01-01']),
    ('promotions', [1, 1, '10', 'Teste', 1]),
])
def test_duplicate_ids(source, table, row):
    write_table(source, table, [row, row])
    with pytest.raises(CatalogError, match='duplicado'):
        Catalog.load(source)


@pytest.mark.parametrize('row', [[1, 'Teste'], [1, 'Teste', 'Teste', 'extra']])
def test_malformed_rows(source, row):
    write_table(source, 'categories', [row])
    with pytest.raises(CatalogError, match='linha 2'):
        Catalog.load(source)


def test_invalid_utf8(source):
    (source / 'categories.csv').write_bytes(b'\xff')
    with pytest.raises(CatalogError, match='categories.csv'):
        Catalog.load(source)


def test_zero_discount(source):
    write_table(source, 'promotions', [[1, 1, '0', 'Teste', 1]])
    c = Catalog.load(source)
    assert c.active_promotions(1)[0].discounted_price(Decimal('10.05')) == Decimal('10.05')
