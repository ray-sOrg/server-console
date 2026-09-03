"""Validate the Console dish payload before any database mutation."""
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit
from uuid import UUID

CATEGORIES = {
    'RECOMMENDED', 'COLD_DISH', 'SEASONAL_VEGETABLE', 'HOT_DISH',
    'SOUP', 'SNACK_STAPLE', 'SEAFOOD', 'BEVERAGE', 'BAIJIU',
    'BEER', 'FITNESS_MEAL', 'OTHER',
}
NUTRIENTS = ('proteinG', 'carbohydrateG', 'fatG', 'fiberG', 'sugarG', 'sodiumMg')


def number(value, field, positive=False, maximum=1000000):
    if isinstance(value, bool) or value is None:
        raise ValueError(f'{field} 必须是数值')
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f'{field} 必须是数值') from None
    if not result.is_finite() or result < 0 or result > maximum:
        raise ValueError(f'{field} 超出允许范围')
    if positive and result < Decimal('0.01'):
        raise ValueError(f'{field} 必须不小于 0.01')
    if result != result.quantize(Decimal('0.01')):
        raise ValueError(f'{field} 最多支持两位小数')
    return result


def image_url(value, field):
    if value is None or value == '':
        return None
    if not isinstance(value, str) or len(value) > 2048:
        raise ValueError(f'{field} 必须是图片链接')
    url = urlsplit(value)
    if url.scheme not in ('https', 'http') or not url.netloc or url.username or url.password:
        raise ValueError(f'{field} 必须是 http(s) 链接')
    return value


def nutrition_payload(data):
    if not isinstance(data, dict):
        raise ValueError('nutrition 必须是对象')
    allowed = set(NUTRIENTS) | {
        'basis', 'defaultServingAmount', 'servingUnit', 'caloriesKcal', 'labelImageUrl',
    }
    if set(data) - allowed:
        raise ValueError('营养数据包含未知字段')
    basis, unit = data.get('basis'), data.get('servingUnit')
    valid_units = {'PER_100G': ('g',), 'PER_100ML': ('ml',), 'PER_SERVING': ('piece', 'serving')}
    if not isinstance(basis, str) or unit not in valid_units.get(basis, ()):
        raise ValueError('营养基准与份量单位不匹配')
    result = {
        'basis': basis,
        'servingUnit': unit,
        'defaultServingAmount': number(data.get('defaultServingAmount'), '默认份量', positive=True),
        'caloriesKcal': number(data.get('caloriesKcal'), '热量'),
        'labelImageUrl': image_url(data.get('labelImageUrl'), '营养成分表图片'),
    }
    for field in NUTRIENTS:
        result[field] = number(data[field], field) if data.get(field) is not None else None
    return result


def dish_payload(data, existing=None):
    if not isinstance(data, dict) or not data:
        raise ValueError('请提供菜品信息')
    result = {}
    for field, limit in (('name', 80), ('nameEn', 80), ('description', 500), ('descEn', 500)):
        if field not in data:
            continue
        value = data[field]
        if value is not None and (not isinstance(value, str) or len(value) > limit):
            raise ValueError(f'{field} 长度不能超过 {limit} 个字符')
        result[field] = value.strip() if isinstance(value, str) else None
    if ('name' in result and not result['name']) or (existing is None and not result.get('name')):
        raise ValueError('请输入菜品名称')
    category = data.get('category', existing.category if existing else None)
    if not isinstance(category, str) or category not in CATEGORIES:
        raise ValueError('无效的菜品分类')
    result['category'] = category
    if 'id' in data:
        try:
            dish_id = str(UUID(str(data['id'])))
        except ValueError:
            raise ValueError('菜品 ID 必须是 UUID') from None
        if existing and dish_id != existing.id:
            raise ValueError('不能修改菜品 ID')
        if existing is None:
            result['id'] = dish_id
    if existing is None or 'price' in data:
        result['price'] = number(data.get('price', 0), '价格')
    if 'image' in data:
        result['image'] = image_url(data['image'], '菜品图片')
    for field in ('isAvailable', 'isSpicy', 'isVegetarian'):
        if field in data:
            if not isinstance(data[field], bool):
                raise ValueError(f'{field} 必须为布尔值')
            result[field] = data[field]
    # Omitting nutrition preserves the current record; explicit null clears it
    # only for ordinary dishes. Full objects replace the nutrition values.
    if 'nutrition' in data:
        result['nutrition'] = nutrition_payload(data['nutrition']) if data['nutrition'] is not None else None
    has_nutrition = result.get('nutrition', existing.nutrition if existing else None)
    if category == 'FITNESS_MEAL' and has_nutrition is None:
        raise ValueError('健身餐必须填写营养信息')
    return result
